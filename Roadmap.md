# VentOptimizer — Roadmap & Workflow

## The zero-waste philosophy (why this folder is organized the way it is)
The goal is to get accurate work from Claude **without burning usage** re-reading everything each time. So the project's memory lives in small Markdown files (the "Project Brain"), and Claude reads **only the file a task needs** (see the reading-order table in `CLAUDE.md`). Ahmed talks in plain language; Claude explains everything back in plain language (Ahmed is not a coder).

**The loop:** read `CLAUDE.md` + `docs/_Current_Task.md` → git checkpoint → do + explain → log to `docs/_Task_History.md` → commit.

---

## Phases

### Phase 0 — Setup ✅
Folder renamed to VentOptimizer, git initialized, Project Brain seeded, v2.4 logic ported to Python, prototype extracted to `app/`, manuscript distilled into the evidence base.

### Phase 1 — Model accuracy & research  ← WE ARE HERE
Prove how accurate the predictions are, then fix the weakest assumptions.
- Reproduce v2.4 behaviour in Python (done in setup; verify).
- Build the **MIMIC-IV shadow-testing harness** (`validate_mimic.py`).
- Quantify prediction error (plateau pressure, MP, pH).
- Tackle the open questions in `docs/_Research_Agenda.md` worst-first (likely: linear compliance → recruitment formula → CO₂/dead-space).
- **Exit:** a validation report + a prioritized, evidence-backed fix list.

### Phase 2 — Engine hardening
Implement the validated improvements (nonlinear compliance if justified, better dead space, EtCO₂ proxy for the ABG-lag problem, possibly add driving pressure to the objective).

### Phase 3 — App sync
Update `app/ventoptimizer.html` so the bedside demo matches the proven engine. UX cleanup. Clear "suggestion, not a decision" framing.

### Phase 4 — Write-up
Turn the validation into an abstract/paper (reuses the manuscript skill set and the same MIMIC pipeline).

---

## Guardrails that never change
- **Decision-support, not a medical device.** Output is always a clinician-reviewed suggestion.
- **No uncited clinical numbers.** Everything traces to `docs/_Evidence_Base.md`.
- **Explain the code.** Every change comes with a plain-language explanation.
- **Git checkpoints.** Always a rollback point.
