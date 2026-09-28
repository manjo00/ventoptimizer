# Schema — the data shapes

These are the objects that move through the system. (Plain-language: think of each as a labelled form with fields.) Updated 2026-09-28 when the safe-PEEP ceiling was wired into the optimizer.

## PatientCase — who the patient is
| Field | Meaning | Unit |
|---|---|---|
| `pbw` | Predicted body weight (from height + sex) | kg |
| `base_paco2` | Current arterial CO₂ | mmHg |
| `hco3` | Bicarbonate (buffering capacity) | mmol/L |
| `permissive` | Allow higher CO₂ (pH floor 7.20 instead of 7.30)? | true/false |
| `pf_ratio` *(optional)* | Oxygenation: PaO₂ ÷ FiO₂ (lower = worse lungs) — information only | ratio |
| `ri_index` *(optional)* | A **measured** Recruitment-to-Inflation index (bedside maneuver `[N1]`; >0.5 = recruitable) — **information only, it no longer changes the math** | 0–1 |
| `age`, `sex`, `height_cm`, `weight_kg`, `use_hb` *(optional)* | Enable the opt-in Harris–Benedict dead space | — |
| `measured_deadspace_ml`, `measured_vd_vt` *(optional)* | A measured dead space — always wins when given | mL / 0–1 |

## Baseline — the patient's CURRENT ventilator settings and state (measured)
| Field | Meaning | Unit |
|---|---|---|
| `vt` | Tidal volume (breath size) | mL |
| `rr` | Respiratory rate (breaths/min) | /min |
| `peep` | Positive end-expiratory pressure (pressure kept at end of breath) | cmH₂O |
| `pplat` | **Plateau pressure — measured via an inspiratory hold. REQUIRED** (anchors lung stiffness) | cmH₂O |
| `ppeak` | Peak airway pressure | cmH₂O |
| *state for the safe-PEEP ceiling (all optional):* `fio2`, `spo2`, `pao2`, `peep_total`, `rr_spont`, `controlled_mode`, `map_mmHg`, `vasopressor_running`, `icp`, `chest_tube`, `dpl_measured` | What `engine/safe_peep.py` needs for the ceilings and gates (see `_Clinical_Logic` §8) | — |

## CandidateSetting — one setting the optimizer is testing
`vt`, `rr`, `pinsp` (inspiratory pressure) at the **current** `peep`. In Volume mode (VC) the tool sets `vt`; in Pressure mode (PC) it sets `pinsp` and predicts the resulting `vt`. **PEEP is not a search knob any more** — it is held, and handled by the PEEP-guidance block (below).

## Prediction — what physiology.py returns for a candidate
| Field | Meaning |
|---|---|
| `mp_tidal` | **Tidal (driving-pressure) power (J/min) — the number we minimize and compare by** |
| `mp` | Absolute Mechanical Power, Gattinoni plateau form (J/min) `[E1]` |
| `mp_dyn` | Absolute power, the manuscript's peak-only surrogate (J/min) `[M][N8]` — reported alongside, never mixed with `mp` in one comparison |
| `mp_formula` | Which absolute form was used (plateau form, or the surrogate when no plateau exists) |
| `pplat` | Predicted plateau pressure |
| `driving_p` | Driving pressure = Pplat − PEEP (lung stretch per breath) |
| `ppeak` | Predicted peak pressure |
| `ph`, `paco2` | Predicted blood pH and CO₂ |
| `tau`, `te` | Time constant and expiratory time (for auto-PEEP / breath-stacking check) |
| `compliance` | Compliance used (mL/cmH₂O) — **unchanged** across a PEEP step (the best-supported point estimate) |
| `compliance_range`, `pplat_range`, `mp_tidal_range` | For a PEEP step: the (low, high) range of what compliance, plateau and tidal power might do — **placeholder from the open demo** until the full-MIMIC state model exists |

## Limits — the hard safety gates (a candidate is rejected if it fails any)
| Limit | Value | Source |
|---|---|---|
| `max_pplat` | 30 cmH₂O | `[E3]` ARDSNet — `_Evidence_Base.md` |
| `max_vt_kg` / `min_vt_kg` | 8 / 4 mL/kg PBW | `[E3]` lung-protective range |
| `min_ph` | 7.30 (or 7.20 permissive) | `[E3][E6]` permissive hypercapnia conventions |
| breath-stacking | `te ≥ 3 × tau` (95% exhalation) | time-constant physiology `[E5]` (the 1-s inspiration is an `[ASSUMPTION]`) |
| ~~recruitment rules~~ | *retired 2026-09-28* — no PEEP rules inside the search; PEEP has its own ceiling and gates | `_Research_Log` 1b/2a |
| driving pressure > 15 | **flagged**, not rejected (the tidal-power score already pushes it down) | `[N9][E4]` |

## SafePeepResult — the ceiling (engine/safe_peep.py)
`peep_now`, `compliance_now`, `peep_max_safe` (the ceiling, or the current PEEP when an increase is vetoed), `binding_constraint`, `projected_pplat_at_max`, `projected_dp_at_max`, `envelope_low`/`envelope_high` (the ARDSNet PEEP/FiO₂ range), `oxygenation` (status text), `vetoes` (reasons that forbid any increase), `cautions`, `notes`.

## OptimizerResult — the final answer
`setting` (a CandidateSetting at the current PEEP), `prediction` (a Prediction), `baseline_power` (`mp`, `mp_dyn`, `mp_tidal` of the current settings), `explanation` (plain-language text), `peep_ceiling` (a SafePeepResult), `peep_guidance` (text: the ceiling, the range for each possible PEEP step, and the test-step protocol). `setting` is `None` if nothing was safe.
