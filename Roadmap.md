# VentOptimizer — Roadmap & Workflow

## The zero-waste philosophy (why this folder is organized the way it is)
The goal is to get accurate work from Claude **without burning usage** re-reading everything each time. So the project's memory lives in small Markdown files (the "Project Brain"), and Claude reads **only the file a task needs** (see the reading-order table in `CLAUDE.md`). Ahmed talks in plain language; Claude explains everything back in plain language (Ahmed is not a coder).

**The loop:** read `CLAUDE.md` + `docs/_Current_Task.md` → git checkpoint → do + explain → log to `docs/_Task_History.md` → commit.

---

## Phases

### Phase 0 — Setup ✅
Folder renamed to VentOptimizer, git initialized, Project Brain seeded, v2.4 logic ported to Python, prototype extracted to `app/`, manuscript distilled into the evidence base.

### Scope focus (refined 2026-06-20)
We proved the *safe, easy* knob (rebalance VT↔RR) barely moves mechanical power. So the project now hinges on the **two real MP levers**, and each has **two questions** — both answered with **high-quality / Q1 evidence**:
1. **Permissive hypercapnia** *(solvable now)* — (a) how far can CO₂ rise / how low can pH go **safely**? (b) how much MP does that buy? (Gate: not for raised-ICP / brain injury.)
   - **Note — manual limit:** allow the practitioner to set a patient-specific pH/CO₂ limit from their own knowledge of the case (same pattern as the manual dead-space override). The tool uses the **stricter** of that manual limit and the evidence-based floor.
2. **PEEP / recruitment** *(the parked hard problem)* — (a) how to handle the individual, unpredictable response? (b) how much MP does it actually affect? Return to this after #1.

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
