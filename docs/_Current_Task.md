# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-28
**Phase:** 1 (centered on the PEEP goal)
**Status:** steps 1, 1b and 2a DONE → next = step 2b (the pre-specified full-MIMIC analysis plan) — and a strategic question for Ahmed (below)

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it.
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

**Objective metric (locked 2026-09-27):** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098 × RR × VT × ½(Pplat − PEEP)`; report absolute MP alongside. Never compare by absolute MP. (Derivation: `_Required_Variables.md` §1b.)

## Done so far on the core goal (all 2026-09-28)
- **Step 1 — required variables + dataset:** `docs/_Required_Variables.md` + `engine/check_coverage.py`. **MIMIC-IV confirmed** (every required input present; only gap = an absolute pleural reference, partly covered by the ~3% of stays with esophageal-derived transpulmonary pressure).
- **Step 1b — honest re-run on real plateaus:** usable pair = two real plateaus, one PEEP step between, 'after' ≤ 4 h, controlled mode both sides → **27 pairs / 13 stays**. Population recruitment rule **retracted** (β 0.026, interval includes 0; no held-out gain). Survives: compliance not constant (17.7%); PEEP changes hardest to predict (MAE 4.19 vs VT-only 2.71 vs noise floor 1.41).
- **Step 2a — per-patient pilot** (`engine/peep_response_pilot.py`): the PEEP-step compliance spread is **3.2× the no-change noise floor** (noise IQR −9 to +7) → the individual response is **real**. But it **does not repeat**: consecutive steps agree in direction **43%**, Spearman **0.09** (5 stays, 14 step pairs). Predicting later steps: baseline MAE **4.01** beats population 4.42, blend 5.40, **own previous step 8.70**, own 24-h curve 10.59 → own-history **amplifies noise**. **Option B (learn from the last step) retired.**

## What the pilot means (the honest state of sub-problem 2)
Neither a population constant nor the patient's last step predicts the next compliance change. The response is real but **state-dependent** — it changes with the PEEP *level* (U-shape: recruit low, overdistend high), the step *direction*, and the evolving lung. So a prediction, if one exists, must come from **state predictors** (PEEP level, direction, baseline Crs / ΔP, P/F or S/F, PaCO₂, BMI, days on vent) fitted on thousands of pairs, or from **multi-point per-patient curves** — both need full MIMIC. And the tool must report **prediction intervals**, not point estimates. If prediction stays this uncertain at full scale, the defensible design is **option C: predict a range, then verify with a small reversible test step** — still math-only on recorded data (usable pairs *are* recorded test steps).

## Immediate next steps
2b. **Pre-specified analysis plan for Ahmed's full-MIMIC run** (written before the data is touched, so we cannot fool ourselves): usable-pair extraction (same rules + sensitivity: steps ≥ 4 cmH₂O, averaged repeated plateaus); β distribution; a state-predictor model of the compliance response (PEEP level, direction, baseline Crs, ΔP, S/F or P/F, PaCO₂, BMI, days on vent) with held-out-by-patient evaluation and prediction intervals; per-patient U-shaped curves where ≥ 3 real levels exist; outputs = aggregate tables only. Then Ahmed runs `check_coverage.py`, `validate_mimic.py`, `peep_response_pilot.py` locally and pastes the printed output.
3. **Sub-problem 1** (highest safe PEEP): overdistension ceilings (Pplat, ΔP, elastance-ratio stress) + oxygenation floors + gates (ICP, air leak, hemodynamics, effort, auto-PEEP). This side does not depend on predicting compliance and can proceed now.

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → frame as **prediction/prototype**, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate.
- Never carry a measured value (plateau) across a setting change it was not measured under.
- Never present a compliance prediction without its uncertainty.

## Validated so far (after 2a)
- Every theory paper-validated (`_Literature_Validation.md`) — unaffected.
- **Compliance not constant — HOLDS** (17.7% within-patient on real controlled plateaus).
- **PEEP changes hardest to predict — HOLDS** (MAE 4.19 vs VT-only 2.71 vs noise floor 1.41).
- **Individual PEEP response is real — CONFIRMED** (spread 3.2× the noise floor).
- **Population slope — NOT SUPPORTED** (β 0.026, interval includes 0). **Own-last-step slope — NOT SUPPORTED** (direction repeats 43%; MAE 8.70 vs 4.01 baseline).
- MP savings from VT↔RR ≈ 0; HB dead space worsened CO₂ prediction — unchanged.

## Noticed (not fixing now)
1. **MP formula: docs vs code mismatch** (`_Evidence_Base` [E1] / `_Clinical_Logic` §1 print `Ppeak − ½(Ppeak − PEEP)`; code uses `Ppeak − ½(Pplat − PEEP)`). Decide, cite, align.
2. exp4/exp5 still run on carried-plateau snapshots; re-run on `pplat_fresh` rows for tidiness.
3. `_Task_History.md` rows are not in date order — cosmetic.

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- **Strategic (needs your call):** given that prediction from history failed at demo scale, do we (a) keep aiming at a state-predictor model on full MIMIC, (b) shift the design to option C "predict a range + verify with a small test step", or (c) both — model first, test-step as the safety net? My recommendation: **(c)**.
- **Run all three scripts on full MIMIC-IV** after step 2b's plan is written; paste the printed output (aggregate only).
- Pick the paper-title angle; folder rename (cosmetic).
