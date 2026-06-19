# Architecture — how the pieces fit (1 page)

## The core idea
Give the tool a **patient's current state + current ventilator settings**. It tries **thousands of alternative settings**, predicts what each would do to the lungs and blood gases, throws away the unsafe ones, and returns the **safe setting with the lowest Mechanical Power**.

## Data flow
```
PatientCase + Baseline
        │
        ▼
 physiology.predict(setting)  ← for each candidate setting: predicts Pplat, MP, pH, auto-PEEP risk
        │
        ▼
 optimizer.grid_search()      ← loops all candidate settings, applies safety constraints, scores survivors
        │                        score = Mechanical Power + small penalty for straying from baseline
        ▼
 best CandidateSetting + plain-language explanation
```

## Two implementations, one brain
| Layer | File(s) | Role | Status |
|---|---|---|---|
| **Research engine (source of truth)** | `engine/physiology.py`, `engine/optimizer.py` | The real, testable model. All accuracy work happens here. | Phase 1 |
| **Validation** | `engine/validate_mimic.py` | Shadow-tests the engine against real MIMIC-IV patients. | Phase 1 deliverable |
| **Bedside front-end** | `app/ventoptimizer.html` | The clickable demo a clinician would use. Mirrors the engine. | Prototype (v2.4) |

Rule: the web app must only ever implement physiology the **Python engine has proven**. Python leads; HTML follows.

## File responsibilities
| File | Owns | Does NOT own |
|---|---|---|
| `physiology.py` | All prediction math (compliance, MP, gas exchange, time constants) | Searching settings, safety limits |
| `optimizer.py` | The grid search, the safety constraints, the scoring/penalty | The physics formulas (it calls `physiology.py`) |
| `validate_mimic.py` | Loading MIMIC cases, comparing predicted vs observed | The model itself |
| `ventoptimizer.html` | UI + a JS copy of the same logic for the demo | Anything the engine hasn't validated |

## Where the numbers come from
Every formula in `physiology.py`/`optimizer.py` maps to an entry in `docs/_Clinical_Logic.md`, which in turn cites `docs/_Evidence_Base.md`. If a number has no citation, it is an `[ASSUMPTION]` and must be flagged.
