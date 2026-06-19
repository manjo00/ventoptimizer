# Schema — the data shapes

These are the four objects that move through the system. (Plain-language: think of each as a labelled form with fields.)

## PatientCase — who the patient is
| Field | Meaning | Unit |
|---|---|---|
| `pbw` | Predicted body weight (from height + sex) | kg |
| `pf_ratio` | Oxygenation: PaO₂ ÷ FiO₂ (lower = worse lungs) | ratio |
| `ri_index` | Recruitment-to-Inflation index (how "openable" the lungs are; >0.5 = recruitable) | 0–1 |
| `base_paco2` | Current arterial CO₂ | mmHg |
| `hco3` | Bicarbonate (buffering capacity) | mmol/L |
| `permissive` | Allow higher CO₂ (pH floor 7.20 instead of 7.30)? | true/false |

## Baseline — the patient's CURRENT ventilator settings (measured)
| Field | Meaning | Unit |
|---|---|---|
| `vt` | Tidal volume (breath size) | mL |
| `rr` | Respiratory rate (breaths/min) | /min |
| `peep` | Positive end-expiratory pressure (pressure kept at end of breath) | cmH₂O |
| `pplat` | **Plateau pressure — measured via an inspiratory hold. REQUIRED** (anchors lung stiffness) | cmH₂O |
| `ppeak` | Peak airway pressure | cmH₂O |

## CandidateSetting — one setting the optimizer is testing
`vt`, `rr`, `peep`, `pinsp` (inspiratory pressure). In Volume mode (VC) the tool sets `vt`; in Pressure mode (PC) it sets `pinsp` and predicts the resulting `vt`.

## Prediction — what physiology.py returns for a candidate
| Field | Meaning |
|---|---|
| `mp` | Mechanical Power (J/min) — the thing we minimize |
| `pplat` | Predicted plateau pressure |
| `driving_p` | Driving pressure = Pplat − PEEP (lung stretch per breath) |
| `ppeak` | Predicted peak pressure |
| `ph` | Predicted blood pH |
| `paco2` | Predicted CO₂ |
| `tau`, `te` | Time constant and expiratory time (for auto-PEEP / breath-stacking check) |

## Limits — the hard safety gates (a candidate is rejected if it fails any)
| Limit | Value | Source |
|---|---|---|
| `max_pplat` | 30 cmH₂O | ARDSNet — see `_Evidence_Base.md` |
| `max_vt_kg` / `min_vt_kg` | 8 / 4 mL/kg PBW | lung-protective range |
| `min_ph` | 7.30 (or 7.20 permissive) | permissive hypercapnia `[TO-RESEARCH: cite]` |
| breath-stacking | `te ≥ 3 × tau` (95% exhalation) | time-constant physiology `[ASSUMPTION]` |
| recruitment rules | non-recruitable: no PEEP increase; hypoxic+recruitable: no PEEP drop | heuristic `[ASSUMPTION]` |

## OptimizerResult — the final answer
`best_setting` (a CandidateSetting), `best_prediction` (a Prediction), `baseline_mp`, `improvement` (J/min saved vs baseline), `explanation` (plain-language text), or `no_solution` if nothing was safe.
