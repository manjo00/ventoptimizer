# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-27
**Phase:** 1 (now centered on the PEEP goal)
**Status:** in progress

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it.
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

## Immediate next steps
1. **Define the required-variable list** for the PEEP math + confirm a dataset (start: MIMIC-IV) covers it. (`_Research_Agenda` → "The PEEP problem" has the draft list + the pleural-signal gap.)
2. **Prototype sub-problem 2** (PEEP → compliance → MP): build on the 28% population baseline + the **183 demo PEEP changes**; push toward per-patient prediction. No-balloon lever: elastance-ratio lung stress from Pplat/PEEP/VT.
3. **Sub-problem 1** (highest safe PEEP): overdistension ceiling (plateau / elastance lung-stress) + oxygenation response.

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → frame as **prediction/prototype**, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate.

## Validated so far
- VT/RR pressure prediction GOOD (plateau MAE 2.68 for VT changes); **PEEP changes unreliable (MAE 4.80) = the crux.**
- PEEP-aware compliance: **28%** prediction win (population avg; individual = the hard part).
- MP savings from VT↔RR redistribution ≈ **0** → PEEP (+ permissive hypercapnia) are the real levers.
- Every theory paper-validated (`_Literature_Validation.md`).

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- When ready: run `validate_mimic.py` on full MIMIC-IV locally; paste aggregates.
