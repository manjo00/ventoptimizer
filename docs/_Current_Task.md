# Current Task — Phase 1: improve compliance (Track C)

**Date:** 2026-06-20
**Phase:** 1 (Model accuracy)
**Status:** baseline done; Track C next

## Done this session
- **Track A ✅** — every clinical number now cited (`docs/_Evidence_Base.md`).
- **Data governance ✅** — rule in `CLAUDE.md` + `docs/_Data_Access.md`.
- **Demo harness ✅** — `engine/validate_mimic.py` runs on the open MIMIC-IV demo (100 patients).
- **First real result (demo):** within-patient compliance varies ~19% (median); plateau-prediction **MAE 3.05 cmH₂O** (target ≤ 2). Logged in `docs/_Research_Log.md`.

## Track C attempt #1 result (2026-06-20)
- Robust/smoothed compliance did **NOT** help (3.07 vs 3.05). The error is not noise.
- **Diagnostic:** VT-only changes MAE **2.68**; PEEP changes MAE **4.80** → the error is a **recruitment** effect (compliance shifts when PEEP moves).

## Next (Track C #2 — the real fix)
- Measure compliance-vs-PEEP from the data; build a **PEEP-aware (recruitment) compliance**; re-run → does the PEEP-change MAE drop?
- Then a pH/CO₂ prediction experiment + revisit dead space.

## Open with Ahmed
- When we reach a good point, **you** run `validate_mimic.py` on the **full MIMIC-IV** locally and paste back the aggregate numbers (governance rule).

## Noticed (not fixing now)
- (none)
