"""
peep_response_pilot.py — STEP 2a: can a patient's OWN history predict their PEEP response?

Plain-language: step 1b showed that one population rule ("compliance rises β per cmH2O
of PEEP") does not work — patients respond very differently. The obvious next idea
(option B in docs/_Research_Agenda.md) is to learn each patient's response from their
own charted history. Before building that into the engine, this pilot asks three
honest questions on the usable PEEP-step pairs (defined in validate_mimic.py):

  6a. NOISE FLOOR — how much does measured compliance wobble when NOTHING was changed?
      If that wobble is as wide as the spread across a PEEP step, a single step is too
      noisy to reveal an individual response, and no per-patient method can work on
      single steps (it would need several steps, or bigger steps).
  6b. CONSISTENCY — for patients with two or more usable steps, does the response
      repeat? (Does the direction agree? Do the slopes correlate?) If a patient's
      response is not stable, their history cannot predict their next step.
  6c. PREDICTION — for the later steps of those patients, compare ways of predicting
      the plateau after the step:
        * baseline: compliance unchanged;
        * population slope, learned on OTHER patients;
        * the patient's own previous step(s);
        * the patient's own recent compliance-vs-PEEP points (last 24 h);
        * a 50/50 blend of own slope and population slope.

Aggregate output only — never a patient row. Usage:
  python engine/peep_response_pilot.py --mimic data/mimic-iv-clinical-database-demo-2.2
"""

import argparse
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from validate_mimic import load_snapshots, fresh_plateaus, usable_peep_pairs


def frac_desc(x):
    """Describe a set of fractional compliance changes in plain numbers."""
    x = np.asarray(x, dtype=float) * 100
    if x.size == 0:
        return "n=0"
    return (f"n={x.size}: median {np.median(x):+.1f}%, IQR {np.percentile(x, 25):+.1f} to "
            f"{np.percentile(x, 75):+.1f}, beyond ±20%: {(np.abs(x) > 20).mean() * 100:.0f}%")


def exp6a_noise_floor(fresh, pairs, max_gap_h=12.0):
    """Compliance change between two consecutive REAL plateaus when nothing was changed
    (same PEEP, same VT within 10 mL, controlled mode, <= max_gap_h apart) — the wobble
    that measurement noise plus natural drift produce — versus the change across a PEEP step."""
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
    nc = np.array(nc)
    up = pairs.loc[pairs["dpeep"] > 0, "frac_change"].to_numpy()
    down = pairs.loc[pairs["dpeep"] < 0, "frac_change"].to_numpy()
    out = {
        "NO setting change (noise floor)": frac_desc(nc),
        "across a PEEP step UP": frac_desc(up),
        "across a PEEP step DOWN": frac_desc(down),
    }
    if nc.size and len(pairs):
        iqr = lambda v: np.percentile(v, 75) - np.percentile(v, 25)
        out["IQR width ratio: all PEEP steps ÷ noise floor"] = round(float(iqr(pairs["frac_change"]) / iqr(nc)), 2)
        out["IQR width ratio: PEEP-step per-cmH2O slope ÷ noise floor per 3 cmH2O"] = round(
            float(iqr(pairs["frac_change"] / pairs["dpeep"].abs()) / (iqr(nc) / 3.0)), 2)
    return out


def exp6b_consistency(pairs):
    """Is a patient's PEEP response stable over time? For stays with >= 2 usable steps, compare
    the per-cmH2O slope of consecutive steps: does the direction repeat, do the sizes correlate?"""
    p = pairs.sort_values(["stay_id", "t_change"]).copy()
    p["slope"] = p["frac_change"] / p["dpeep"]           # fractional compliance change per cmH2O of PEEP
    prev, cur, stays = [], [], 0
    for sid, g in p.groupby("stay_id"):
        s = g["slope"].to_numpy()
        if len(s) >= 2:
            stays += 1
        for k in range(1, len(s)):
            prev.append(s[k - 1])
            cur.append(s[k])
    prev, cur = np.array(prev), np.array(cur)
    if cur.size == 0:
        return {"stays_with_>=2_usable_steps": stays, "consecutive_step_pairs": 0}
    rank_r = pd.Series(prev).rank().corr(pd.Series(cur).rank())      # Spearman rank correlation
    return {
        "stays_with_>=2_usable_steps": stays,
        "consecutive_step_pairs": int(cur.size),
        "direction_repeats_pct (sign of previous slope == sign of next)": round(float((np.sign(prev) == np.sign(cur)).mean() * 100), 0),
        "spearman_rank_correlation (previous slope vs next slope)": round(float(rank_r), 2),
        "median_|slope|_per_cmH2O (previous / next)": f"{np.median(np.abs(prev)):.3f} / {np.median(np.abs(cur)):.3f}",
    }


def fit_beta(df):
    """Least-squares slope through the origin: frac_change ≈ β · ΔPEEP."""
    return float((df["frac_change"] * df["dpeep"]).sum() / (df["dpeep"] ** 2).sum())


