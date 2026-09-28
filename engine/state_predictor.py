"""
state_predictor.py — STEP 2b: the PRE-SPECIFIED full-MIMIC analysis (decision (c), 2026-09-28).

Plain-language: steps 1b and 2a showed that neither one population rule nor a patient's
last PEEP step predicts how their compliance responds to a PEEP change. Ahmed chose
option (c): try to predict the response from the patient's STATE before the step
(PEEP level, direction, lung stiffness, oxygenation, CO2, body size, days on the
ventilator) on the full MIMIC-IV, AND keep a small reversible "test step" as the
safety net whenever the prediction is uncertain.

This script IS the analysis plan in code (docs/_Analysis_Plan_FullMIMIC.md is the same
plan in words, written before the full data is touched). It answers, in order:

  Q2  population response at scale — size, direction, spread, slope β with an interval
  Q4  noise floor vs step size — is the signal clearer with bigger PEEP steps?
  Q1  the STATE MODEL — can pre-step state predict the compliance change better than
      "no change", judged on patients the model never saw (grouped cross-validation),
      with an 80% prediction interval whose coverage we check?  → H1 verdict
  Q3  the TEST STEP — does a first small step predict the next one in the same
      direction (the 'verify' half of option (c))?
  Q5  the OVERDISTENSION signal — how often compliance FALLS when PEEP goes up, by
      PEEP level and driving pressure (feeds sub-problem 1: the highest safe PEEP)
  S   sensitivity definitions of a usable pair

Pre-specified rules that the code enforces:
  * model results are labelled UNDERPOWERED when there are fewer than MIN_N_MODEL pairs
    (the demo has ~27 — it only tests that the pipeline runs);
  * every stratified table suppresses cells with fewer than MIN_CELL pairs;
  * aggregate output only — never a patient row or identifier.

Usage:
  python engine/state_predictor.py --mimic data/mimic-iv-clinical-database-demo-2.2
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from validate_mimic import (load_snapshots, fresh_plateaus, usable_peep_pairs, read_filtered,
                            load_demographics, exp3b_recruitment_on_usable_pairs)

MIN_N_MODEL = 300          # pre-specified minimum usable pairs before the model result counts
MIN_CELL = 10              # pre-specified: never report a subgroup with fewer pairs than this
K_FOLDS, REPEATS = 5, 3    # grouped cross-validation by patient, repeated with different shuffles
LAMBDA_GRID = [0.1, 1.0, 10.0, 100.0]   # pre-specified ridge penalties; the one used is chosen by INNER grouped CV
CLIP = (-0.7, 1.5)         # pre-specified plausibility clip: a predicted compliance change is held to −70% … +150%
NOISE_THRESHOLD = 0.10     # |compliance change| above 10% counts as a real move (the demo noise floor)
H1_MAE_GAIN = 0.15         # H1: the state model must cut the after-step plateau MAE by >= 15% ...
H1_COVERAGE = 0.75         # ... AND its 80% prediction interval must cover >= 75% of observed values

# pre-step state signals: last value at or before the step, within a look-back window (hours)
SIGNALS = {220277: "spo2", 223835: "fio2", 220224: "pao2", 220235: "paco2", 223830: "ph"}
WINDOW_H = {"spo2": 4, "fio2": 24, "pao2": 12, "paco2": 12, "ph": 12}
PC_MODES = {"P-CMV", "PCV+"}

FEATURES = ["dpeep", "peep_before", "peep_sq", "dpeep_x_peep", "c_before", "dpeep_x_c", "dp_before",
            "vt_per_pbw", "sf_ratio", "dpeep_x_sf", "paco2", "ph", "bmi", "age", "male",
            "days_on_vent", "is_pc"]


# ----------------------------------------------------------------------------------
# 1. attach the pre-step STATE to every usable pair
# ----------------------------------------------------------------------------------
def attach_state(pairs, mimic, snaps):
    """Add the pre-step state features to each usable pair: gases/oxygenation (last reading
    before the step within a window), body size, age, sex, days on the ventilator, mode family."""
    p = pairs.sort_values("t_change").reset_index(drop=True)

    ce = read_filtered(os.path.join(mimic, "icu", "chartevents.csv.gz"),
                       ["stay_id", "charttime", "itemid", "valuenum"], list(SIGNALS))
    ce["charttime"] = pd.to_datetime(ce["charttime"])
    for iid, name in SIGNALS.items():
        s = (ce[ce["itemid"] == iid][["stay_id", "charttime", "valuenum"]]
               .rename(columns={"valuenum": name, "charttime": "t_sig"}).sort_values("t_sig"))
        p = pd.merge_asof(p.sort_values("t_change"), s, left_on="t_change", right_on="t_sig", by="stay_id",
                          direction="backward", tolerance=pd.Timedelta(hours=WINDOW_H[name]))
        p = p.drop(columns=["t_sig"])
    p = p.sort_values(["stay_id", "t_change"]).reset_index(drop=True)

    # FiO2 is charted as a percent (40) on most ventilators and as a fraction (0.4) on some
    fio2 = p["fio2"].where(p["fio2"] <= 1.0, p["fio2"] / 100.0)
    p["sf_ratio"] = p["spo2"] / fio2
    p["pf_ratio"] = p["pao2"] / fio2

    demo = load_demographics(mimic)             # only stays with a charted height (needed for PBW)
    get = lambda s, key: demo.get(int(s), {}).get(key, np.nan)
    p["pbw"] = p["stay_id"].map(lambda s: get(s, "pbw"))
    p["age"] = p["stay_id"].map(lambda s: get(s, "age"))
    p["male"] = p["stay_id"].map(lambda s: 1.0 if demo.get(int(s), {}).get("sex") == "M" else (0.0 if int(s) in demo else np.nan))
    p["bmi"] = p["stay_id"].map(lambda s: get(s, "weight") / (get(s, "height") / 100.0) ** 2 if int(s) in demo else np.nan)

    # days on the ventilator at the moment of the step (procedure record; fallback = first vent setting)
    pe = read_filtered(os.path.join(mimic, "icu", "procedureevents.csv.gz"), ["stay_id", "itemid", "starttime"], [225792])
    pe["starttime"] = pd.to_datetime(pe["starttime"])
    first_start = pe.groupby("stay_id")["starttime"].min()
    fallback = snaps.dropna(subset=["peep"]).groupby("stay_id")["charttime"].min()
    start = pd.Series(first_start.reindex(p["stay_id"]).to_numpy(), index=p.index)
    start = start.fillna(pd.Series(fallback.reindex(p["stay_id"]).to_numpy(), index=p.index))
    p["days_on_vent"] = (p["t_change"] - start).dt.total_seconds() / 86400.0

    # ventilator mode family at the 'before' plateau (pressure-controlled vs volume-controlled)
    modes = snaps[["stay_id", "charttime", "mode"]].dropna(subset=["mode"]).sort_values("charttime")
    p = pd.merge_asof(p.sort_values("t_before"), modes, left_on="t_before", right_on="charttime",
                      by="stay_id", direction="backward").drop(columns=["charttime"])
    p = p.sort_values(["stay_id", "t_change"]).reset_index(drop=True)
    p["is_pc"] = p["mode"].isin(PC_MODES).astype(float)

    # derived mechanics + the pre-specified interaction terms
    p["dp_before"] = p["pplat_before"] - p["peep_before"]
    p["vt_per_pbw"] = p["vt_before"] / p["pbw"]
    p["peep_sq"] = p["peep_before"] ** 2
    p["dpeep_x_peep"] = p["dpeep"] * p["peep_before"]
    p["dpeep_x_c"] = p["dpeep"] * p["c_before"]
    p["dpeep_x_sf"] = p["dpeep"] * p["sf_ratio"]

    # subject id (for grouping the cross-validation by PATIENT, not by stay)
    icu = pd.read_csv(os.path.join(mimic, "icu", "icustays.csv.gz"), usecols=["stay_id", "subject_id"])
    p["subject_id"] = p["stay_id"].map(dict(zip(icu["stay_id"], icu["subject_id"])))
    return p


# ----------------------------------------------------------------------------------
# 2. the models (plain numpy so the script runs on any machine)
# ----------------------------------------------------------------------------------
def ridge_fit(X, y, lam=10.0):
    """Ridge regression on standardized features; missing values → training-fold mean."""
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd[~np.isfinite(sd) | (sd == 0)] = 1.0
    mu[~np.isfinite(mu)] = 0.0
    Xs = (np.where(np.isnan(X), mu, X) - mu) / sd
    A = np.c_[np.ones(len(Xs)), Xs]
    pen = np.eye(A.shape[1]) * lam
    pen[0, 0] = 0.0                                     # never shrink the intercept
    w = np.linalg.solve(A.T @ A + pen, A.T @ y)
    return w, mu, sd


def ridge_predict(model, X):
    w, mu, sd = model
    Xs = (np.where(np.isnan(X), mu, X) - mu) / sd
    return np.c_[np.ones(len(Xs)), Xs] @ w


def fit_beta(df):
    return float((df["frac_change"] * df["dpeep"]).sum() / (df["dpeep"] ** 2).sum())


def grouped_folds(subjects, k, seed):
    """Assign every PATIENT (not stay, not pair) to one of k folds."""
    uniq = np.unique(subjects)
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    fold_of = {s: i % k for i, s in enumerate(uniq)}
    return np.array([fold_of[s] for s in subjects])


def choose_lambda(X, y, subjects, seed=0):
    """Pick the ridge penalty by an INNER 3-fold grouped CV on the training patients only
    (so the test patients never influence the choice). Falls back to 10 when too few patients."""
    if len(np.unique(subjects)) < 6:
        return 10.0
    folds = grouped_folds(subjects, 3, seed)
    best, best_mae = 10.0, np.inf
    for lam in LAMBDA_GRID:
        errs = []
        for f in range(3):
            tr, te = folds != f, folds == f
            if te.sum() == 0 or tr.sum() < 5:
                continue
            m = ridge_fit(X[tr], y[tr], lam)
            errs.append(np.abs(np.clip(ridge_predict(m, X[te]), *CLIP) - y[te]).mean())
        mae = float(np.mean(errs)) if errs else np.inf
        if mae < best_mae:
            best, best_mae = lam, mae
    return best


def rank_auc(score, label):
    """Area under the ROC curve by ranks (Mann–Whitney). None if one class is missing."""
    label = np.asarray(label, bool)
    if label.all() or (~label).all():
        return None
    r = pd.Series(score).rank().to_numpy()
    n1, n0 = label.sum(), (~label).sum()
    return float((r[label].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def try_gbm():
    """Optional model M3 (quantile gradient boosting) — only if scikit-learn is installed."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor
    except Exception:
        return None


