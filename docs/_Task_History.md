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
