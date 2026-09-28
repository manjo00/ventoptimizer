# Data Dictionary — the MIMIC-IV codes we use (ventilator, gases, vitals, gates, patient, outcome)

Quick reference so we never have to re-hunt for the data. In MIMIC there is **no
"ventilator" file** — every bedside reading sits in one giant table, identified by
a number code.

- **The bedside readings live in:** `icu/chartevents.csv.gz` (one row per reading: *stay · time · code · value*).
- **The decoder (number → name) is:** `icu/d_items.csv.gz` (lab codes: `hosp/d_labitems.csv.gz`).
- **Other tables we use:** `icu/inputevents` (drug infusions), `icu/outputevents` (drains), `icu/procedureevents` (ventilation episodes, intubation), `hosp/labevents` (lab blood gases), `hosp/patients` / `hosp/admissions` / `icu/icustays` (age, sex, death, stay times), `hosp/omr` (outpatient height/weight).
- **"Demo coverage"** below = readings / ventilated stays with ≥1 reading, as a share of the **67 ventilated stays** in the open 100-patient demo (from `engine/check_coverage.py`, 2026-09-28). Same codes apply in full MIMIC-IV.
- **Tier** = role in the PEEP math (see `docs/_Required_Variables.md`): **REQ** the math cannot run without it · **REC** safer/more accurate, has a fallback · **OPT** cross-check or rare-but-valuable.

## A. Ventilator mechanics (d_items category = `Respiratory`)
| Code (itemid) | Plain meaning | Unit | Tier | Harness field | Demo coverage |
|---|---|---|---|---|---|
| **224685** | Tidal Volume (observed) — breath size actually delivered | mL | REQ | `vt` ✅ used | 1,331 / 67 (100%) |
| 224684 | Tidal Volume (set) — the dial value | mL | REC | (fallback) | 769 / 62 (93%) |
| 224686 | Tidal Volume (spontaneous) | mL | — | — | — |
| **220339** | PEEP set — pressure held between breaths | cmH₂O | REQ | `peep` ✅ used | 1,447 / 67 (100%) |
| 224700 | Total PEEP Level (set + auto-PEEP) | cmH₂O | REC | (true ΔP) | 490 / 55 (82%) |
| 224699 | ZAuto Peep Level | cmH₂O | OPT | — | 0 in demo |
| **224696** | **Plateau Pressure** — lung-stretch pressure (inspiratory hold) | cmH₂O | REQ | `pplat` ✅ used | 510 / 56 (84%) |
| **224695** | Peak Insp. Pressure — highest pressure in the breath | cmH₂O | REQ | `ppeak` ✅ used | 1,319 / 66 (99%) |
| 224697 | Mean Airway Pressure | cmH₂O | OPT | — | 1,342 / 67 (100%) |
| **220210** | Respiratory Rate (vital sign, hourly) | /min | REQ | `rr` ✅ used | 10,077 / 67 (100%) |
| 224690 | Respiratory Rate (Total) — ventilator-measured | /min | REC | (alt) | 1,331 / 67 (100%) |
| 224688 | Respiratory Rate (Set) | /min | REC | — | 801 / 63 (94%) |
| 224689 | Respiratory Rate (spontaneous) — **> 0 means the patient is breathing → plateau unreliable** | /min | REC | passivity check | 1,314 / 66 (99%) |
| **223849** | Ventilator Mode (text; Dräger vocabulary) | — | REQ | mode filter | 1,048 / 54 |
| **229314** | Ventilator Mode (Hamilton vocabulary) | — | REQ | mode filter | 402 / 18 (both: 100%) |
| 223848 | Ventilator Type (Drager / Hamilton / …) | — | OPT | — | 1,292 / 66 (99%) |
| 224687 | Minute Volume | L/min | OPT | VE cross-check | 1,359 / 67 (100%) |
| 224738 | Inspiratory Time | s | OPT | Te = 60/RR − Ti | 740 / 65 (97%) |
| 226873 / 226871 | Inspiratory Ratio / Expiratory Ratio (the I:E) | — | OPT | — | 1,016 / 50 (75%) |
| 224691 | Flow Rate (inspiratory) | L/min | OPT | resistance → τ | 330 / 19 (28%) |
| 224692 / 224735 | Flow Pattern (Variable / Sq.) / (variable-fixed) | — | OPT | — | 1,237 / 66 |
| 224701 | PSV Level (pressure support) | cmH₂O | OPT | flags support mode | 698 / 59 (88%) |
| 224705 / 224706 | P High / P Low (APRV) | cmH₂O | OPT | flags APRV (exclude) | 8 / 3 (5%) |
| 229661 | Compliance (ventilator-computed) | — | OPT | cross-check | 0 in demo |
| 220283 / 229665 / 229664 | Resistance / Resistance Insp / Exp (ventilator-computed) | cmH₂O/L/s | OPT | cross-check | 0 in demo |
| **224746 / 224747** | **Transpulmonary Pressure (Exp. Hold / Insp. Hold)** — esophageal-balloon-derived; **the pleural reference we thought MIMIC lacked** | cmH₂O | OPT★ | validation subset | 26 / 2 (3%) |
| 227187 | Pinsp (Draeger only) | cmH₂O | OPT | — | 2 / 2 |

