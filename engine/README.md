# engine/ — the Python research engine

This folder is the **brain** of VentOptimizer: the real, testable model. (The web
app in `app/` is just a demo face; this is what we trust and improve.)

## What you need (one-time)
- **Python 3** installed. Check by opening a terminal and typing `python --version`.
- Nothing else for the optimizer — it uses only built-in Python (no installs).
- (Later, the MIMIC validation will need `pandas`; we'll install it when we get there.)

## The files
| File | What it does (plain language) |
|---|---|
| `physiology.py` | The "what would happen if…" calculator. Predicts pressures, Mechanical Power, and pH for one setting. Does no choosing. |
| `optimizer.py` | The chooser. Tries thousands of settings, drops unsafe ones, keeps the lowest-energy safe one, and explains why. |
| `validate_mimic.py` | The accuracy checker (Phase 1). Replays real patients and compares predicted vs what actually happened. Currently a skeleton with fake demo data. |

## How to run them
Open a terminal **in the project folder** and type:

```bash
python engine/optimizer.py        # see a recommended setting for the example patient
python engine/validate_mimic.py   # see the accuracy-check format (synthetic demo for now)
```

Each prints a plain-language result. If you see an error, copy the whole message
to Claude — no need to understand it yourself.

## The golden rules (also in CLAUDE.md)
- Every formula traces to a citation in `docs/_Evidence_Base.md`. No invented numbers.
- This advises a clinician; it never decides.
- When the code changes, Claude explains the change in plain words.
