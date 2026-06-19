# Current Task — Phase 1 launch: Track A (citations) + Track B setup

**Date:** 2026-06-20
**Phase:** 1 (Model accuracy)
**Status:** in progress

## Goal
(A) Make every clinical number in the model defensible with a real citation — no
data needed. (B) Set up the compliant, local-only data pipeline so we can validate
against real MIMIC-IV patients next.

## Files to touch
- `docs/_Clinical_Logic.md`, `docs/_Evidence_Base.md` — resolve every `[ASSUMPTION]` with a citation/justification (Track A)
- `docs/_Research_Log.md` — start the lab notebook with the Track A entry
- `CLAUDE.md` — data-governance rule ✅
- `docs/_Data_Access.md` — data checklist ✅
- `engine/validate_mimic.py` — finalize the real-data loader (Track B, after Ahmed shares column names)

## Acceptance criteria
- [ ] Every `[ASSUMPTION]` tag in `_Clinical_Logic.md` is cited or explicitly justified
- [ ] Data-governance rule in `CLAUDE.md` + `_Data_Access.md` checklist ✅
- [ ] Research log started with the Track A entry
- [ ] No clinical number without a citation
- [ ] Committed + pushed

## Noticed (not fixing now)
- (none yet)

## Open with Ahmed (Track B — when ready)
- Who is credentialed on PhysioNet? (that person runs the data steps)
- Then: paste the dataset's **column names** so I can finalize `validate_mimic.py`.