# ----------------------------------------------------------------------------------
# 3. Q1 — the state model, judged on unseen patients
# ----------------------------------------------------------------------------------
def q1_state_model(p):
    X = p[FEATURES].to_numpy(float)
    y = p["frac_change"].to_numpy(float)
    subjects = p["subject_id"].to_numpy()
    GBM = try_gbm()
    preds = {"M0 baseline (no change)": [], "M1 population slope": [], "M2 state model (ridge)": []}
    if GBM is not None:
        preds["M3 state model (gradient boosting)"] = []
    lo_all, hi_all, y_all, idx_all = [], [], [], []

    for rep in range(REPEATS):
        folds = grouped_folds(subjects, K_FOLDS, seed=rep)
        for f in range(K_FOLDS):
            tr, te = folds != f, folds == f
            if te.sum() == 0 or tr.sum() < 5:
                continue
            lam = choose_lambda(X[tr], y[tr], subjects[tr], seed=rep)
            m2 = ridge_fit(X[tr], y[tr], lam)
            yhat_tr = np.clip(ridge_predict(m2, X[tr]), *CLIP)
            q10, q90 = np.percentile(yhat_tr - y[tr], [10, 90])      # residual quantiles → 80% interval
            yhat_te = np.clip(ridge_predict(m2, X[te]), *CLIP)
            beta = fit_beta(p[tr])
            preds["M0 baseline (no change)"].append((np.where(te)[0], np.zeros(te.sum())))
            preds["M1 population slope"].append((np.where(te)[0], np.clip(beta * p.loc[te, "dpeep"].to_numpy(), *CLIP)))
            preds["M2 state model (ridge)"].append((np.where(te)[0], yhat_te))
            lo_all.append(yhat_te - q90)
            hi_all.append(yhat_te - q10)
            y_all.append(y[te])
            idx_all.append(np.where(te)[0])
            if GBM is not None:
                Xtr = np.where(np.isnan(X[tr]), np.nanmean(X[tr], 0), X[tr])
                Xte = np.where(np.isnan(X[te]), np.nanmean(X[tr], 0), X[te])
                g = GBM(max_depth=3, learning_rate=0.05, max_iter=200, random_state=rep).fit(Xtr, y[tr])
                preds["M3 state model (gradient boosting)"].append((np.where(te)[0], np.clip(g.predict(Xte), *CLIP)))

    out, mae_by = {}, {}
    for name, chunks in preds.items():
        idx = np.concatenate([c[0] for c in chunks])
        yh = np.concatenate([c[1] for c in chunks])
        r = p.iloc[idx]
        c_pred = r["c_before"].to_numpy() * np.maximum(1 + yh, 0.3)
        plat_err = r["peep_after"].to_numpy() + r["vt_after"].to_numpy() / c_pred - r["pplat_after"].to_numpy()
        frac_err = yh - y[idx]
        real_move = np.abs(y[idx]) > NOISE_THRESHOLD
        direction = (np.sign(yh) == np.sign(y[idx]))[real_move]
        line = (f"plateau MAE {np.abs(plat_err).mean():.2f} cmH2O | compliance-change MAE {np.abs(frac_err).mean() * 100:.1f}%")
        if name != "M0 baseline (no change)" and real_move.sum() >= MIN_CELL:
            line += f" | direction correct (moves > {NOISE_THRESHOLD:.0%}) {direction.mean() * 100:.0f}% (n={real_move.sum()} predictions over {REPEATS} repeats)"
        up = r["dpeep"].to_numpy() > 0
        if name.startswith("M2") or name.startswith("M3"):
            auc = rank_auc(-yh[up], y[idx][up] < -NOISE_THRESHOLD) if up.sum() >= MIN_CELL else None
            if auc is not None:
                line += f" | overdistension AUC (PEEP-up steps) {auc:.2f}"
        mae_by[name] = float(np.abs(plat_err).mean())
        out[name] = line

    lo, hi, yy = np.concatenate(lo_all), np.concatenate(hi_all), np.concatenate(y_all)
    coverage = float(((yy >= lo) & (yy <= hi)).mean())
    width = float(np.median(hi - lo) * 100)
    out["M2 80% prediction interval"] = f"coverage {coverage * 100:.0f}% (target >= {H1_COVERAGE:.0%}) | median width {width:.0f} compliance-% points"

    # H1 verdict (pre-specified)
    base, m2 = mae_by["M0 baseline (no change)"], mae_by["M2 state model (ridge)"]
    gain = (base - m2) / base if base else 0.0
    if len(p) < MIN_N_MODEL:
        verdict = f"UNDERPOWERED — {len(p)} usable pairs < {MIN_N_MODEL}; numbers above only prove the pipeline runs"
    elif gain >= H1_MAE_GAIN and coverage >= H1_COVERAGE:
        verdict = f"H1 MET — MAE gain {gain * 100:.0f}% >= {H1_MAE_GAIN:.0%} and coverage {coverage * 100:.0f}% >= {H1_COVERAGE:.0%}"
    else:
        verdict = f"H1 NOT MET — MAE gain {gain * 100:.0f}% (need >= {H1_MAE_GAIN:.0%}), coverage {coverage * 100:.0f}% (need >= {H1_COVERAGE:.0%}) → option C (range + test step) is primary"
    out["H1 verdict"] = verdict

    # standardized coefficients on ALL pairs (signs tell the story; aggregate, no patient data)
    lam_all = choose_lambda(X, y, subjects)
    m_all = ridge_fit(X, y, lam_all)
    coefs = sorted(zip(FEATURES, m_all[0][1:]), key=lambda t: -abs(t[1]))
    out[f"M2 standardized coefficients (all pairs, ridge λ={lam_all:g}, largest first)"] = ", ".join(f"{k} {v:+.3f}" for k, v in coefs[:8])
    return out


