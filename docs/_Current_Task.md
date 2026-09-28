# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-28
**Phase:** 1 (centered on the PEEP goal)
**Status:** steps 1, 1b, 2a, 2b and **sub-problem 1 v1 DONE** → **waiting on Ahmed's full-MIMIC run** (the decisive experiment) · next build task = wire the ceiling into the optimizer + the option C "range + test step" output (see below)

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it. ✅ **v1 built** (`engine/safe_peep.py`).
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power. ⏳ **awaiting the full-MIMIC run** (state model, H1) with option C (range + test step) as the safety net.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

**Objective metric (locked 2026-09-27):** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098 × RR × VT × ½(Pplat − PEEP)`; report absolute MP alongside (Gattinoni plateau form when a plateau exists; the manuscript's peak-only surrogate as fallback, always labelled — decision 2026-09-28, `_Evidence_Base` [E1]/[N8]). Never compare by absolute MP.

**Design decision (locked 2026-09-28, Ahmed — option (c)):** sub-problem 2 = a **state-predictor model + uncertainty range** on full MIMIC-IV, with a **small reversible test step** (option C) as the safety net — primary if the model fails its pre-set criterion.

## Done so far on the core goal (all 2026-09-28)
- **Step 1** — required variables + dataset: `_Required_Variables.md` + `check_coverage.py`. **MIMIC-IV confirmed.**
- **Step 1b** — honest re-run on real plateaus: **27 usable pairs / 13 stays**; population rule **retracted** (β 0.026, interval includes 0).
- **Step 2a** — per-patient pilot: response **real** (3.2× noise) but **does not repeat** (direction 43%); own-last-step worse than "no change". Option B retired.
- **Step 2b** — frozen analysis plan `_Analysis_Plan_FullMIMIC.md` + `state_predictor.py` (H1–H5, pass marks, decision rules, governance).
- **Sub-problem 1 v1** — `engine/safe_peep.py`: from the current chart only, the highest PEEP at which plateau ≤ 30 `[E3]`, ΔP ≤ 15 `[N9][E4]` and ΔP_L ≤ 11.7 `[N9]` still hold under a cautious margin (compliance may fall 5%/cmH₂O `[ASSUMPTION]`), capped by the PEEP/FiO₂ envelope `[E3][N7]`, with vetoes (ICP > 22 `[N10]`, MAP < 65 `[N11]`, effort, over-limit) and cautions (vasopressor, chest tube, auto-PEEP). **Demo:** **32%** of moments vetoed (MAP < 65, effort, ΔP > 15); where an increase is allowed, headroom median **5 cmH₂O** (IQR 2–6), **11%** with none, **ΔP binds in 50%**, plateau 38%, envelope 12%; charted PEEP never above the ALVEOLI envelope; SpO₂ above target in 83%.

## Immediate next steps
1. **Ahmed — the full-MIMIC run** (`_Analysis_Plan_FullMIMIC.md` §12): four scripts, paste the printed output (aggregates only), note the MIMIC-IV version + `git rev-parse --short HEAD`. Then apply the frozen decision rules (§10). H5 also replaces the 5%/cmH₂O margin in `safe_peep.py` with measured worst-case responses by PEEP level.
2. **Wire the ceiling into the optimizer:** `optimizer.py` candidate PEEPs must lie in `[current PEEP, safe_peep ceiling]`; surface the vetoes/cautions in the explanation; report MP (a) + MP_dyn (b) labelled, and MP_tidal as the comparison metric. Add the peak-only fallback to `physiology.py` when no plateau exists.
3. **Option C output (the safety net, needed whichever way H1 goes):** for a proposed PEEP step, print the expected compliance-change **range** (from the state-stratified Δ%C quantiles once the full run exists; until then the 1b IQR as a placeholder, labelled) and the **test-step protocol** (small reversible step → measure plateau → keep or reverse), all as clinician-reviewed suggestions.
4. Later: `safe_peep.py` v2 — patient-specific elastance ratio when a measured transpulmonary pressure exists (the 3% subset); per-PEEP-level margins from H5.

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → prediction/prototype, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate. A ceiling is never a recommendation to go there.
- Never carry a measured value (plateau) across a setting change it was not measured under.
- Never present a compliance prediction without its uncertainty. Never change a frozen criterion after seeing full-MIMIC results (log deviations first).

## Validated so far
- Every theory paper-validated (`_Literature_Validation.md`) — unaffected. Compliance not constant — HOLDS. PEEP changes hardest to predict — HOLDS. Individual response real — CONFIRMED. Population slope — NOT SUPPORTED. Own-last-step slope — NOT SUPPORTED.
- MP savings from VT↔RR ≈ 0; HB dead space worsened CO₂ prediction — unchanged.
- Safe-PEEP ceiling behaves sensibly on the demo (see above); its outcome check (above vs at/below the ceiling) needs the full run (n < 10 in the demo).

## Noticed (not fixing now)
1. ~~MP formula docs vs code mismatch~~ — **settled 2026-09-28** (`_Evidence_Base` [E1]/[N8]); the peak-only fallback still has to be *implemented* in `physiology.py` (step 2 above).
2. exp4/exp5 still run on carried-plateau snapshots; re-run on `pplat_fresh` rows for tidiness.
3. `_Task_History.md` rows are not in date order — cosmetic.
4. `_Data_Access.md` still names the "Temporal Dataset for Respiratory Support" as the download; the plan targets the MIMIC-IV clinical tables directly — reconcile when Ahmed confirms what he holds.
5. `safe_peep.py` validation treats every chest tube as a possible air leak (104 moments) — many are post-operative drains; a finer rule needs a cited criterion.

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- **Run the four scripts on full MIMIC-IV and paste the output** (aggregates only). Which MIMIC-IV version do you hold, and who is credentialed?
- Pick the paper-title angle; folder rename (cosmetic).
