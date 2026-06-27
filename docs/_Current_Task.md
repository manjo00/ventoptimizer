# Current Task — Phase 1: solvable wins (PEEP parked)

**Date:** 2026-06-20
**Phase:** 1 (Model accuracy)
**Status:** in progress

## Decision
The hard PEEP / recruitment problem is **PARKED** (Ahmed) — finish the solvable items first, return to it later. (Options A–D recorded in `_Research_Agenda` → "The PEEP problem".)

## Solvable focus (in order)
1. ✅ **DONE — MP savings from VT↔RR redistribution: near-zero.** On 3,077 real snapshots, median **0.1 J/min** savable; only 7.6% could save ≥1. At constant CO₂ clearance the *safe* knob barely moves power. (`_Research_Log`.)
2. ⭐ **NOW — MP savings from permissive hypercapnia** (the real lever): allow CO₂ to rise to a pH floor → reduce ventilation → measure the MP drop, on real patients. (With the raised-ICP contraindication gate.)
3. **Driving pressure as an explicit target/output** (Costa 2021, Amato 2015).
4. Per-patient *learned* dead space (revisit; CO₂ prediction is noisy → lower yield).

## Validated so far (Phase 1)
- VT/RR pressure prediction is GOOD (plateau MAE 2.68 for VT changes); PEEP changes are the unreliable part.
- PEEP-aware compliance: 28% prediction win (population-average; individual PEEP response = the parked hard problem).
- Dead space: HB built (opt-in; worsened CO₂ prediction); manual override always wins.
- Every theory paper-validated (`_Literature_Validation.md`).

## Open with Ahmed
- When ready: run `validate_mimic.py` on the **full MIMIC-IV** locally; paste aggregates.

## Noticed (not fixing now)
- 🚩 Optimizer must never push PEEP up just for compliance (ART). 🚩 Permissive mode needs a raised-ICP gate. (See `_Literature_Validation`.)
