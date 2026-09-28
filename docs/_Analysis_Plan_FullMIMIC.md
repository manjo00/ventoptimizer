# Analysis Plan — the full MIMIC-IV run (pre-specified, step 2b)

**Version 1.0 — 2026-09-28 — written and committed BEFORE any full-MIMIC data is touched.** Any deviation from this plan must be written into `_Research_Log.md` *before* the results are interpreted. This is how we stop ourselves from fooling ourselves again (see the carried-plateau artifact, `_Research_Log` 2026-09-28).
**Decision it serves (Ahmed, 2026-09-28): option (c)** — build a **state-predictor model** of the compliance response to a PEEP step on the full MIMIC-IV, **and** keep a **small reversible test step** (option C) as the safety net whenever the prediction is uncertain.
**The plan in code:** `engine/state_predictor.py` (plus the three earlier scripts). **Who runs it:** the PhysioNet-credentialed team member, locally. **What comes back to Claude:** the printed aggregates only.

---

## 1. What we already know (open demo, 100 patients)
- Usable PEEP-step pairs are scarce: 27 of 183 apparent events (real plateau on both sides, one step, ≤ 4 h, controlled mode).
- The individual response is **real** (spread across a step ≈ 3× the no-change noise floor) but **neither a population slope nor the patient's last step predicts it** (β 0.026 with an interval including 0; own-last-step prediction worse than "no change").
- Noise floor: with nothing changed, compliance still wobbles (IQR −9% to +7%); a "real move" is therefore defined as |Δ%C| > 10%.
- Everything else the math needs is present in MIMIC-IV (`_Required_Variables.md`). Expected scale-up ≈ 500× → on the order of 10,000 usable pairs.

## 2. Objectives and pre-specified hypotheses
| # | Question | Hypothesis / pass criterion (fixed in advance) |
|---|---|---|
| **H1 (primary)** | Can the compliance change across a PEEP step be predicted from the patient's **pre-step state**, on patients the model never saw? | The state model (M2) cuts the after-step **plateau MAE by ≥ 15%** vs "no change" (M0) **and** its **80% prediction interval covers ≥ 75%** of observed values, in grouped-by-patient cross-validation, with **n ≥ 300** usable pairs. Both conditions or H1 fails. |
| H2 | How big and how heterogeneous is the population response at scale? | Descriptive: β with bootstrap 95% interval; PEEP-up / PEEP-down medians and IQRs; share of "real moves" vs the noise floor. No pass/fail. |
| H3 | Is a **small first step informative about the next step** in the same direction (the "verify" half of option C)? | In same-direction consecutive steps within 24 h: **direction repeats ≥ 70% and Spearman ≥ 0.3** in at least one pre-specified stratum (first step ≥ 4 cmH₂O, or starting PEEP ≤ 8 / > 8). |
| H4 | Do **bigger steps** give a clearer signal? | The IQR-to-noise ratio is larger for steps ≥ 4 cmH₂O than for steps < 4 cmH₂O. |
| H5 | Where does the **overdistension** side begin? | Among PEEP-up steps, the share where compliance **falls > 10%** rises with starting PEEP level and with pre-step driving pressure (monotone across the three bins). Feeds sub-problem 1 (highest safe PEEP). |