## B. Blood gases & oxygenation
| Code | Plain meaning | Unit | Tier | Harness field | Demo coverage |
|---|---|---|---|---|---|
| **223835** | Inspired O₂ Fraction (FiO₂) | fraction | REQ | (P/F, S/F) | 1,660 / 67 (100%) |
| **220277** | O₂ saturation, pulse oximetry (SpO₂) — hourly, dense | % | REQ | oxygenation response | 9,815 / 67 (100%) |
| **223830** | pH (Arterial) | — | REQ | `ph` ✅ used | 584 / 58 (87%) |
| **220235** | Arterial CO₂ Pressure (PaCO₂) | mmHg | REQ | `paco2` ✅ used | 567 / 58 (87%) |
| 220224 | Arterial O₂ pressure (PaO₂) | mmHg | REC | P/F | 567 / 58 (87%) |
| 220227 | Arterial O₂ Saturation (SaO₂) | % | OPT | — | 93 / 31 (46%) |
| 225698 | TCO₂ (calc) Arterial — bicarbonate proxy | mmol/L | REC | HCO₃ proxy | 567 / 58 (87%) |
| 227443 | HCO₃ (serum) | mmol/L | REC | HCO₃ | 677 / 66 (99%) |
| 228640 | EtCO₂ | mmHg | OPT | dead-space fraction | 194 / 13 (19%) |
| 220274 / 226062 / 223679 | pH (Venous) / Venous CO₂ / TCO₂ venous | — | — | not used | — |
| **Lab ABG panel** `hosp/labevents`: 50820 pH · 50818 pCO₂ · 50821 pO₂ · 50804 Calculated Total CO₂ · 50802 Base Excess · 50817 O₂ Saturation · 52033 Specimen Type (to keep arterial) | — | REC | timed gas, second source | 3,336 / 63 (94%) |
| Lab ABG vent fields: 50819 PEEP · 50826 Tidal Volume · 50827 Ventilation Rate · 50812 Intubated · 50828 Ventilator · 52023 Assist/Control | — | OPT | settings at gas time | 301 / 28 (42%) |
| 50882 | Bicarbonate (chemistry) | mmol/L | REC | HCO₃ | 676 / 65 (97%) |
| 50813 | Lactate | mmol/L | OPT | perfusion safety | 427 / 60 (90%) |

## C. Hemodynamics (is raising PEEP safe for the circulation?)
| Code | Plain meaning | Unit | Tier | Demo coverage |
|---|---|---|---|---|
| 220052 | Arterial Blood Pressure mean (invasive line) | mmHg | REC | 4,707 / 45 (67%) |
| 220181 | Non Invasive Blood Pressure mean (cuff) | mmHg | REC | 5,479 / 66 (99%) |
| 220045 | Heart Rate | bpm | OPT | 10,081 / 67 (100%) |
| 220074 | Central Venous Pressure — **spot values (hourly), not a waveform** | mmHg | REC | 1,200 / 33 (49%) |
| `inputevents` 221906 Norepinephrine · 221749 Phenylephrine · 222315 Vasopressin · 221289 Epinephrine · 221662 Dopamine · 221653 Dobutamine | vasopressor / inotrope infusions (rate, start, end) | — | REC | 1,512 / 42 (63%) |

