# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-28
**Phase:** 1 (centered on the PEEP goal)
**Status:** steps 1, 1b, 2a, 2b DONE → **waiting on Ahmed's full-MIMIC run** (the decisive experiment) · **next task = sub-problem 1 (highest safe PEEP)**, which does not depend on it

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it.
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

**Objective metric (locked 2026-09-27):** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098 × RR × VT × ½(Pplat − PEEP)`; report absolute MP alongside. Never compare by absolute MP.

**Design decision (locked 2026-09-28, Ahmed — option (c)):** sub-problem 2 = a **state-predictor model + uncertainty range** on full MIMIC-IV, with a **small reversible test step** (option C) as the safety net — and as the primary design if the model fails its pre-set criterion.

## Done so far on the core goal (all 2026-09-28)
- **Step 1 — required variables + dataset:** `_Required_Variables.md` + `check_coverage.py`. **MIMIC-IV confirmed.**
- **Step 1b — honest re-run on real plateaus:** usable pair = two real plateaus, one PEEP step, 'after' ≤ 4 h, controlled both sides → **27 pairs / 13 stays**. Population rule **retracted** (β 0.026, interval includes 0; no held-out gain).
- **Step 2a — per-patient pilot:** the response is **real** (3.2× the noise floor) but **does not repeat** (direction 43%, Spearman 0.09); own-last-step prediction worse than "no change" (8.70 vs 4.01). **Option B retired.**
- **Step 2b — frozen analysis plan + code:** `docs/_Analysis_Plan_FullMIMIC.md` (H1–H5 with pass/fail criteria; cohort; pair definition + S1/S2/S4/S5; fixed predictor list with windows; M0/M1/M2(+M3); grouped-by-patient 5×3 CV; 80% prediction interval; test-step H3; overdistension H5; decision rules; governance; run instructions) + `engine/state_predictor.py` (aggregate output; min n = 300 and cell suppression < 10 enforced; pipeline-tested on the demo → UNDERPOWERED as designed).

## Immediate next steps
1. **Ahmed — the full-MIMIC run** (`_Analysis_Plan_FullMIMIC.md` §12): run the four scripts locally in order, paste the printed output (aggregates only), and note the MIMIC-IV version + `git rev-parse --short HEAD`. Claude then applies the pre-specified decision rules (§10) — no re-interpretation.
2. **Sub-problem 1 — the highest SAFE PEEP (start now, independent of prediction):** define the ceilings (Pplat ≤ 30 `[E3]`; driving-pressure ceiling — cite before use; elastance-ratio lung stress `(Pplat−PEEP)×0.7` as an upper bound `[ASSUMPTION]`), the oxygenation floors (SpO₂/PaO₂ targets `[E3]`, PEEP/FiO₂ envelope `[E3][N7]`), and the gates (raised ICP, air leak, hemodynamic instability — thresholds `[TO-CITE]`, spontaneous effort, auto-PEEP/τ). Build it as `engine/safe_peep.py`: given a snapshot, return the highest PEEP that keeps every ceiling/floor/gate satisfied *under the current compliance* (no prediction needed), with the reasons. Validate on the demo: how often is the charted PEEP above/below that ceiling? H5 from the full run later sharpens the overdistension ceiling.
3. After the full run: implement the winning branch of the decision tree (model + interval, or option C range + test step) in `physiology.py` / `optimizer.py`.

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → prediction/prototype, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate.
- Never carry a measured value (plateau) across a setting change it was not measured under.
- Never present a compliance prediction without its uncertainty. Never change a frozen criterion after seeing full-MIMIC results (log deviations first).

## Validated so far (after 2b)
- Every theory paper-validated (`_Literature_Validation.md`) — unaffected.
- **Compliance not constant — HOLDS** (17.7% within-patient). **PEEP changes hardest to predict — HOLDS** (4.19 vs 2.71 vs noise floor 1.41). **Individual response real — CONFIRMED** (3.2× noise).
- **Population slope — NOT SUPPORTED. Own-last-step slope — NOT SUPPORTED.**
- MP savings from VT↔RR ≈ 0; HB dead space worsened CO₂ prediction — unchanged.

## Noticed (not fixing now)
1. **MP formula: docs vs code mismatch** (`_Evidence_Base` [E1] / `_Clinical_Logic` §1 print `Ppeak − ½(Ppeak − PEEP)`; code uses `Ppeak − ½(Pplat − PEEP)`). Decide, cite, align — needed before sub-problem 1's MP reporting.
2. exp4/exp5 still run on carried-plateau snapshots; re-run on `pplat_fresh` rows for tidiness.
3. `_Task_History.md` rows are not in date order — cosmetic.
4. `_Data_Access.md` still names the "Temporal Dataset for Respiratory Support" as the download; the plan now targets the MIMIC-IV clinical tables directly — reconcile when Ahmed confirms what he holds.

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- **Run the four scripts on full MIMIC-IV and paste the output** (aggregates only). Which MIMIC-IV version do you hold, and who is credentialed?
- Pick the paper-title angle; folder rename (cosmetic).
