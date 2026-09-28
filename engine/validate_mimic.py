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

  STEP 1b (2026-09-28) — the HONEST re-runs (experiments 1b, 2b, 3b):
      The original experiments carried the last plateau forward in time, so after a
      PEEP change they compared a NEW PEEP against an OLD plateau — which fakes a
      compliance change. The 1b versions use only plateaus that were actually
      measured, in a controlled ventilator mode, and pair them around a single PEEP
      step (the "usable pairs" defined in docs/_Required_Variables.md §3).

It prints AGGREGATE numbers only (means, errors, counts) — NEVER patient rows.
Tested on the open MIMIC-IV demo (100 patients). For the full credentialed
MIMIC-IV, the credentialed user runs this SAME script locally (governance rule).
The big table is read in slices, so it also works on the full data.

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

from physiology import estimate_vco2_ml_min   # Harris–Benedict CO2-production estimate

# MIMIC-IV chart itemids → the fields we care about (confirmed in the demo dictionary).
ITEMS = {
    224685: "vt",        # Tidal Volume (observed), mL
    220339: "peep",      # PEEP set, cmH2O
    224696: "pplat",     # Plateau Pressure, cmH2O  (the inspiratory-hold number)
    224695: "ppeak",     # Peak Insp. Pressure, cmH2O
    220210: "rr",        # Respiratory Rate
    224689: "rr_spont",  # Respiratory Rate (spontaneous) — > 0 means the patient is pulling breaths
    223830: "ph",        # pH (Arterial)
    220235: "paco2",     # Arterial CO2 Pressure
}
MODE_IDS = [223849, 229314]   # Ventilator Mode (Dräger vocabulary) / (Hamilton vocabulary) — text values

# Mode strings that mean CONTROLLED breaths (plateau and compliance are only meaningful there).
CONTROLLED_MODES = {"CMV/ASSIST/AutoFlow", "CMV/ASSIST", "CMV", "APV (cmv)", "P-CMV", "PCV+",
                    "SIMV", "SIMV/PSV", "SIMV/AutoFlow", "SIMV/PSV/AutoFlow", "PRVC/AC", "PRVC/SIMV"}


def read_filtered(path, usecols, keep_itemids, chunksize=2_000_000):
    """Read a big MIMIC table in slices, keeping only the item codes we care about.
    (Full MIMIC-IV chartevents is hundreds of millions of rows — never load it whole.)"""
    parts = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, compression="gzip"):
        parts.append(chunk[chunk["itemid"].isin(keep_itemids)])
    if not parts:
        return pd.DataFrame(columns=usecols)
    return pd.concat(parts, ignore_index=True)


def load_snapshots(demo_dir):
    """Read chartevents and build one row per (patient-stay, time) with the vent fields.

    Two extra columns matter for the honest (step-1b) experiments:
      pplat_fresh — True only where a plateau was actually charted at that time.
                    Settings (VT, PEEP, rate) are carried forward until changed, which is
                    right for settings; a carried plateau, however, is a STALE copy of an
                    older measurement, so we must know which rows are real measurements.
      controlled  — True when the ventilator mode in force is a controlled mode (plateau
                    and compliance mean nothing during pressure-support / spontaneous breathing).
    """
    ce = os.path.join(demo_dir, "icu", "chartevents.csv.gz")
    df = read_filtered(ce, ["stay_id", "charttime", "itemid", "value", "valuenum"],
                       list(ITEMS) + MODE_IDS)
    df["charttime"] = pd.to_datetime(df["charttime"])

    # the mode is text; everything else is a number
    mode = (df[df["itemid"].isin(MODE_IDS)][["stay_id", "charttime", "value"]]
              .rename(columns={"value": "mode"})
              .sort_values(["stay_id", "charttime"])
              .drop_duplicates(["stay_id", "charttime"], keep="last"))
    num = df[df["itemid"].isin(ITEMS)].copy()
    num["field"] = num["itemid"].map(ITEMS)

    # One row per (stay, time); if a field was charted twice at the same minute, take the median.
    piv = (num.pivot_table(index=["stay_id", "charttime"], columns="field",
                           values="valuenum", aggfunc="median")
              .reset_index()
              .sort_values(["stay_id", "charttime"]))
    for c in ["vt", "peep", "pplat", "ppeak", "rr", "rr_spont"]:
        if c not in piv.columns:
            piv[c] = np.nan
    piv["pplat_fresh"] = piv["pplat"].notna()          # remember which plateaus are REAL measurements

    # Ventilator settings persist until changed → forward-fill them within each stay,
    # so a plateau reading lines up with the VT/PEEP in effect at that moment.
    for c in ["vt", "peep", "pplat", "ppeak", "rr", "rr_spont"]:
        piv[c] = piv.groupby("stay_id")[c].ffill()

    # attach the ventilator mode in force at each row (the last mode charted at or before it)
    piv = pd.merge_asof(piv.sort_values("charttime"), mode.sort_values("charttime"),
                        on="charttime", by="stay_id", direction="backward")
    piv = piv.sort_values(["stay_id", "charttime"]).reset_index(drop=True)
    piv["controlled"] = piv["mode"].isin(CONTROLLED_MODES)
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


