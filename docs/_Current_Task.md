# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-28
**Phase:** 1 (centered on the PEEP goal)
**Status:** steps 1 and 1b DONE → next = step 2a (per-patient PEEP-response pilot + the pre-specified full-MIMIC analysis plan)

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it.
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

**Objective metric (locked 2026-09-27):** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098 × RR × VT × ½(Pplat − PEEP)` (breath energy, not the static PEEP baseline); report absolute MP alongside. Never compare by absolute MP. (Derivation: `_Required_Variables.md` §1b.)

## Step 1 — DONE 2026-09-28: required-variable list + dataset coverage
`docs/_Required_Variables.md` + `engine/check_coverage.py`. **MIMIC-IV confirmed** as the prototype dataset (every required input present; only gap = an absolute pleural reference, partly covered by the ~3% of stays with esophageal-derived transpulmonary pressure).

## Step 1b — DONE 2026-09-28: honest re-run on REAL plateau measurements
- **Method:** `validate_mimic.py` now flags `pplat_fresh` (a plateau really charted at that time) and `controlled` (ventilator mode in force). **Usable pair** = two consecutive real plateaus, exactly one PEEP step between them, 'after' plateau ≤ 4 h after the step, controlled mode both sides. Demo: 495 real plateaus (488 controlled); funnel 43 → 31 → 28 → **27 usable pairs in 13 stays** (18 up / 9 down, median |ΔPEEP| 3).
- **Results (old → honest):** PEEP↑ compliance change **+40% → +8.6%** [IQR −7 to +31]; PEEP↓ **−23% → −4.1%** [−30 to +35]; only **56%** of steps move the "expected" way; **β 0.083 → 0.026** (bootstrap 95% −0.038 to +0.089, includes 0); held-out gain **+28% → −4.5%** (LOSO MAE 3.57 baseline vs 3.73 PEEP-aware). Survives: compliance not constant (**17.7%** within-patient); PEEP changes hardest to predict (MAE **4.19** vs VT-only **2.71** vs noise floor **1.41**).
- **Meaning:** the population recruitment rule is **retracted**; the *average* effect is small and the *individual* response is wildly heterogeneous — Ahmed's original insight, confirmed on clean data. **Sub-problem 2 must be solved per patient** (own PEEP-step history, predictors, physiology bounds). The prototype's `×0.1` is an `[ASSUMPTION]`, probably too large. 27 pairs cannot fit predictors → the **full-MIMIC run is the decisive experiment**.

## Immediate next steps
2a. **Per-patient PEEP-response pilot (option B in `_Research_Agenda`):** for stays with ≥ 2 usable steps, does the patient's *own previous* step predict the next one better than the population β? Tiny n in the demo → pilot code + honest report.
2b. **Pre-specified analysis plan for Ahmed's full-MIMIC run** (written before the data is touched): β distribution on usable pairs; predictors of the individual response (baseline P/F or S/F, PaCO₂, Crs, BMI, days on vent); the per-patient method vs population; outputs = aggregate tables only. Then Ahmed runs `check_coverage.py` + `validate_mimic.py` locally and pastes the printed output.
3. **Sub-problem 1** (highest safe PEEP): overdistension ceilings (Pplat, ΔP, elastance-ratio stress) + oxygenation floors + gates (ICP, air leak, hemodynamics, effort, auto-PEEP).

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → frame as **prediction/prototype**, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate.
- Never carry a measured value (plateau) across a setting change it was not measured under.

## Validated so far (revised 2026-09-28, after 1b)
- Every theory paper-validated (`_Literature_Validation.md`) — unaffected.
- **Compliance not constant — HOLDS** (17.7% within-patient variation on real controlled plateaus).
- **PEEP changes hardest to predict — HOLDS** (MAE 4.19 vs VT-only 2.71 vs noise floor 1.41; n = 33).
- **Population recruitment slope / PEEP-aware gain — NOT SUPPORTED** (β 0.026, interval includes 0; LOSO −4.5%).
- **Heterogeneous individual response — CONFIRMED** (same-direction IQR −30% to +35%).
- MP savings from VT↔RR redistribution ≈ **0** — unchanged (the comparison uses the same compliance on both sides, so carried plateaus cancel).
- HB dead space worsened CO₂ prediction — unchanged.

## Noticed (not fixing now)
1. **MP formula: docs vs code mismatch.** `_Evidence_Base` [E1] and `_Clinical_Logic` §1 print the manuscript's peak-only surrogate `Ppeak − ½(Ppeak − PEEP)`; `physiology.py`, `validate_mimic.py` and the HTML use `Ppeak − ½(Pplat − PEEP)`. Decide one (Gattinoni's plateau form when Pplat is known; the surrogate as fallback), cite it, align all four.
2. exp4/exp5 still run on carried-plateau snapshots; re-run them on `pplat_fresh` rows for tidiness (conclusions unlikely to change).
3. `_Task_History.md` rows are not in date order — cosmetic.

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- **Run both scripts on full MIMIC-IV** after step 2b's plan is written; paste the printed output (aggregate only).
- Pick the paper-title angle; folder rename (cosmetic).