# ----------------------------------------------------------------------------------
# 4. Q3 — the test step: does a first step predict the next one in the same direction?
# ----------------------------------------------------------------------------------
def q3_test_step(p, within_h=24.0):
    p = p.sort_values(["stay_id", "t_change"]).copy()
    p["slope"] = p["frac_change"] / p["dpeep"]
    rows = []
    for sid, g in p.groupby("stay_id"):
        g = g.reset_index(drop=True)
        for k in range(1, len(g)):
            a, b = g.iloc[k - 1], g.iloc[k]
            if np.sign(a["dpeep"]) != np.sign(b["dpeep"]):
                continue
            if (b["t_change"] - a["t_change"]) > pd.Timedelta(hours=within_h):
                continue
            rows.append({"first_abs_dpeep": abs(a["dpeep"]), "first_peep": a["peep_before"],
                         "s1": a["slope"], "s2": b["slope"], "agree": float(np.sign(a["slope"]) == np.sign(b["slope"]))})
    d = pd.DataFrame(rows)
    out = {"same-direction step pairs within 24 h": int(len(d))}
    if len(d) == 0:
        return out

    def describe(sub, label):
        if len(sub) < MIN_CELL:
            out[label] = f"n={len(sub)} < {MIN_CELL} — suppressed"
            return
        rho = pd.Series(sub["s1"]).rank().corr(pd.Series(sub["s2"]).rank())
        out[label] = f"n={len(sub)}: direction repeats {sub['agree'].mean() * 100:.0f}%, Spearman {rho:.2f}"

    describe(d, "all")
    describe(d[d["first_abs_dpeep"] < 4], "first step < 4 cmH2O")
    describe(d[d["first_abs_dpeep"] >= 4], "first step >= 4 cmH2O")
    describe(d[d["first_peep"] <= 8], "starting PEEP <= 8")
    describe(d[d["first_peep"] > 8], "starting PEEP > 8")
    return out