# ---------------------------------------------------------------------------
# STEP 1b (2026-09-28) — the HONEST versions of experiments 1–3.
# Unit of analysis = a REAL plateau measurement (pplat_fresh), never a carried value.
# ---------------------------------------------------------------------------

def fresh_plateaus(snaps):
    """Only the rows where a plateau was actually measured, with the settings in force at
    that moment, plausibility-filtered, with compliance computed."""
    f = snaps[snaps["pplat_fresh"]].copy()
    f = physiologic_filter(f)
    return f.sort_values(["stay_id", "charttime"]).reset_index(drop=True)


def peep_change_times(snaps):
    """{stay_id: table of (charttime, new PEEP)} — every moment the PEEP setting changed."""
    out = {}
    for sid, g in snaps.dropna(subset=["peep"]).groupby("stay_id"):
        g = g.sort_values("charttime")
        prev = g["peep"].shift()
        changed = g["peep"].ne(prev) & prev.notna()
        out[sid] = g.loc[changed, ["charttime", "peep"]].reset_index(drop=True)
    return out


def usable_peep_pairs(snaps, fresh, after_h=4.0):
    """Build the trustworthy before/after pairs around a PEEP change.

    A pair = two consecutive REAL plateau measurements in the same stay with
      * exactly ONE PEEP change between them (a single step — no ambiguity about which
        PEEP each plateau belongs to: 'before' was measured at the old PEEP, 'after' at the new),
      * the 'after' plateau measured within `after_h` hours of that step,
      * a controlled ventilator mode on both sides.
    Also returns a funnel (how many pairs each rule removes) and sensitivity flags
    (no spontaneous breaths charted; 'before' plateau at most 12 h old)."""
    changes = peep_change_times(snaps)
    rows, n_any = [], 0
    for sid, g in fresh.groupby("stay_id"):
        g = g.reset_index(drop=True)
        ch = changes.get(sid)
        for i in range(1, len(g)):
            if abs(g["peep"][i] - g["peep"][i - 1]) < 1:
                continue
            n_any += 1
            t0, t1 = g["charttime"][i - 1], g["charttime"][i]
            if ch is None:
                continue
            between = ch[(ch["charttime"] > t0) & (ch["charttime"] <= t1)]
            if len(between) != 1:
                continue                                   # zero or several steps → ambiguous → skip
            t_change = between["charttime"].iloc[0]
            spont0, spont1 = g["rr_spont"][i - 1], g["rr_spont"][i]
            rows.append({
                "stay_id": sid, "t_before": t0, "t_change": t_change, "t_after": t1,
                "peep_before": g["peep"][i - 1], "peep_after": g["peep"][i],
                "vt_before": g["vt"][i - 1], "vt_after": g["vt"][i],
                "pplat_before": g["pplat"][i - 1], "pplat_after": g["pplat"][i],
                "c_before": g["compliance"][i - 1], "c_after": g["compliance"][i],
                "hours_before": (t_change - t0) / pd.Timedelta(hours=1),
                "hours_after": (t1 - t_change) / pd.Timedelta(hours=1),
                "controlled_both": bool(g["controlled"][i - 1] and g["controlled"][i]),
                "spont_zero_both": bool((pd.isna(spont0) or spont0 == 0) and (pd.isna(spont1) or spont1 == 0)),
            })
    p = pd.DataFrame(rows)
    if len(p) == 0:
        return p, {"consecutive real-plateau pairs with a PEEP difference": n_any}
    p["dpeep"] = p["peep_after"] - p["peep_before"]
    p["frac_change"] = (p["c_after"] - p["c_before"]) / p["c_before"]
    in_window = p["hours_after"] <= after_h
    usable_mask = in_window & p["controlled_both"]
    funnel = {
        "consecutive real-plateau pairs with a PEEP difference": int(n_any),
        "...with exactly ONE PEEP step between them": int(len(p)),
        f"...AND 'after' plateau within {after_h:g} h of the step": int(in_window.sum()),
        "...AND controlled mode on both sides  (= USABLE)": int(usable_mask.sum()),
        "...AND no spontaneous breaths charted (sensitivity)": int((usable_mask & p["spont_zero_both"]).sum()),
        "...AND 'before' plateau <= 12 h old (sensitivity)": int((usable_mask & (p["hours_before"] <= 12)).sum()),
    }
    return p[usable_mask].reset_index(drop=True), funnel


