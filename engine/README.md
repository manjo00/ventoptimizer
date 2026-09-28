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
| `physiology.py` | The "what would happen if…" calculator. Predicts pressures, Mechanical Power, and pH for one setting. Does no choosing. |
| `optimizer.py` | The chooser. Tries thousands of settings, drops unsafe ones, keeps the lowest-energy safe one, and explains why. |
| `validate_mimic.py` | The accuracy checker (Phase 1). Replays real MIMIC-IV patients (aggregate output only) and runs the experiments: compliance stability, plateau prediction, recruitment across PEEP steps (the "1b" versions use only plateaus that were really measured, in a controlled mode), CO₂ prediction, and how much power the VT↔rate knob can save. Reads the big table in slices, so it works on the full data. Run: `python engine/validate_mimic.py --demo <MIMIC-IV folder>`. |
| `peep_response_pilot.py` | The per-patient pilot (step 2a). Asks three questions on the usable PEEP-step pairs: how much compliance wobbles when nothing changed (noise floor), whether a patient's response repeats from one step to the next, and whether the patient's own history predicts the next step better than the population slope. Run: `python engine/peep_response_pilot.py --mimic <folder>`. |
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