# ----------------------------------------------------------------------------------
# 5. Q5 — the overdistension signal by PEEP level and driving pressure
# ----------------------------------------------------------------------------------
def q5_overdistension(p):
    up = p[p["dpeep"] > 0].copy()
    out = {"PEEP-up steps": int(len(up))}
    if len(up) == 0:
        return out
    up["fell"] = up["frac_change"] < -NOISE_THRESHOLD
    up["rose"] = up["frac_change"] > NOISE_THRESHOLD

    def cell(sub, label):
        if len(sub) < MIN_CELL:
            out[label] = f"n={len(sub)} < {MIN_CELL} — suppressed"
        else:
            out[label] = f"n={len(sub)}: compliance FELL >10% in {sub['fell'].mean() * 100:.0f}%, ROSE >10% in {sub['rose'].mean() * 100:.0f}%"

    cell(up, "all PEEP-up steps")
    for lo, hi, lab in [(0, 8, "starting PEEP <= 8"), (8, 12, "starting PEEP 9-12"), (12, 99, "starting PEEP >= 13")]:
        cell(up[(up["peep_before"] > lo) & (up["peep_before"] <= hi)] if lo else up[up["peep_before"] <= hi], lab)
    for lo, hi, lab in [(0, 12, "driving pressure before < 12"), (12, 15, "driving pressure before 12-15"), (15, 99, "driving pressure before > 15")]:
        sub = up[(up["dp_before"] >= lo) & (up["dp_before"] < hi)] if lo else up[up["dp_before"] < hi]
        cell(sub, lab)
    return out


