# CLAUDE.md — VentOptimizer
# Read this whole file before touching anything. It is the master context.

VentOptimizer recommends mechanical-ventilator settings (tidal volume, respiratory rate, PEEP, inspiratory pressure) that **minimize Mechanical Power** — the energy delivered to the lungs each minute — while staying inside hard safety limits, to reduce Ventilator-Induced Lung Injury (VILI). It is a **decision-support prototype, not a medical device.**

The evidence that minimizing Mechanical Power is the right goal comes from Ahmed's own MIMIC-IV study: each +1 J/min of power raised the adjusted odds of 28-day death by ~9%, with risk rising steadily and **no safe threshold even below 17 J/min** (see `docs/_Evidence_Base.md`).

---

## 🔴 THREE NON-NEGOTIABLES

### 1. 🧑‍🏫 Teaching mode — Ahmed is NOT a programmer
- Whenever you write or change code, **explain in plain language what it does and how it works** — before or right after the code, not just in comments.
- Define every coding or clinical term **once**, simply, the first time it appears in a reply.
- Prefer clear, boring code over clever code. Short functions, obvious names.
- Never assume Ahmed can read code. If a bug needs his input, describe the behavior in plain words, not stack traces.

### 2. 🩺 Clinical safety — evidence or it doesn't go in
- **Every formula, constant, and threshold must trace to a citation in `docs/_Evidence_Base.md`.** No invented clinical numbers, ever.
- If something is an assumption or a guess, say so out loud and tag it `[ASSUMPTION]` in the docs.
- This tool advises; it never decides. Always frame output as a suggestion a clinician reviews.

### 3. 🟢 Git checkpoint every session
This folder is a git repo. Before changing files, create a rollback point yourself:
```bash
git add -A && git commit -m "checkpoint: before <task>"
```
Commit again when the task is done:
```bash
git add -A && git commit -m "feat/fix/docs: <task>"
```
End commit messages with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

**☁️ Backup to GitHub — push after EVERY task.** The remote `origin` is the main backup:
`https://github.com/manjo00/ventoptimizer.git`. After each task's final commit, immediately:
```bash
git push origin HEAD
```
Never leave a finished task with unpushed commits. If a push fails (auth or conflict), tell Ahmed in plain language and stop — do **not** force-push without asking him first.

---

## 🔒 DATA GOVERNANCE — credentialed data NEVER comes to Claude

When we validate against MIMIC (or any credentialed dataset):
- **Patient data stays on the local machine. Never paste it to Claude.** PhysioNet's data-use agreement forbids sharing credentialed data with third-party AI / online services.
- **The loop:** Claude writes the code → the **credentialed person runs it locally** → only **aggregate, de-identified results** (mean errors, counts, plots) come back to Claude.
- **Safe to share with Claude:** column names, the data dictionary, aggregate numbers, error tables. **Never:** individual patient rows, identifiers (subject_id values, dates), raw extracts.
- Never `git commit` patient data — keep it outside the repo (the `.gitignore` blocks common data folders). Practical checklist: `docs/_Data_Access.md`.

---

## 📋 HOW A SESSION WORKS

1. **Read `CLAUDE.md` + `docs/_Current_Task.md`.** That's usually all the context you need.
2. **Challenge first.** If the request is ambiguous, contradicts the evidence base, or is unsafe — push back with one focused question before doing anything.
3. **Restate** the task in ~2 sentences and **list the exact files** you'll touch.
4. **Git checkpoint** (command above).
5. **Write the task** into `docs/_Current_Task.md` using the template at the bottom of that file.
6. **Do the work — and explain it** in plain language as you go (teaching mode).
7. **Spotted an unrelated problem?** Note it under `## Noticed (not fixing now)` in `_Current_Task.md`. Don't fix it now.
8. **When done, always:** append one line to `docs/_Task_History.md`, update any doc whose facts changed, `git commit`, then **`git push origin HEAD`** (back up to GitHub).

---

## 🔋 ZERO-WASTE READING ORDER (read ONLY what the task needs)

The whole point of this setup is to NOT re-read everything. Match the task to the minimum file:

| If the task is about… | Read only |
|---|---|
| The physiology / equations / "why" | `docs/_Clinical_Logic.md` |
| The research evidence / a clinical number | `docs/_Evidence_Base.md` |
| Data shapes (inputs/outputs/limits) | `docs/_Schema.md` |
| How pieces connect | `docs/_Architecture.md` |
| What to do next / open questions | `docs/_Research_Agenda.md` + `Roadmap.md` |
| The Python engine code | `engine/README.md`, then the one `.py` file named |
| The web prototype | `app/ventoptimizer.html` |
| Source material (manuscript, prototype) | `reference/` |

Do **not** open `reference/` PDFs unless a number isn't already in `_Evidence_Base.md`.

---

## 🗺 STACK & FILE MAP

**Stack:** Python (research + validation engine — the accuracy work) · plain HTML/JS (the bedside front-end prototype). No frameworks, no build step. Python is the source of truth; the web app only ships physiology the Python engine has proven.

```
VentOptimizer/
├── CLAUDE.md              ← this file (read first)
├── Roadmap.md             ← phased plan + the zero-waste philosophy
├── docs/                  ← the Project Brain (modular context)
│   ├── _Architecture.md   ├── _Clinical_Logic.md  ├── _Schema.md
│   ├── _Evidence_Base.md  ├── _Research_Agenda.md
│   ├── _Current_Task.md   └── _Task_History.md
├── engine/                ← Python: physiology.py · optimizer.py · validate_mimic.py · README.md
├── app/                   ← ventoptimizer.html (v2.4 prototype)
├── reference/             ← READ-ONLY source: Manuscript_V3.pdf, Research Poster.pdf, Mega-Prompt Context.md
└── poster_day/            ← parked poster deliverables (unrelated to the engine)
```

---

## 📍 WHERE WE ARE

- **Phase 0 — Setup:** ✅ done (brain seeded, code ported, git initialized).
- **Phase 1 — Model accuracy & research:** ← current. Goal: validate the physiology predictions against real data (MIMIC-IV shadow testing) and fix the weakest assumptions. See `docs/_Research_Agenda.md`.

The model's biggest *unproven* assumptions (do not trust these as accurate yet): **linear lung compliance**, the **R/I-index recruitment heuristic**, and **simplified CO₂ kinetics**. Validating/replacing these is Phase 1's job.

---

## 🚫 NEVER DO
1. Put a clinical number in code without a citation in `_Evidence_Base.md`.
2. Present output as a decision rather than a clinician-reviewed suggestion.
3. Write code without explaining it to Ahmed in plain language.
4. Skip the git checkpoint.
5. Edit files in `reference/` (source material — read-only).
6. Fix unrelated bugs mid-task — log them under `## Noticed` instead.

*Last updated: 2026-06 (Phase 0 setup). Update this file when the architecture or phase changes.*
