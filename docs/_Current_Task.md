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

## Track C attempt #2 result (2026-06-20) — ✅ WIN
- Built a **data-learned PEEP-aware compliance** `C×(1+β·ΔPEEP)`, β≈0.083/cmH₂O.
- Honest train/test (learn on half the patients, score on the other half): PEEP-change MAE **4.48 → 3.21 = 28% better** on held-out patients.
- Measured recruitment: compliance **+40%** when PEEP↑, **−23%** when PEEP↓. (The prototype's guessed ×0.1 was close.)

## Next
- **Ahmed:** confirm on the **full MIMIC-IV** (run `validate_mimic.py` locally; paste aggregates) before we change the production model.
- **Phase 2:** once confirmed, implement the PEEP-aware compliance in `engine/physiology.py` + `optimizer.py`.
- **Dead space (done 2026-06-20):** built Harris–Benedict + manual override in `physiology.py`. Validation: HB **worsened** CO₂ prediction on the demo (14.4→33.6 mmHg) → HB opt-in, manual wins, anatomic default. **Next: per-patient *learned* dead space** (fit from each patient's own CO₂ data — like the PEEP win).

## Open with Ahmed
- When we reach a good point, **you** run `validate_mimic.py` on the **full MIMIC-IV** locally and paste back the aggregate numbers (governance rule).

## Noticed (not fixing now)
- 🚩 **Optimizer design-safety (Phase 2/3):** the recruitment logic could recommend higher PEEP to lower MP via modeled compliance gains. The ART trial (JAMA 2017) showed compliance-titrated PEEP *increased* mortality → constrain the optimizer so it never pushes PEEP up justified only by modeled compliance. See `_Literature_Validation.md`.
- 🚩 **Permissive-mode gate (Phase 2/3):** "Permissive CO₂" must not apply to raised-ICP / brain-injured patients (hypercapnia raises ICP) — add a contraindication flag. (`_Literature_Validation` T10.)
- 🩺 **Driving pressure as an explicit target:** Costa 2021 — driving pressure's mortality impact is ~4× respiratory rate's. Consider adding it to the objective/limits. (`_Literature_Validation` T12.)
