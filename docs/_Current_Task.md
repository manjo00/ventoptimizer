# Current Task — Phase 1 kickoff: MIMIC shadow-testing harness

**Date:** 2026-06-19
**Phase:** 1 (Model accuracy & research)
**Status:** NOT STARTED — this is the next task after setup.

## Goal
Build `engine/validate_mimic.py`: a harness that pulls real ventilated patients from MIMIC-IV and, for each, compares **what the physiology model predicts** against **what actually happened**. This tells us where the model is accurate and where it is wrong — the foundation of Phase 1.

## Why this first
We cannot "accurately optimize" until we know how accurate the predictions are. Shadow testing turns vague worry ("linear compliance might be wrong") into numbers ("plateau-pressure prediction is off by X cmH₂O on average").

## Files to touch (when started)
- `engine/validate_mimic.py` — new harness (load cases → predict → compare → report error)
- `docs/_Research_Agenda.md` — record findings as they come in
- `docs/_Evidence_Base.md` — add any new cited numbers used

## Acceptance criteria
- [ ] Loads a sample of ventilated patients with the fields the model needs (VT, RR, PEEP, Pplat/Ppeak, ABG)
- [ ] Runs `physiology.predict()` on each and tabulates predicted vs observed (Pplat, MP, pH)
- [ ] Prints a clear error summary (mean/median error per variable) **in plain language**
- [ ] No clinical number used without a citation in `_Evidence_Base.md`
- [ ] Git committed

## Open question to resolve with Ahmed before coding
- Which dataset for shadow testing — the same **MIMIC-IV** derived respiratory dataset from the manuscript, or the **MIMIC-III** the mega-prompt mentioned? (Recommend MIMIC-IV: you already have access + the pipeline experience.)

## Noticed (not fixing now)
- (none yet)

---
### Template — copy this block to start any new task
```markdown
# Current Task — <short name>
**Date:** <today>   **Phase:** <n>   **Status:** in progress
## Goal
<Ahmed's request, restated plainly>
## Files to touch
- `<file>` — <what & why>
## Acceptance criteria
- [ ] <proof it works>
- [ ] No uncited clinical numbers
- [ ] Git committed
## Noticed (not fixing now)
<unrelated issues spotted>
```