## D. Gates / contraindications
| Code | Plain meaning | Tier | Demo coverage |
|---|---|---|---|
| 220765 / 227989 | Intra Cranial Pressure (#1 / #2) — **raised-ICP gate** (no permissive hypercapnia; PEEP caution) | REQ when present | 313 / 2 (3%) |
| 226474 / 229518 (procedures) | ICP bolt / Camino inserted | OPT | rare |
| 226588 / 226589 (`outputevents`) · 223993 / 224438 (chart) · 225433 / 227712 (procedures) | Chest tube output / site / placed / removed — **air-leak gate** | REC | 1,026 / 24 (36%) |
| `inputevents` 221555 Cisatracurium · 222062 Vecuronium | Neuromuscular blocker infusion → **passive mechanics guaranteed** | REC | 0 in demo (codes exist) |

## E. Patient descriptors
| Source | Plain meaning | Tier | Demo coverage |
|---|---|---|---|
| 226730 Height (cm) · 226707 Height (Inch) | height → **PBW** (predicted body weight) → VT/kg limits | REQ | 96 / 48 (**72%** of ventilated stays) |
| `hosp/omr` result_name = "Height (Inches)" | outpatient height — **fallback** | REQ (fallback) | raises height to 59 / 67 (**88%**) |
| 226512 Admission Weight (Kg) · 224639 Daily Weight · 226531 Admission Weight (lbs) | weight → BMI | REC | 432 / 66 (99%) |
| `hosp/patients`: gender, anchor_age | sex / age → PBW formula | REQ | 100% |

## F. Timing / cohort
| Source | Plain meaning | Tier | Demo coverage |
|---|---|---|---|
| `procedureevents` 225792 Invasive Ventilation (starttime, endtime) | ventilation episodes → days on vent, ventilator-free days | REQ | 65 / 60 (90%) |
| 225794 Non-invasive Ventilation · 224385 Intubation · 227194 Extubation · 225468 Unplanned Extubation | episode boundaries | OPT | 66 / 50 (75%) |
| `icu/icustays`: intime, outtime, los | stay window (also used to attach labs to a stay) | REQ | 100% |

## G. Outcomes (validation only — never an input to the math)
| Source | Plain meaning | Demo |
|---|---|---|
| `hosp/admissions`: hospital_expire_flag, deathtime | died in hospital | 14 / 67 ventilated stays (20.9%) |
| `hosp/patients`: dod (date of death, incl. after discharge) | 28-day / 90-day mortality (dod ≤ ICU intime + 28 d) | computed by `check_coverage.py` |

## Ventilator-mode strings (values of 223849 / 229314) — which breaths count as "controlled"
Plateau pressure and compliance are only meaningful in **controlled, passive** breaths. Demo distribution of mode rows (aggregate):
- **Controlled (kept):** `CMV/ASSIST/AutoFlow` 467 · `APV (cmv)` 220 · `CMV/ASSIST` 29 · `P-CMV` 15 (also listed for full MIMIC: `CMV`, `PCV+`, `SIMV*`, `PRVC*`).
- **Support / spontaneous (excluded from mechanics):** `CPAP/PSV` 467 · `SPONT` 148 · `PSV/SBT` 27 · `Standby` 22 · `MMV/PSV/AutoFlow` 21 · `VS` 10 · `CPAP/PSV+ApnVol` 8 · `NIV` 7 · others ≤ 2.
- **≈ 50% of mode rows are controlled** → roughly half of ventilated time is *not* usable for plateau-based mechanics.
- The classification list lives in `CONTROLLED_MODES` inside `engine/check_coverage.py`; the script prints any string it hasn't seen.

## Notes / gotchas
- **Plateau (224696) is the scarce one** — 510 readings vs 1,447 PEEP readings: it is charted at roughly **one vent check in three**, because it needs an inspiratory-hold maneuver. It is the field the model anchors on.
- **⚠ The forward-fill trap (found 2026-09-28):** the harness carries the last plateau forward in time. That is fine while PEEP is unchanged, but **after a PEEP change a carried plateau is a stale number measured at the OLD PEEP** — using it as the "after" measurement manufactures a fake compliance change in exactly the direction we reported (PEEP↑ → compliance "↑"). Any PEEP-response analysis must use a plateau **charted after the change, at the new PEEP**. `check_coverage.py` counts those usable pairs.
- **Bicarbonate (HCO₃):** no clean single vent code; use TCO₂ (225698), serum HCO₃ (227443), or lab bicarbonate (50882).
- **"observed" vs "set"** tidal volume: we use *observed* (224685) = what the lung actually got.
- **Labs are keyed by admission (`hadm_id`), not by ICU stay** — attach a lab to a stay by admission + time inside `intime…outtime` (done in `check_coverage.py`).
- **Height is missing in ~30% of ventilated stays** at the bedside; the outpatient `omr` table recovers about half of those. Without height there is no PBW and no VT/kg limit → such stays are excluded (or need a stated fallback).
- These codes are the same in **full MIMIC-IV**, so the scripts work unchanged when Ahmed runs them on the full data.

## The exact mappings the code uses
- `ITEMS = {...}` at the top of `engine/validate_mimic.py` — the 7 fields the accuracy harness pivots on.
- `VARIABLES = [...]` at the top of `engine/check_coverage.py` — the full tiered list above, in code form. To add a field, add it here and there.
