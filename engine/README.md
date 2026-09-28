# engine/ — the Python research engine

This folder is the **brain** of VentOptimizer: the real, testable model. (The web
app in `app/` is just a demo face; this is what we trust and improve.)

## What you need (one-time)
- **Python 3** installed. Check by opening a terminal and typing `python --version`.
- Nothing else for the optimizer — it uses only built-in Python (no installs).
- The two MIMIC scripts need `pandas` and `numpy` (one-time: `pip install pandas numpy`).

## The files
| File | What it does (plain language) |
|---|---|
| `physiology.py` | The "what would happen if…" calculator. Predicts pressures, the three labelled power numbers (tidal power = the one we compare by; Gattinoni's plateau form; the manuscript's peak-only surrogate), and pH for one setting. Across a PEEP step it assumes compliance unchanged and attaches a range. Does no choosing. |
| `optimizer.py` | The chooser. Tries every VT/rate (or Pinsp/rate) combination **at the current PEEP**, drops unsafe ones, keeps the lowest **tidal power**, and explains why. Then the PEEP guidance: the safe ceiling (from `safe_peep.py`), what each step inside the safe interval might do (a range), and the test-step protocol. PEEP is never "optimized" — no validated model predicts the lung's response yet. |
| `validate_mimic.py` | The accuracy checker (Phase 1). Replays real MIMIC-IV patients (aggregate output only) and runs the experiments: compliance stability, plateau prediction, recruitment across PEEP steps (the "1b" versions use only plateaus that were really measured, in a controlled mode), CO₂ prediction, and how much power the VT↔rate knob can save. Reads the big table in slices, so it works on the full data. Run: `python engine/validate_mimic.py --demo <MIMIC-IV folder>`. |
| `peep_response_pilot.py` | The per-patient pilot (step 2a). Asks three questions on the usable PEEP-step pairs: how much compliance wobbles when nothing changed (noise floor), whether a patient's response repeats from one step to the next, and whether the patient's own history predicts the next step better than the population slope. Run: `python engine/peep_response_pilot.py --mimic <folder>`. |
| `safe_peep.py` | The ceiling (sub-problem 1). From the current chart only, it finds the highest PEEP at which the plateau, driving pressure and estimated lung stress still stay under their cited limits (with a cautious worst-case margin), caps it with the ARDSNet PEEP/FiO₂ envelope, and applies the safety gates (raised ICP, low blood pressure, invalid mechanics = no increase; chest tube, vasopressor, auto-PEEP = caution). Run: `python engine/safe_peep.py` for a worked example, or `--mimic <folder>` for the aggregate validation. |
| `state_predictor.py` | The full-MIMIC analysis (step 2b), i.e. the frozen plan in `docs/_Analysis_Plan_FullMIMIC.md` in code: attaches each patient's pre-step state to the usable PEEP-step pairs, tests whether that state predicts the compliance change on patients the model never saw, checks the prediction interval, tests whether a first small step predicts the next (the test-step idea), and maps where compliance starts to fall as PEEP rises. Prints aggregates only; labels itself UNDERPOWERED below 300 pairs. Run: `python engine/state_predictor.py --mimic <folder>`. |
| `check_web_port.py` | The mirror check. Pulls the logic out of `app/ventoptimizer.html`, runs it in Node on four invented cases, runs the Python engine on the same cases, and compares every number and reason. Run it after any change to the engine or the page: `python engine/check_web_port.py` (needs Node.js). |
| `check_coverage.py` | The dataset checker. Opens a MIMIC-IV folder and reports, for every variable the PEEP math needs, how often it is present — plus how many PEEP changes are usable. Prints aggregate counts only. Run: `python engine/check_coverage.py --mimic <folder>` (the list it checks is explained in `docs/_Required_Variables.md`). |

## How to run them
Open a terminal **in the project folder** and type:

```bash
python engine/optimizer.py        # see a recommended setting for the example patient
python engine/validate_mimic.py --demo data/mimic-iv-clinical-database-demo-2.2   # the accuracy experiments (aggregate output)
python engine/check_coverage.py --mimic data/mimic-iv-clinical-database-demo-2.2  # does the dataset carry every input we need?
```

Each prints a plain-language result. If you see an error, copy the whole message
to Claude — no need to understand it yourself.

## The golden rules (also in CLAUDE.md)
- Every formula traces to a citation in `docs/_Evidence_Base.md`. No invented numbers.
- This advises a clinician; it never decides.
- When the code changes, Claude explains the change in plain words.
