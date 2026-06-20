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


def exp3_peep_aware_compliance(d):
    """Model #2 — make compliance PEEP-aware (recruitment), LEARNED from the data.

    When PEEP changes, real compliance shifts (the lung recruits/over-distends). We:
      A) measure that shift from the data (descriptive), and
      B) test a corrected prediction HONESTLY: learn the PEEP→compliance slope on
         HALF the patients (train), then score it on the OTHER half (test), so we
         never grade our own homework. Corrected compliance = C_old × (1 + β·ΔPEEP).
    """
    rows = []
    for sid, g in d.groupby("stay_id"):
        g = g.sort_values("charttime").reset_index(drop=True)
        comp = g["compliance"].to_numpy()
        vt = g["vt"].to_numpy()
        peep = g["peep"].to_numpy()
        pplat = g["pplat"].to_numpy()
        for i in range(1, len(g)):
            dpeep = peep[i] - peep[i - 1]
            if abs(dpeep) < 1:                       # only PEEP-change events
                continue
            rows.append((int(sid), comp[i - 1], comp[i], dpeep, vt[i], peep[i], pplat[i]))
    if not rows:
        return {"peep_change_events": 0}

    df = pd.DataFrame(rows, columns=["sid", "c_before", "c_after", "dpeep", "vt", "peep", "pplat"])
    df["frac_change"] = (df["c_after"] - df["c_before"]) / df["c_before"]

    # A) descriptive: how did compliance move when PEEP went up vs down?
    up = df.loc[df["dpeep"] > 0, "frac_change"]
    down = df.loc[df["dpeep"] < 0, "frac_change"]

    # B) honest train/test by patient parity (even-id patients train, odd-id test)
    train, test = df[df["sid"] % 2 == 0], df[df["sid"] % 2 == 1]
    if len(train) < 5 or len(test) < 5:
        return {"peep_change_events": int(len(df)), "note": "too few events for a split"}

    # least-squares recruitment slope through the origin: frac_change ≈ β · ΔPEEP
    beta = float((train["frac_change"] * train["dpeep"]).sum() / (train["dpeep"] ** 2).sum())

    mae = lambda pred: round(float(np.mean(np.abs(pred - test["pplat"]))), 2)
    pred_base = test["peep"] + test["vt"] / test["c_before"]
    mult = (1 + beta * test["dpeep"]).clip(lower=0.3)          # keep compliance positive/sane
    pred_aware = test["peep"] + test["vt"] / (test["c_before"] * mult)

    mb, ma = mae(pred_base), mae(pred_aware)
    return {
        "peep_change_events_total": int(len(df)),
        "compliance_change_when_PEEP_UP_median_pct": round(float(up.median() * 100), 1) if len(up) else None,
        "compliance_change_when_PEEP_DOWN_median_pct": round(float(down.median() * 100), 1) if len(down) else None,
        "learned_slope_beta_per_cmH2O": round(beta, 4),
        "test_events": int(len(test)),
        "baseline_MAE_on_test": mb,
        "PEEP_aware_MAE_on_test": ma,
        "improvement_pct": round((mb - ma) / mb * 100, 1) if mb else None,
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
    print("     compliance beat the single-last-reading baseline.\n")

    print("Experiment 3 — PEEP-aware (recruitment) compliance, learned from data")
    for k, v in exp3_peep_aware_compliance(d).items():
        print(f"   {k}: {v}")
    print("   → does adjusting compliance for the PEEP change beat the baseline")
    print("     ON THE HELD-OUT TEST patients? (positive improvement_pct = yes)")


if __name__ == "__main__":
    main()