def exp1b_compliance_stability_fresh(fresh):
    """Experiment 1, honestly: within-patient compliance variation using only REAL plateaus
    measured in a controlled mode."""
    f = fresh[fresh["controlled"]]
    g = f.groupby("stay_id")["compliance"].agg(["count", "mean", "std"])
    g = g[g["count"] >= 3]
    cv = (g["std"] / g["mean"]).dropna()
    return {
        "patients_assessed": int(len(g)),
        "median_within_patient_variation_pct": round(float(cv.median() * 100), 1) if len(cv) else None,
    }


def exp2b_fresh_plateau_prediction(fresh, max_gap_h=12.0):
    """Experiment 2, honestly: predict each REAL plateau from the previous REAL plateau's
    compliance (both in a controlled mode, at most `max_gap_h` apart) and split the error by
    what changed in between: nothing (= the measurement noise floor), tidal volume only, or PEEP.
    Prediction: Pplat = PEEP_now + VT_now / C_previous."""
    groups = {"no change (noise floor)": [], "VT-only change": [], "PEEP change": []}
    gap = pd.Timedelta(hours=max_gap_h)
    for sid, g in fresh.groupby("stay_id"):
        g = g.reset_index(drop=True)
        for i in range(1, len(g)):
            if not (g["controlled"][i - 1] and g["controlled"][i]):
                continue
            if (g["charttime"][i] - g["charttime"][i - 1]) > gap:
                continue
            err = g["peep"][i] + g["vt"][i] / g["compliance"][i - 1] - g["pplat"][i]
            if abs(g["peep"][i] - g["peep"][i - 1]) >= 1:
                key = "PEEP change"
            elif abs(g["vt"][i] - g["vt"][i - 1]) >= 10:
                key = "VT-only change"
            else:
                key = "no change (noise floor)"
            groups[key].append(err)
    out = {}
    for k, v in groups.items():
        a = np.abs(np.array(v))
        if a.size:
            out[f"{k}: n / MAE / within 2 cmH2O"] = f"{a.size} / {a.mean():.2f} / {(a <= 2).mean() * 100:.0f}%"
        else:
            out[f"{k}: n / MAE / within 2 cmH2O"] = "0 / — / —"
    return out


