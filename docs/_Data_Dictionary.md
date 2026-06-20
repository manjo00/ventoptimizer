# Data Dictionary — ventilator & blood-gas codes (MIMIC-IV)

Quick reference so we never have to re-hunt for the data. In MIMIC there is **no
"ventilator" file** — every bedside reading sits in one giant table, identified by
a number code.

- **The data lives in:** `icu/chartevents.csv.gz` (one row per reading: *patient · time · code · value*).
- **The decoder (number → name) is:** `icu/d_items.csv.gz`.
- "Demo readings" below = how many rows existed in the open 100-patient demo (a rough sense of availability).

## Ventilator settings (d_items category = `Respiratory`)
| Code (itemid) | Plain meaning | Unit | Harness field | Demo readings |
|---|---|---|---|---|
| **224685** | Tidal Volume (observed) — breath size actually delivered | mL | `vt` ✅ used | 1,331 |
| 224684 | Tidal Volume (set) — breath size the dial is set to | mL | (alt) | 769 |
| 224686 | Tidal Volume (spontaneous) | mL | — | — |
| **220339** | PEEP set — baseline pressure held between breaths | cmH₂O | `peep` ✅ used | 1,447 |
| 224700 | Total PEEP Level (incl. auto-PEEP) | cmH₂O | (alt) | 490 |
| **224696** | **Plateau Pressure** — true lung-stretch pressure (inspiratory hold) | cmH₂O | `pplat` ✅ used | 510 |
| **224695** | Peak Insp. Pressure — highest pressure in the breath | cmH₂O | `ppeak` ✅ used | 1,319 |
| 224697 | Mean Airway Pressure | cmH₂O | — | 1,342 |
| **220210** | Respiratory Rate — breaths per minute | insp/min | `rr` ✅ used | 13,913 |
| 224690 | Respiratory Rate (Total) | insp/min | (alt) | 1,331 |
| 223835 | Inspired O₂ Fraction (FiO₂) | fraction | (for P/F) | 1,746 |

## Blood gases (d_items category = `Labs`, "Arterial")
| Code (itemid) | Plain meaning | Unit | Harness field | Demo readings |
|---|---|---|---|---|
| **223830** | pH (Arterial) — blood acidity | — | `ph` ✅ used | 644 |
| **220235** | Arterial CO₂ Pressure (PaCO₂) | mmHg | `paco2` ✅ used | 623 |
| 220224 | Arterial O₂ pressure (PaO₂) | mmHg | (for P/F) | 623 |
| 225698 | TCO₂ (calc) Arterial — bicarbonate proxy | mmol/L | (HCO₃ proxy) | 623 |

## Notes / gotchas
- **Plateau (224696) is the scarce one** — only 510 readings, because it needs an inspiratory-hold maneuver that's rarely charted. It's the field the model anchors on, so its scarcity limits how much we can validate. (Same reason the manuscript used *peak*-based dynamic MP.)
- **Bicarbonate (HCO₃):** not a clean single vent code; use the ABG TCO₂ proxy (225698) **or** serum bicarbonate from `hosp/labevents.csv.gz` (lab itemid `50882`). Needed for the pH formula.
- **"observed" vs "set"** tidal volume: we use *observed* (224685) = what the lung actually got.
- These codes are the same in **full MIMIC-IV**, so the harness works unchanged when Ahmed runs it on the full data.

## The exact mapping the harness uses
See the `ITEMS = {...}` block at the top of `engine/validate_mimic.py` — it is this table in code form. To add a field, add its code here and there.