# ----------------------------------------------------------------------------------
# 6. Q4 + S — noise floor vs step size, and the sensitivity definitions
# ----------------------------------------------------------------------------------
def noise_floor(fresh, max_gap_h=12.0):
    gap = pd.Timedelta(hours=max_gap_h)
    nc = []
    for sid, g in fresh.groupby("stay_id"):
        g = g.reset_index(drop=True)
        for i in range(1, len(g)):
            if not (g["controlled"][i - 1] and g["controlled"][i]):
                continue
            if g["charttime"][i] - g["charttime"][i - 1] > gap:
                continue
            if abs(g["peep"][i] - g["peep"][i - 1]) >= 1 or abs(g["vt"][i] - g["vt"][i - 1]) >= 10:
                continue
            nc.append((g["compliance"][i] - g["compliance"][i - 1]) / g["compliance"][i - 1])
    return np.array(nc)


def q4_noise_vs_step_size(fresh, p):
    nc = noise_floor(fresh)
    iqr = lambda v: float(np.percentile(v, 75) - np.percentile(v, 25)) if len(v) else np.nan
    out = {"noise floor (no setting change)": f"n={len(nc)}, IQR width {iqr(nc) * 100:.1f} compliance-% points"}
    for lab, sub in [("steps < 4 cmH2O", p[p["dpeep"].abs() < 4]), ("steps >= 4 cmH2O", p[p["dpeep"].abs() >= 4])]:
        if len(sub) < MIN_CELL:
            out[lab] = f"n={len(sub)} < {MIN_CELL} — suppressed"
        else:
            out[lab] = (f"n={len(sub)}: IQR width {iqr(sub['frac_change']) * 100:.1f} points "
                        f"(ratio to noise {iqr(sub['frac_change']) / iqr(nc):.2f}), per-cmH2O IQR "
                        f"{iqr(sub['frac_change'] / sub['dpeep'].abs()) * 100:.1f}")
    return out