def exp3b_recruitment_on_usable_pairs(pairs, n_boot=2000, seed=0):
    """Experiment 3, honestly: how does REAL measured compliance move across a PEEP step?
       A) descriptive — median % change when PEEP went up / down, and how often compliance
          moved the 'expected' way (up with PEEP up, down with PEEP down);
       B) the recruitment slope β in  C_after ≈ C_before × (1 + β·ΔPEEP), least squares through
          the origin, with a bootstrap 95% interval (re-sample the pairs 2,000 times);
       C) an honest prediction test — leave-one-stay-out: fit β on every OTHER stay, predict this
          stay's after-plateau, pool the errors. Baseline = keep C_before unchanged."""
    if len(pairs) == 0:
        return {"usable_pairs": 0}
    up, down = pairs[pairs["dpeep"] > 0], pairs[pairs["dpeep"] < 0]
    fc, dp = pairs["frac_change"].to_numpy(), pairs["dpeep"].to_numpy()
    beta = float((fc * dp).sum() / (dp ** 2).sum())
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(pairs), len(pairs))
        boots.append((fc[idx] * dp[idx]).sum() / (dp[idx] ** 2).sum())
    lo, hi = np.percentile(boots, [2.5, 97.5])

    err_base, err_aware = [], []
    for sid in pairs["stay_id"].unique():
        train, test = pairs[pairs["stay_id"] != sid], pairs[pairs["stay_id"] == sid]
        if len(train) < 3:
            continue
        b = float((train["frac_change"] * train["dpeep"]).sum() / (train["dpeep"] ** 2).sum())
        mult = (1 + b * test["dpeep"]).clip(lower=0.3)          # keep compliance positive/sane
        err_base.extend((test["peep_after"] + test["vt_after"] / test["c_before"] - test["pplat_after"]).tolist())
        err_aware.extend((test["peep_after"] + test["vt_after"] / (test["c_before"] * mult) - test["pplat_after"]).tolist())
    eb, ea = np.abs(np.array(err_base)), np.abs(np.array(err_aware))

    def med_iqr(x):
        x = np.asarray(x) * 100
        if x.size == 0:
            return "—"
        return f"{np.median(x):+.1f}% [IQR {np.percentile(x, 25):+.1f} to {np.percentile(x, 75):+.1f}]"

    return {
        "usable_pairs": int(len(pairs)),
        "stays": int(pairs["stay_id"].nunique()),
        "PEEP_up_pairs / PEEP_down_pairs": f"{len(up)} / {len(down)}",
        "median_|dPEEP|_cmH2O": float(pairs["dpeep"].abs().median()),
        "compliance_change_when_PEEP_UP (median)": med_iqr(up["frac_change"]),
        "compliance_change_when_PEEP_DOWN (median)": med_iqr(down["frac_change"]),
        "share_of_PEEP_UP_pairs_where_compliance_ROSE_pct": round(float((up["frac_change"] > 0).mean() * 100), 0) if len(up) else None,
        "share_of_PEEP_DOWN_pairs_where_compliance_FELL_pct": round(float((down["frac_change"] < 0).mean() * 100), 0) if len(down) else None,
        "learned_slope_beta_per_cmH2O": round(beta, 4),
        "beta_95pct_bootstrap_interval": f"[{lo:+.4f}, {hi:+.4f}]",
        "LOSO_test_pairs": int(eb.size),
        "baseline_MAE_cmH2O (C unchanged)": round(float(eb.mean()), 2) if eb.size else None,
        "PEEP_aware_MAE_cmH2O (C × (1+β·ΔPEEP))": round(float(ea.mean()), 2) if ea.size else None,
        "improvement_pct": round(float((eb.mean() - ea.mean()) / eb.mean() * 100), 1) if eb.size else None,
        "median_abs_error_cmH2O (baseline / aware)": f"{np.median(eb):.2f} / {np.median(ea):.2f}" if eb.size else None,
    }


def load_demographics(demo_dir):
    """Per-patient age, sex, height, weight, PBW — needed for the Harris–Benedict dead space."""
    icu = pd.read_csv(os.path.join(demo_dir, "icu", "icustays.csv.gz"),
                      usecols=["subject_id", "stay_id"], compression="gzip")
    pat = pd.read_csv(os.path.join(demo_dir, "hosp", "patients.csv.gz"),
                      usecols=["subject_id", "gender", "anchor_age"], compression="gzip").set_index("subject_id")
    ce = read_filtered(os.path.join(demo_dir, "icu", "chartevents.csv.gz"),
                       ["stay_id", "itemid", "valuenum"], [226730, 226512, 224639])
    height = ce[ce["itemid"] == 226730].groupby("stay_id")["valuenum"].median()   # Height (cm)
    weight = ce[ce["itemid"].isin([226512, 224639])].groupby("stay_id")["valuenum"].median()  # weight kg

    s2subj = dict(zip(icu["stay_id"], icu["subject_id"]))
    demo = {}
    for sid in icu["stay_id"].unique():
        subj = s2subj.get(sid)
        if subj not in pat.index:
            continue
        h = height.get(sid)
        if h is None or pd.isna(h):
            continue
        sex = "M" if str(pat.loc[subj, "gender"]).upper().startswith("M") else "F"
        pbw = (50 if sex == "M" else 45.5) + 0.91 * (float(h) - 152.4)   # Devine PBW
        w = weight.get(sid)
        demo[int(sid)] = {
            "age": float(pat.loc[subj, "anchor_age"]), "sex": sex, "height": float(h),
            "weight": float(w) if (w is not None and not pd.isna(w)) else pbw, "pbw": pbw,
        }
    return demo