def own_curve_slope(fresh_stay, t_change, hours=24.0):
    """The patient's own compliance-vs-PEEP slope (mL/cmH2O per cmH2O of PEEP) fitted on their
    real, controlled plateaus in the previous `hours`. None if they were all at one PEEP."""
    h = fresh_stay[(fresh_stay["charttime"] < t_change) &
                   (fresh_stay["charttime"] >= t_change - pd.Timedelta(hours=hours)) &
                   fresh_stay["controlled"]]
    if h["peep"].nunique() < 2:
        return None
    return float(np.polyfit(h["peep"].to_numpy(float), h["compliance"].to_numpy(float), 1)[0])


def exp6c_prediction(pairs, fresh, blend_w=0.5):
    """For every usable step that has at least one EARLIER usable step in the same stay, predict
    the after-step compliance several ways and score the resulting plateau prediction."""
    p = pairs.sort_values(["stay_id", "t_change"]).reset_index(drop=True)
    fresh_by_stay = {sid: g for sid, g in fresh.groupby("stay_id")}
    rows = []
    for sid, g in p.groupby("stay_id"):
        g = g.reset_index(drop=True)
        others = p[p["stay_id"] != sid]
        beta_pop = fit_beta(others) if len(others) >= 3 else None
        for k in range(1, len(g)):                       # only steps that HAVE a history
            r, hist = g.iloc[k], g.iloc[:k]
            beta_own = fit_beta(hist)
            b_curve = own_curve_slope(fresh_by_stay[sid], r["t_change"])
            c0, dp = r["c_before"], r["dpeep"]
            preds = {"baseline (compliance unchanged)": c0}
            if beta_pop is not None:
                preds["population slope (other patients)"] = c0 * max(1 + beta_pop * dp, 0.3)
                preds["blend 50/50 own + population"] = c0 * max(1 + blend_w * (beta_own + beta_pop) * dp, 0.3)
            preds["own previous step(s)"] = c0 * max(1 + beta_own * dp, 0.3)
            if b_curve is not None:
                preds["own recent compliance-vs-PEEP points (24 h)"] = max(c0 + b_curve * dp, 0.3 * c0)
            for m, c_pred in preds.items():
                hit = np.nan if m.startswith("baseline") else float(np.sign(c_pred - c0) == np.sign(r["c_after"] - c0))
                rows.append({"method": m,
                             "plateau_err": r["peep_after"] + r["vt_after"] / c_pred - r["pplat_after"],
                             "frac_err": (c_pred - r["c_after"]) / c0,
                             "sign_hit": hit})
    e = pd.DataFrame(rows)
    if len(e) == 0:
        return {"evaluable later steps (have own history)": 0}
    out = {"evaluable later steps (have own history)": int((e["method"] == "baseline (compliance unchanged)").sum())}
    for m, g in e.groupby("method", sort=False):
        line = (f"n={len(g)}: plateau MAE {g['plateau_err'].abs().mean():.2f} cmH2O, "
                f"compliance-change MAE {g['frac_err'].abs().mean() * 100:.1f}%")
        if g["sign_hit"].notna().any():
            line += f", direction correct {g['sign_hit'].mean() * 100:.0f}%"
        out[m] = line
    return out


def main():
    ap = argparse.ArgumentParser(description="Step 2a pilot: per-patient PEEP response on usable pairs.")
    ap.add_argument("--mimic", required=True, help="MIMIC-IV folder containing icu/ and hosp/")
    args = ap.parse_args()

    snaps = load_snapshots(args.mimic)
    fresh = fresh_plateaus(snaps)
    pairs, funnel = usable_peep_pairs(snaps, fresh)
    print("=== STEP 2a — per-patient PEEP-response pilot (aggregate results only) ===\n")
    print(f"Real plateau measurements: {len(fresh)} in {fresh['stay_id'].nunique()} stays; usable PEEP-step pairs: "
          f"{len(pairs)} in {pairs['stay_id'].nunique() if len(pairs) else 0} stays\n")

    print("6a — NOISE FLOOR: how much does compliance change when nothing was changed?")
    for k, v in exp6a_noise_floor(fresh, pairs).items():
        print(f"   {k}: {v}")
    print("   → if the PEEP-step spread is not clearly wider than the noise floor, single steps cannot")
    print("     reveal an individual response (ratio ≈ 1 = pure noise; ≫ 1 = real individual signal).\n")

    print("6b — CONSISTENCY: does a patient's response repeat from one step to the next?")
    for k, v in exp6b_consistency(pairs).items():
        print(f"   {k}: {v}")
    print("   → ~50% direction agreement and ~0 correlation = no stable individual response to learn from.\n")

    print("6c — PREDICTION: for later steps, which way of predicting the after-step plateau is best?")
    for k, v in exp6c_prediction(pairs, fresh).items():
        print(f"   {k}: {v}")
    print("   → lower MAE = better; 'direction correct' = did the method predict whether compliance rose or fell.")


if __name__ == "__main__":
    main()