def sensitivity(pairs_all_usable, snaps, fresh):
    """Re-run the population summary under the pre-specified alternative pair definitions."""
    defs = {
        "primary (after <= 4 h, controlled both)": pairs_all_usable,
        "S1 steps >= 4 cmH2O": pairs_all_usable[pairs_all_usable["dpeep"].abs() >= 4],
        "S2 after-plateau <= 2 h": pairs_all_usable[pairs_all_usable["hours_after"] <= 2],
        "S4 no spontaneous breaths charted": pairs_all_usable[pairs_all_usable["spont_zero_both"]],
        "S5 first step per stay only": pairs_all_usable.sort_values("t_change").groupby("stay_id").head(1),
    }
    out = {}
    for lab, d in defs.items():
        if len(d) < MIN_CELL:
            out[lab] = f"n={len(d)} < {MIN_CELL} — suppressed"
            continue
        up, down = d[d["dpeep"] > 0]["frac_change"], d[d["dpeep"] < 0]["frac_change"]
        out[lab] = (f"n={len(d)} ({d['stay_id'].nunique()} stays): β {fit_beta(d):+.3f}; "
                    f"PEEP-up median {up.median() * 100:+.1f}% (n={len(up)}), PEEP-down median {down.median() * 100:+.1f}% (n={len(down)})")
    return out


# ----------------------------------------------------------------------------------
def show(title, d, note=None):
    print(title)
    for k, v in d.items():
        print(f"   {k}: {v}")
    if note:
        print(f"   → {note}")
    print()


def main():
    ap = argparse.ArgumentParser(description="Step 2b: pre-specified full-MIMIC analysis (state model + test-step check).")
    ap.add_argument("--mimic", required=True, help="MIMIC-IV folder containing icu/ and hosp/")
    args = ap.parse_args()

    snaps = load_snapshots(args.mimic)
    fresh = fresh_plateaus(snaps)
    pairs, funnel = usable_peep_pairs(snaps, fresh)
    print("=== STEP 2b — pre-specified full-MIMIC analysis (aggregate results only) ===\n")
    print("Funnel:")
    for k, v in funnel.items():
        print(f"   {k}: {v}")
    print(f"\nUsable pairs: {len(pairs)} in {pairs['stay_id'].nunique() if len(pairs) else 0} stays "
          f"(pre-specified minimum for the model: {MIN_N_MODEL})\n")
    if len(pairs) == 0:
        return

    show("[Q2] Population response at scale", exp3b_recruitment_on_usable_pairs(pairs))
    show("[Q4] Noise floor vs step size", q4_noise_vs_step_size(fresh, pairs),
         "a ratio near 1 = single steps are noise; larger steps should give a larger ratio.")

    p = attach_state(pairs, args.mimic, snaps)
    missing = {f: int(p[f].isna().sum()) for f in FEATURES if p[f].isna().any()}
    print(f"[Q1] State features attached to {len(p)} pairs; missing values per feature (imputed with the training mean): {missing}\n")
    show("[Q1] State model vs baseline — grouped cross-validation by PATIENT (5 folds × 3 repeats)", q1_state_model(p),
         "H1 = the state model must beat 'no change' by >= 15% AND its 80% interval must cover >= 75%.")
    show("[Q3] Test step — does a first step predict the next in the same direction?", q3_test_step(p),
         "high direction-repeat + positive Spearman = a small test step is informative (option C works).")
    show("[Q5] Overdistension signal — how often compliance FALLS when PEEP goes up", q5_overdistension(p),
         "a rising 'FELL' share at higher PEEP / higher driving pressure = where the U-curve turns (sub-problem 1).")
    show("[S] Sensitivity — alternative usable-pair definitions", sensitivity(pairs, snaps, fresh))
    print("Paste everything printed above back to Claude. Nothing above identifies a patient.")


if __name__ == "__main__":
    main()