def exp4_co2_prediction(snaps, demo):
    """Predict the next arterial CO2 after a TIDAL-VOLUME change, two ways:
       BASELINE — fixed anatomic dead space (2.2 mL/kg).
       HARRIS–BENEDICT — physiological dead space from the patient's CO2 production.
    Dead space only changes the prediction when VT changes, so we use VT-change ABG pairs.
    No train/test needed — HB is a fixed published equation, nothing is fitted to the data."""
    d = snaps.dropna(subset=["paco2", "vt", "rr"]).copy()
    d = d[(d["paco2"] > 10) & (d["paco2"] < 150) & (d["vt"] >= 100) & (d["vt"] <= 1500) &
          (d["rr"] > 0) & (d["rr"] <= 60)]
    err_fixed, err_hb = [], []
    for sid, g in d.groupby("stay_id"):
        info = demo.get(int(sid))
        if not info:
            continue
        pbw = info["pbw"]
        vco2 = estimate_vco2_ml_min(info["age"], info["sex"], info["weight"], info["height"])
        g = g.sort_values("charttime").reset_index(drop=True)
        vt, rr, co = g["vt"].to_numpy(), g["rr"].to_numpy(), g["paco2"].to_numpy()
        for i in range(1, len(g)):
            if abs(vt[i] - vt[i - 1]) < 30:           # need a real VT change
                continue
            vd_fixed = 2.2 * pbw
            vd_hb = vd_fixed
            if vco2 and co[i - 1] > 0:
                ve0 = (vt[i - 1] / 1000.0) * rr[i - 1]
                vd_vt = min(max(1.0 - (vco2 * 0.863) / (co[i - 1] * ve0), 0.1), 0.85)
                vd_hb = vd_vt * vt[i - 1]
            va0f, va1f = (vt[i - 1] - vd_fixed) * rr[i - 1], (vt[i] - vd_fixed) * rr[i]
            va0h, va1h = (vt[i - 1] - vd_hb) * rr[i - 1], (vt[i] - vd_hb) * rr[i]
            if min(va0f, va1f, va0h, va1h) <= 0:
                continue
            err_fixed.append(co[i - 1] * va0f / va1f - co[i])     # predicted − measured
            err_hb.append(co[i - 1] * va0h / va1h - co[i])
    ef, eh = np.array(err_fixed), np.array(err_hb)
    if ef.size == 0:
        return {"vt_change_abg_pairs": 0}
    mae = lambda x: round(float(np.mean(np.abs(x))), 2)
    return {
        "vt_change_abg_pairs": int(ef.size),
        "baseline_MAE_mmHg (fixed 2.2/kg)": mae(ef),
        "harris_benedict_MAE_mmHg": mae(eh),
        "improvement_pct": round(float((np.mean(np.abs(ef)) - np.mean(np.abs(eh)))
                                       / np.mean(np.abs(ef)) * 100), 1),
    }


