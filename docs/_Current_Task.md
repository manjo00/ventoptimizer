# Current Task — Phase 1: improve compliance (Track C)

**Date:** 2026-06-20
**Phase:** 1 (Model accuracy)
**Status:** baseline done; Track C next

## Done this session
- **Track A ✅** — every clinical number now cited (`docs/_Evidence_Base.md`).
- **Data governance ✅** — rule in `CLAUDE.md` + `docs/_Data_Access.md`.
- **Demo harness ✅** — `engine/validate_mimic.py` runs on the open MIMIC-IV demo (100 patients).
- **First real result (demo):** within-patient compliance varies ~19% (median); plateau-prediction **MAE 3.05 cmH₂O** (target ≤ 2). Logged in `docs/_Research_Log.md`.

## Next (Track C — beat the baseline)
- Replace the **constant** compliance with a **per-patient / recently-updated** compliance (use the patient's own recent VT–Pplat points), re-run the harness → does the plateau MAE drop below 3.05?
- Then add a pH/CO₂ prediction experiment and revisit dead space.

## Open with Ahmed
- When we reach a good point, **you** run `validate_mimic.py` on the **full MIMIC-IV** locally and paste back the aggregate numbers (governance rule).

## Noticed (not fixing now)
- (none)
