# Task History

Append-only log of completed work. Oldest first, **newest at the bottom**. Check at session start to avoid redoing work.

Format: `Date | task | result`

---

| Date | Task | Result |
|---|---|---|
| 2026-06-19 | Phase 0 — Project setup | git init; seeded Project Brain (CLAUDE.md, Roadmap.md, docs/*); ported v2.4 logic into Python `engine/` + `app/ventoptimizer.html`; distilled manuscript into `_Evidence_Base.md`. Stack: Python engine = source of truth, HTML = front-end. **Folder rename `research poster day` → `VentOptimizer` is a pending MANUAL step (folder was locked).** GitHub backup live: manjo00/ventoptimizer. |
| 2026-06-20 | Phase 1 Track A — literature pass + data governance | Resolved every `[ASSUMPTION]`/`[TO-RESEARCH]` tag in `_Evidence_Base.md` with real citations (R/I Chen 2020; dead space Radford + critique; P–V nonlinearity Hickling 1998; permissive pH ARDSNet). Added the data-governance rule (CLAUDE.md), `_Data_Access.md`, `_Research_Log.md`. Found **linear compliance + dead space** = the two evidence-backed weak points. |
| 2026-06-20 | Phase 1 — dataset scouting | No large ARDS-rich fully-open dataset exists; scope clarified = **all ventilated patients** (not ARDS). Path: open MIMIC-IV demo now → full MIMIC-IV (Ahmed, manual) later → AmsterdamUMCdb optional. |
| 2026-06-20 | Phase 1 Track B/C — first shadow test on MIMIC-IV demo | Built `engine/validate_mimic.py` (aggregate-only). **Demo baseline:** within-patient compliance varies ~19% median; plateau-prediction **MAE 3.05 cmH₂O** (1,056 changes; 84% within 5). Nonlinear/updated compliance = Track-C target #1. |
| 2026-06-20 | Phase 1 Track C #1 — robust compliance (rejected) | Median-of-5 smoothing did NOT help (3.07 vs 3.05). Diagnostic split found the error lives in PEEP changes (MAE 4.80) vs VT-only (2.68) → recruitment, not noise. |
| 2026-06-20 | Phase 1 Track C #2 — PEEP-aware compliance (✅ validated) | Data-learned recruitment slope β≈0.083/cmH₂O (compliance +40% PEEP↑, −23% PEEP↓). Honest train/test: **PEEP-change MAE 4.48→3.21, 28% better** on held-out patients. First validated model improvement; prototype's guessed ×0.1 ≈ data. Confirm on full MIMIC-IV → then implement in physiology.py (Phase 2). |
| 2026-06-20 | docs — ventilator/ABG data dictionary | Added `docs/_Data_Dictionary.md`: plain-English cheat-sheet of the MIMIC itemids (codes) for ventilator settings + blood gases, units, and demo availability. Pointers added to CLAUDE.md + `_Data_Access.md`. |