def exp5_mp_reduction_available(snaps, demo):
    """The tool's core value on real patients: how much mechanical power could be
    SAFELY saved by redistributing tidal volume <-> rate, with PEEP held, alveolar
    ventilation (CO2 clearance) preserved, VT kept 4-8 mL/kg, and plateau <= 30 —
    using each patient's OWN measured mechanics. Achievable MP vs delivered MP."""
    d = snaps.dropna(subset=["vt", "rr", "peep", "pplat", "ppeak"]).copy()
    d = d[(d["pplat"] > d["peep"]) & (d["pplat"] <= 40) & (d["ppeak"] >= d["pplat"]) &
          (d["vt"] >= 100) & (d["vt"] <= 1200) & (d["rr"] > 0) & (d["rr"] <= 45)]

    def mp(rr, vt_ml, ppeak, pplat, peep):
        return 0.098 * rr * (vt_ml / 1000.0) * (ppeak - 0.5 * (pplat - peep))

    actual_mps, reductions = [], []
    for sid, g in d.groupby("stay_id"):
        info = demo.get(int(sid))
        if not info:
            continue
        pbw = info["pbw"]
        vd = 2.2 * pbw
        for vt0, rr0, peep, pplat, ppeak in zip(g["vt"], g["rr"], g["peep"], g["pplat"], g["ppeak"]):
            if (pplat - peep) <= 0 or (vt0 - vd) <= 0:
                continue
            C = vt0 / (pplat - peep)                 # the patient's OWN measured compliance
            gap = ppeak - pplat                      # their OWN resistive gap
            va_target = (vt0 - vd) * rr0             # alveolar ventilation to preserve (keeps CO2 ~constant)
            actual = mp(rr0, vt0, ppeak, pplat, peep)
            best = actual
            for vt in range(int(4 * pbw), int(8 * pbw) + 1, 5):   # lung-protective VT window
                if (vt - vd) <= 0:
                    continue
                rr = va_target / (vt - vd)           # rate that preserves alveolar ventilation
                if rr < 5 or rr > 35:
                    continue
                pplat_new = peep + vt / C
                if pplat_new > 30:                   # plateau safety cap
                    continue
                m = mp(rr, vt, pplat_new + gap, pplat_new, peep)
                if m < best:
                    best = m
            actual_mps.append(actual)
            reductions.append(actual - best)

    if not reductions:
        return {"snapshots": 0}
    r, a = np.array(reductions), np.array(actual_mps)
    return {
        "snapshots": int(r.size),
        "median_delivered_MP_Jmin": round(float(np.median(a)), 1),
        "median_MP_savable_Jmin": round(float(np.median(r)), 2),
        "mean_MP_savable_Jmin": round(float(np.mean(r)), 2),
        "pct_snapshots_>=1_Jmin_savable": round(float(np.mean(r >= 1) * 100), 1),
        "pct_snapshots_>=3_Jmin_savable": round(float(np.mean(r >= 3) * 100), 1),
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

    print("Experiment 1 — is compliance really constant?   [OLD METHOD — carried plateaus]")
    for k, v in exp1_compliance_stability(d).items():
        print(f"   {k}: {v}")
    print("   → higher variation = the linear-compliance assumption is weaker.\n")

    print("Experiment 2 — plateau prediction: baseline vs improved compliance   [OLD METHOD — carried plateaus; SUSPECT, comparison only]")
    for k, v in exp2_plateau_prediction(d).items():
        print(f"   {k}: {v}")
    print("   → lower MAE = better. 'improvement_pct' is how much the robust")
    print("     compliance beat the single-last-reading baseline.\n")

    print("Experiment 3 — PEEP-aware (recruitment) compliance, learned from data   [OLD METHOD — carried plateaus; SUSPECT, comparison only]")
    for k, v in exp3_peep_aware_compliance(d).items():
        print(f"   {k}: {v}")
    print("   → does adjusting compliance for the PEEP change beat the baseline")
    print("     ON THE HELD-OUT TEST patients? (positive improvement_pct = yes)\n")

    print("=" * 78)
    print("STEP 1b — HONEST RE-RUN on REAL plateau measurements only (no carried plateaus)")
    print("=" * 78)
    fresh = fresh_plateaus(snaps)
    print(f"Real plateau measurements (plausible): {len(fresh)} in {fresh['stay_id'].nunique()} stays; "
          f"in a controlled mode: {int(fresh['controlled'].sum())}\n")

    print("Experiment 1b — within-patient compliance variation (real, controlled plateaus only)")
    for k, v in exp1b_compliance_stability_fresh(fresh).items():
        print(f"   {k}: {v}")
    print()

    print("Experiment 2b — plateau prediction error by what changed (real plateaus, controlled, <= 12 h apart)")
    for k, v in exp2b_fresh_plateau_prediction(fresh).items():
        print(f"   {k}: {v}")
    print("   → 'no change' = the measurement noise floor; PEEP-change error above it = the real recruitment effect.\n")

    pairs, funnel = usable_peep_pairs(snaps, fresh)
    print("Experiment 3b — recruitment across ONE PEEP step, USABLE pairs only")
    print("   funnel:")
    for k, v in funnel.items():
        print(f"      {k}: {v}")
    for k, v in exp3b_recruitment_on_usable_pairs(pairs).items():
        print(f"   {k}: {v}")
    print("   → β and the leave-one-stay-out MAE are the honest replacements for the old exp3 numbers.\n")

    print("Experiment 4 — CO2 prediction: anatomic dead space vs Harris–Benedict")
    demo = load_demographics(args.demo)
    print(f"   demographics available for {len(demo)} stays")
    for k, v in exp4_co2_prediction(snaps, demo).items():
        print(f"   {k}: {v}")
    print("   → lower MAE = better; positive improvement_pct = HB beats the fixed rule.\n")

    print("Experiment 5 — how much mechanical power could be SAFELY saved (VT↔RR, PEEP held)")
    for k, v in exp5_mp_reduction_available(snaps, demo).items():
        print(f"   {k}: {v}")
    print("   → the tool's core value: lower power at the same CO2 clearance, within limits.")


if __name__ == "__main__":
    main()
