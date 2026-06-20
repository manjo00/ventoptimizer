"""
validate_mimic.py — shadow-test the model's physiology against real patients.

Plain-language: we replay real ventilated patients and check whether the model's
physics actually matches what happened. Two experiments:

  Experiment 1 — Compliance stability:
      Our model assumes lung "stretchiness" (compliance) is a constant.
      Here we measure how much each patient's real compliance actually moves.
      If it moves a lot, the linear-compliance assumption is weak (Research Agenda Q1).

  Experiment 2 — Plateau-pressure prediction:
      When the clinician CHANGED a setting (tidal volume or PEEP), can the model
      predict the resulting plateau pressure using the patient's earlier compliance?
      The gap between predicted and measured = the model's real error.

It prints AGGREGATE numbers only (means, errors, counts) — NEVER patient rows.
Tested on the open MIMIC-IV demo (100 patients). For the full credentialed
MIMIC-IV, the credentialed user runs this SAME script locally (governance rule).

Usage:
  python engine/validate_mimic.py --demo data/mimic-iv-clinical-database-demo-2.2
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

# Make Unicode (→, —) print safely on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# MIMIC-IV chart itemids → the fields we care about (confirmed in the demo dictionary).
ITEMS = {
    224685: "vt",      # Tidal Volume (observed), mL
    220339: "peep",    # PEEP set, cmH2O
    224696: "pplat",   # Plateau Pressure, cmH2O  (the inspiratory-hold number)
    224695: "ppeak",   # Peak Insp. Pressure, cmH2O
    220210: "rr",      # Respiratory Rate
    223830: "ph",      # pH (Arterial)
    220235: "paco2",   # Arterial CO2 Pressure
}


def load_snapshots(demo_dir):
    """Read chartevents and build one row per (patient-stay, time) with the vent fields."""
    ce = os.path.join(demo_dir, "icu", "chartevents.csv.gz")
    df = pd.read_csv(ce, usecols=["stay_id", "charttime", "itemid", "valuenum"],
                     compression="gzip")
    df = df[df["itemid"].isin(ITEMS)].copy()
    df["field"] = df["itemid"].map(ITEMS)
    df["charttime"] = pd.to_datetime(df["charttime"])

    # One row per (stay, time); if a field was charted twice at the same minute, take the median.
    piv = (df.pivot_table(index=["stay_id", "charttime"], columns="field",
                          values="valuenum", aggfunc="median")
             .reset_index()
             .sort_values(["stay_id", "charttime"]))

    # Ventilator settings persist until changed → forward-fill them within each stay,
    # so a plateau reading lines up with the VT/PEEP in effect at that moment.
    for c in ["vt", "peep", "pplat", "ppeak", "rr"]:
        if c in piv.columns:
            piv[c] = piv.groupby("stay_id")[c].ffill()
    return piv


def physiologic_filter(d):
    """Keep plausible ventilated snapshots and compute compliance."""
    for c in ["vt", "peep", "pplat"]:
        if c not in d.columns:
            return d.iloc[0:0]
    d = d.dropna(subset=["vt", "peep", "pplat"]).copy()
    d = d[(d["pplat"] > d["peep"]) & (d["pplat"] <= 60) &
          (d["peep"] >= 0) & (d["peep"] <= 30) &
          (d["vt"] >= 100) & (d["vt"] <= 1500)]
    d["compliance"] = d["vt"] / (d["pplat"] - d["peep"])      # mL per cmH2O
    d = d[(d["compliance"] > 5) & (d["compliance"] < 200)]
    return d


def exp1_compliance_stability(d):
    """How much does each patient's compliance vary over time? (lower = model assumption safer)"""
    g = d.groupby("stay_id")["compliance"].agg(["count", "mean", "std"])
    g = g[g["count"] >= 3]                      # need a few readings to judge variation
    cv = (g["std"] / g["mean"]).dropna()        # coefficient of variation = spread ÷ average
    return {
        "patients_assessed": int(len(g)),
        "median_within_patient_variation_pct": round(float(cv.median() * 100), 1),
        "mean_within_patient_variation_pct": round(float(cv.mean() * 100), 1),
    }


def exp2_plateau_prediction(d, k=5):
    """When VT or PEEP changed, predict the new plateau pressure two ways and compare:
       BASELINE  — use the single most recent compliance reading.
       IMPROVED  — use the MEDIAN of the patient's last k compliance readings
                   (robust to one-off noisy readings).
       Also splits the baseline error by whether PEEP changed (a recruitment confound:
       compliance measured at the old PEEP may not hold at the new PEEP)."""
    err_base, err_improved, peep_changed = [], [], []
    for _, g in d.groupby("stay_id"):
        g = g.sort_values("charttime").reset_index(drop=True)
        comp = g["compliance"].to_numpy()
        vt = g["vt"].to_numpy()
        peep = g["peep"].to_numpy()
        pplat = g["pplat"].to_numpy()
        for i in range(1, len(g)):
            if not (abs(vt[i] - vt[i - 1]) >= 10 or abs(peep[i] - peep[i - 1]) >= 1):
                continue
            c_last = comp[i - 1]                       # baseline: last single reading
            c_robust = float(np.median(comp[max(0, i - k):i]))  # improved: median of last k
            err_base.append(peep[i] + vt[i] / c_last - pplat[i])
            err_improved.append(peep[i] + vt[i] / c_robust - pplat[i])
            peep_changed.append(abs(peep[i] - peep[i - 1]) >= 1)

    eb, ei, pc = np.array(err_base), np.array(err_improved), np.array(peep_changed)
    if eb.size == 0:
        return {"paired_setting_changes": 0}
    mae = lambda x: round(float(np.mean(np.abs(x))), 2) if x.size else None
    return {
        "paired_setting_changes": int(eb.size),
        "baseline_MAE_cmH2O (last reading)": mae(eb),
        f"improved_MAE_cmH2O (median of last {k})": mae(ei),
        "improvement_pct": round(float((np.mean(np.abs(eb)) - np.mean(np.abs(ei)))
                                       / np.mean(np.abs(eb)) * 100), 1),
        "within_2_cmH2O_pct (improved)": round(float(np.mean(np.abs(ei) <= 2) * 100), 1),
        "—diagnostic split (baseline)—": "",
        "VT-only changes: n / MAE": f"{int((~pc).sum())} / {mae(eb[~pc])}",
        "PEEP changes:    n / MAE": f"{int(pc.sum())} / {mae(eb[pc])}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", required=True, help="path to the extracted MIMIC-IV demo folder")
    args = ap.parse_args()

    print("=== VentOptimizer shadow test (aggregate results only — no patient data) ===\n")
    snaps = load_snapshots(args.demo)
    d = physiologic_filter(snaps)
    print(f"Usable ventilated snapshots (VT+PEEP+Pplat present): {len(d)} "
          f"from {d['stay_id'].nunique()} patients\n")

    print("Experiment 1 — is compliance really constant?")
    for k, v in exp1_compliance_stability(d).items():
        print(f"   {k}: {v}")
    print("   → higher variation = the linear-compliance assumption is weaker.\n")

    print("Experiment 2 — plateau prediction: baseline vs improved compliance")
    for k, v in exp2_plateau_prediction(d).items():
        print(f"   {k}: {v}")
    print("   → lower MAE = better. 'improvement_pct' is how much the robust")
    print("     compliance beat the single-last-reading baseline.")


if __name__ == "__main__":
    main()