## 3. Data, cohort, unit of analysis
- **Source:** MIMIC-IV (the version Ahmed holds; record it in the log), `icu/` + `hosp/` tables. Same item codes as the demo (`_Data_Dictionary.md`).
- **Cohort:** adult ICU stays with any ventilator setting charted (the `check_coverage.py` denominator). **No ARDS restriction** — all ventilated patients (project scope).
- **Unit of analysis = a usable PEEP-step pair** (primary definition, unchanged from step 1b): two consecutive *real* plateau measurements in one stay · **exactly one** PEEP change between them · 'after' plateau **≤ 4 h** after the change · **controlled** ventilator mode at both plateaus (`CONTROLLED_MODES` in `validate_mimic.py`) · plausibility filter (`physiologic_filter`: 0 ≤ PEEP ≤ 30, Pplat > PEEP, Pplat ≤ 60, VT 100–1500 mL, compliance 5–200 mL/cmH₂O).
- **Exclusions:** APRV, NIV, support/spontaneous modes (by mode text); pairs with several PEEP changes between plateaus (ambiguous); stays with no charted height are excluded **only** from the VT/kg feature (imputed), not from the analysis.
- **Sensitivity definitions (all reported):** S1 steps ≥ 4 cmH₂O · S2 'after' ≤ 2 h · S4 no spontaneous breaths charted at either plateau · S5 first step per stay only (independence check). (S3, averaged repeated plateaus, is deferred: it needs a different pairing rule and will be added only if the noise floor at scale is ≥ the demo's.)

## 4. Outcomes
- **Primary:** Δ%C = (C_after − C_before) / C_before, with C = VT / (Pplat − PEEP).
- **For scoring:** the after-step plateau, predicted as `PEEP_after + VT_after / C_pred` (MAE in cmH₂O) — this is the number the optimizer needs.
- **Secondary:** after-step tidal mechanical power `0.098 × RR × VT × ½(Pplat − PEEP)`; **overdistension event** = Δ%C < −10% on a PEEP-up step; **real move** = |Δ%C| > 10% (direction accuracy is scored on real moves only).

## 5. Predictors (the pre-step STATE) — fixed list, no additions without logging
| Feature | Source / window before the step | Why |
|---|---|---|
| ΔPEEP (signed), starting PEEP, starting PEEP², ΔPEEP × starting PEEP | the pair | direction + level (U-shape) |
| C_before, ΔPEEP × C_before, driving pressure before, VT per PBW | the 'before' plateau | baseline mechanics |
| SpO₂/FiO₂ (S/F), ΔPEEP × S/F | SpO₂ ≤ 4 h, FiO₂ ≤ 24 h (setting) | oxygenation / recruitability `[N6]`, `[E7]` |
| PaCO₂, pH | chart ABG ≤ 12 h | dead-space burden / CO₂ side |
| BMI, age, sex | height, weight, `patients` | chest wall, PBW |
| days on the ventilator | `procedureevents` 225792 (fallback: first vent setting) | time-dependence of recruitability |
| mode family (pressure- vs volume-controlled) | mode text at the 'before' plateau | formula family |
- **Missing values:** imputed with the training-fold mean (the script prints the count per feature). PaO₂/FiO₂ is computed but S/F is the model feature (denser).
- **Standardization:** on the training fold only.

## 6. Models and evaluation (fixed)
- **M0** baseline: Δ%C = 0 (compliance unchanged). **M1** population slope: Δ%C = β·ΔPEEP, β fitted on the training fold. **M2** state model: ridge regression on the features above; penalty chosen from {0.1, 1, 10, 100} by an **inner** 3-fold grouped CV on the training patients only. **M3** (optional, only if scikit-learn is installed): gradient boosting, depth 3, 200 rounds — reported alongside, never replaces M2 for H1.
- **Plausibility clip:** every predicted Δ%C is held to −70% … +150%.
- **Cross-validation:** **grouped by patient** (`subject_id`), 5 folds × 3 repeats (seeds 0, 1, 2). A patient's pairs are never split across training and test.
- **Prediction interval (M2):** 80% interval from the 10th/90th percentiles of the training-fold residuals, applied to the test fold; we report **coverage** and **median width**.
- **Metrics:** after-step plateau MAE (primary) · Δ%C MAE · direction accuracy on real moves · overdistension AUC on PEEP-up steps · interval coverage and width · standardized coefficients (signs) on all pairs.
- **Minimum n:** the model result only counts with **≥ 300 usable pairs**; below that the script prints UNDERPOWERED (the demo's 27 pairs are a pipeline test only).

## 7. Test-step analysis (H3, the "verify" half of option C)
Consecutive usable steps in the same stay, **same direction**, second step ≤ 24 h after the first. Report direction-repeat share and Spearman correlation of the per-cmH₂O slopes, overall and by stratum (first step < 4 vs ≥ 4 cmH₂O; starting PEEP ≤ 8 vs > 8). Cells with < 10 pairs are suppressed.

## 8. Overdistension analysis (H5 → sub-problem 1)
Among PEEP-up steps: share with compliance **fell > 10%** and **rose > 10%**, by starting PEEP (≤ 8, 9–12, ≥ 13) and by pre-step driving pressure (< 12, 12–15, > 15). Cells < 10 suppressed.

## 9. Noise and sensitivity (H4, S)
Noise floor = Δ%C between consecutive real controlled plateaus with no setting change (same PEEP, VT within 10 mL, ≤ 12 h). IQR ratio (PEEP steps ÷ noise) for steps < 4 and ≥ 4 cmH₂O. Sensitivity table S1/S2/S4/S5: n, β, PEEP-up / PEEP-down medians.

## 10. Decision rules (what we do with each outcome — decided now)
| Outcome | Action |
|---|---|
| **H1 met** | Implement M2 (with its interval) as the compliance-response predictor in `physiology.py`; the optimizer uses the **lower bound** of the interval for safety ceilings and the **point estimate** for the MP comparison; option C test step recommended whenever the interval includes a compliance fall. |
| **H1 not met** | Option C becomes **primary**: the tool quotes the conditional range (from the state-stratified Δ%C quantiles) and recommends a small reversible test step; sub-problem 2 is "verify", not "predict". |
| **H3 met** | The test step is informative: after a first step, the observed response drives the next recommendation (bounded by the ceilings). |
| **H3 not met** | The test step is used only as a **safety check** (did compliance fall? then reverse), not as a predictor of the next step. |
| **H5 supported** | The PEEP-level / driving-pressure bins where "fell" rises become the **evidence-based overdistension ceiling** in sub-problem 1 (cited to our own data, labelled as such). |
| Any | Nothing here is clinical titration; results are framed as prediction / prototype (`_Literature_Validation` T7; ART). |

## 11. What comes back to Claude (governance)
- **Paste:** the complete printed output of the four scripts (all aggregates: counts, medians, IQRs, MAEs, coverage, coefficient signs, suppressed-cell notes).
- **Never paste:** any table with one row per pair or per patient; `stay_id` / `subject_id` values; dates; raw extracts; the `--csv` output of `check_coverage.py` is fine (per-variable counts), any other CSV is not.
- The scripts suppress every subgroup with fewer than 10 pairs and print no identifiers.

## 12. How to run (Ahmed, locally, in this order)
```bash
python engine/check_coverage.py --mimic <MIMIC-IV folder> --csv coverage_full.csv
python engine/validate_mimic.py --demo <MIMIC-IV folder>
python engine/peep_response_pilot.py --mimic <MIMIC-IV folder>
python engine/state_predictor.py --mimic <MIMIC-IV folder>
```
- `<MIMIC-IV folder>` = the folder that contains `icu/` and `hosp/` (the `.csv.gz` files, not unzipped).
- Needs Python 3 with `pandas` and `numpy` (`pip install pandas numpy`); `scikit-learn` is optional (enables M3).
- The big tables are read in slices; expect **tens of minutes per script** on the full data and a few GB of RAM. If a script stops with an error, copy the whole message to Claude — no patient data is in error messages from these scripts.
- Record in `_Research_Log.md`: MIMIC-IV version, date of the run, git commit hash of the scripts (`git rev-parse --short HEAD`).

## 13. Reproducibility
Fixed seeds (0, 1, 2); the pair definition, feature list, models, thresholds and criteria are frozen in this file and in the script constants (`MIN_N_MODEL`, `MIN_CELL`, `NOISE_THRESHOLD`, `H1_MAE_GAIN`, `H1_COVERAGE`, `LAMBDA_GRID`, `CLIP`, `WINDOW_H`). Changing any of them after seeing full-MIMIC results is a logged deviation.

## 14. Limitations known in advance
- Plateau pressures are charted at ~1 vent check in 3 and half of ventilated time is in support modes → usable pairs are a biased subset (clinicians measured a plateau *because* they changed something). Selection bias is acknowledged, not fixed.
- Steps are small (median 3 cmH₂O) → single-step signal-to-noise is low (H4 tests whether bigger steps help).
- Gases are sparse near steps → CO₂-side features are often imputed.
- No pleural-pressure reference outside the ~3% transpulmonary subset → the collapse-side "target" cannot be validated here; only the overdistension side (H5).
- Everything is observational: association, not intervention.
