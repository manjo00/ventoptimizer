# Evidence Base — every clinical number, with a source

**Rule:** if a number is used in code or docs, it must appear here with a citation. `[M]` = Ahmed's manuscript (`reference/Manuscript_V3.pdf`). External refs use the manuscript's numbers where possible; new refs added in Phase 1 are marked `[N#]`.

---

## Why we minimize Mechanical Power (the whole premise)  `[M]`
- In 18,980 ventilated MIMIC-IV adults, each **+1 J/min** of time-weighted MP raised the **adjusted odds of 28-day death by ~9%** (OR 1.09, 95% CI 1.09–1.10). `[M]`
- Risk is **graded, not threshold** — 28-day survival fell stepwise across MP quartiles (~89% → 86% → 83% → **70%**), and **every quartile boundary sat below 17 J/min**, so harm accrues even in the "acceptable" range. `[M]`
- Held across oxygenation, lung size, and age (ORs 1.08–1.10). `[M]`
- **Implication:** no safe MP floor to "aim for" — lower is better all the way down, subject to safety limits. Objective = *minimize MP*, not *get under 17*.

## The Mechanical Power equation  `[E1] = ref 6` · validated `[E2] = ref 7` · surrogate `[N8]`
Two forms exist and we use both, for different jobs (**decision 2026-09-28** — this resolves the docs-vs-code mismatch):
```
(a) Gattinoni simplified (needs a plateau):  MP  (J/min) = 0.098 × RR × VT(L) × [ Ppeak − ½(Pplat − PEEP) ]
                                             = 0.098 × RR × VT(L) × [ PEEP + (Ppeak − Pplat) + ½ΔP ]   (static + resistive + tidal-elastic)
(b) peak-only surrogate (no plateau needed): MP_dyn (J/min) = 0.098 × RR × VT(L) × [ Ppeak − ½(Ppeak − PEEP) ]  = 0.098 × RR × VT(L) × ½(Ppeak + PEEP)
```
- **Rule:** the engine (`physiology.py`, `validate_mimic.py`, `app/`) computes **(a)** whenever a plateau is charted — it is the validated simplified equation and the only form that yields the **tidal-elastic term we optimize** (`MP_tidal = 0.098 × RR × VT × ½ΔP`). When no plateau exists it falls back to **(b)**. **(b) is always reported alongside** because it is the manuscript's metric (`[M]`: OR 1.09 per J/min, harm below 17 J/min) and the metric of the largest database studies `[N8]`; the two must be labelled, never mixed in one comparison.
- `[E1]` Gattinoni L, et al. Ventilator-related causes of lung injury: the mechanical power. Intensive Care Med 2016;42(10):1567–75.
- `[E2]` Chiumello D, et al. Bedside calculation of mechanical power… Crit Care 2020;24:417. (Validated the simplified forms; notes peak pressure adds a resistive component.)
- `[N8]` Serpa Neto A, et al. *Mechanical power of ventilation is associated with mortality in critically ill patients: an analysis of patients in two observational cohorts.* Intensive Care Med 2018;44:1914–22 — MIMIC-III + eICU (n = 8,207), peak-pressure form; OR per 5 J/min 1.06 / 1.10; risk rises consistently above **17 J/min**; harm persists even at low tidal volume. Q1. Strength: observational association.
- Cohort MP range 0.24–109.6 J/min, mean 13.45. `[M]`

## Lung-protective safety limits
- **Plateau ≤ 30 cmH₂O** and **VT 4–8 mL/kg PBW** — `[E3] = ref 3` Brower RG, et al. (ARDS Network). NEJM 2000;342:1301–8 (6 mL/kg, Pplat cap 30; mortality 39.8%→31.0%).
- **Driving pressure (Pplat − PEEP)** is the ventilator variable most tied to mortality — `[E4] = ref 4` Amato MBP, et al. NEJM 2015;372:747–55. **Decision:** keep MP as the primary objective; evaluate adding driving pressure as a co-monitor/limit in Track C (with data), not bolt it on blindly.
- **Reinforced `[N5]`:** Costa EL, et al. *Ventilatory variables and mechanical power in ARDS.* AJRCCM 2021;204:303–11 — driving pressure's mortality impact is ~**4× respiratory rate's**, and a driving-pressure + RR model ≈ full MP. Supports our low-VT/high-RR bias and makes driving pressure a strong explicit-target candidate. See `_Literature_Validation` T12.

## Recruitment-to-Inflation (R/I) index  `[N1]` — concept & 0.5 threshold now CITED
- `[N1]` Chen L, Del Sorbo L, Grieco DL, et al. *Potential for Lung Recruitment Estimated by the Recruitment-to-Inflation Ratio in ARDS. A Clinical Trial.* Am J Respir Crit Care Med 2020;201(2):178–187.
- The **R/I = 0.5 cut-off** (the cohort median) separates **low (≤0.5)** vs **high (>0.5)** recruitability. → our >0.5 "recruitable" rule is grounded.
- ⚠️ **Was an `[ASSUMPTION]`:** our compliance formula `C_new = C × (1 + (R/I−0.5)×0.1×ΔPEEP)`. The `×0.1` was invented — Chen gives no PEEP→compliance equation.
- **DATA UPDATE (demo, 2026-06-20):** measured a population recruitment slope **β ≈ 0.083 per cmH₂O** (compliance +40% when PEEP↑, −23% when PEEP↓); a `C×(1+β·ΔPEEP)` correction cut PEEP-change plateau error **28%** on held-out patients. So the `×0.1` magnitude is **data-supported (ballpark-correct)**, not arbitrary — confirm on full MIMIC-IV before changing production. See `_Research_Log`. **⚠ 2026-09-28 (step 1b, real plateaus only): that result was an artifact of carried plateaus — retracted. Honest demo estimate β = 0.026 /cmH₂O (bootstrap 95% −0.038 to +0.089), no held-out gain → the `×0.1` is an `[ASSUMPTION]`, not data-supported, and probably too large on average; the response is individual (IQR −30% to +35%). Full-MIMIC re-estimate pending (`_Research_Log` 2026-09-28 1b).**
- 🟥 **Boundary (ART trial, Cavalcanti JAMA 2017; Crit Care 2022 PMID 35918772):** a PEEP-induced compliance change is NOT a recruitment measure, and titrating PEEP to "best compliance" *increased* mortality. So our PEEP-aware compliance is for **plateau PREDICTION only** — it must never drive "raise PEEP for better compliance." See `_Literature_Validation.md` T7.

## Lung compliance is NONLINEAR (the model's biggest weakness)  `[N2]`
- The ARDS pressure–volume curve has **three segments** with a **lower** and an **upper inflection point**; compliance changes with pressure/recruitment — it is **not a single constant**. `[N2]` Hickling KG. *The pressure–volume curve is greatly modified by recruitment. A mathematical model of ARDS lungs.* Am J Respir Crit Care Med 1998;158(1):194–202 (plus the inflection-point P–V literature).
- **Consequence:** our fixed (linear) compliance can mis-predict plateau pressure — most at high/low PEEP. This is **Research Agenda Q1** and the prime Track-C fix (build each patient's own P–V curve).

## Dead space ≈ 2.2 mL/kg — used, but weakly validated  `[N3]`
- Origin: `[N3a]` Radford EP. *Ventilation standards for use in artificial respiration.* J Appl Physiol 1955 — anatomic dead space ≈ **1 mL/lb = 2.2 mL/kg**.
- ⚠️ Caution: `[N3b]` *Anatomic Dead Space Cannot Be Predicted by Body Weight* (Respir Care 2021) found the weight estimate barely correlates with measured dead space (r² ≈ 0.0002; mean error 60 ± 54 mL). So 2.2 mL/kg is a **rough convention**, a real accuracy weakness, and a Track-C candidate (better estimate, or measure it).
- 🟥 **Bigger problem `[N4]`:** the 2.2 mL/kg *anatomic* rule (Vd/Vt ≈ 0.36) badly underestimates *physiological* dead space, which in ARDS is **0.5–0.7** and independently predicts mortality (Vd/Vt 0.54 survivors vs 0.63 non-survivors) — `[N4]` Nuckton TJ, et al. *Pulmonary dead-space fraction as a risk factor for death in ARDS.* NEJM 2002;346:1281–6. → our CO₂/pH predictions are biased in sick lungs; fix with a physiological estimate (ventilatory ratio). See `_Literature_Validation` T9.
- **BUILT + TESTED (2026-06-20):** added a Harris–Benedict physiological dead space (+ manual measured override) in `physiology.py`. On the demo it **worsened** CO₂ prediction (MAE 14.4→33.6 mmHg) — so HB is **opt-in only**; the anatomic rule stays the default and a **measured value (manual) always wins**. See `_Research_Log`. A *more accurate dead space ≠ a better CO₂ prediction*.

## Gas-exchange pH & permissive hypercapnia  `[E6]`
- Henderson–Hasselbalch (pH = 6.1 + log10(HCO₃ / (0.03 × PaCO₂))) is standard physiology.
- **pH floors 7.30 / 7.20:** the widely accepted lowest acceptable pH in permissive hypercapnia is **~7.20** (acknowledged as somewhat arbitrary; no proven hard limit). ARDSNet `[E3]` raised RR / gave bicarbonate when pH < 7.30, tolerating ~7.15–7.30. → our floors are pragmatic, ARDSNet-aligned conventions, not hard physiologic lines.

## Auto-PEEP / time constants  `[E5]`
- A lung empties exponentially; **3 time constants ≈ 95% emptying** (math: 1 − e⁻³ = 0.95). τ = Resistance × Compliance. Standard respiratory mechanics. The "1 s inspiration" inside `Te = 60/RR − 1` is an `[ASSUMPTION]` (typical, not patient-specific).

## Oxygenation substitution (for validation)  `[E7] = ref 21`
- SpO₂/FiO₂ is a validated stand-in for PaO₂/FiO₂ when no arterial gas is available — Pandharipande PP, et al. CCM 2009;37:1317–21.

## PEEP-response predictors & the PEEP/FiO₂ tables  `[N6]` `[N7]` (added 2026-09-28 for the required-variable list)
- `[N6]` Gattinoni L, et al. *Lung recruitment in patients with the acute respiratory distress syndrome.* NEJM 2006;354:1775–86. The recruitable lung fraction varied widely between patients (mean ≈13%) and **predicted the response to PEEP** (oxygenation, dead space, compliance). Used here only to justify **which recorded variables are candidate recruitability inputs** (baseline oxygenation, PaCO₂/dead space, compliance); no threshold taken from it. `[ASSUMPTION until re-checked in the Phase-1 literature pass: that the sicker-baseline ↔ more-recruitable direction holds outside CT-defined ARDS]`
- `[N7]` Brower RG, et al. (ALVEOLI). *Higher versus lower PEEP in patients with ARDS.* NEJM 2004;351:327–36 — the empirical **higher-PEEP/FiO₂ table** (vs the ARDSNet 2000 lower-PEEP table `[E3]`); no mortality difference between tables. Role for us: the two tables bound the *conventional* PEEP range for a given FiO₂ — a sanity envelope, **not** a target. **Table values (encoded in `engine/safe_peep.py`):** lower table FiO₂ 0.3→5 · 0.4→5–8 · 0.5→8–10 · 0.6→10 · 0.7→10–14 · 0.8→14 · 0.9→14–18 · 1.0→18–24; higher table 0.3→5–14 · 0.4→14–16 · 0.5→16–20 · 0.6–0.7→20 · 0.8→20–22 · 0.9→22 · 1.0→22–24. Goal in both: PaO₂ 55–80 mmHg or SpO₂ 88–95%.
- **Hemodynamic guard for PEEP steps:** PEEP lowers venous return / raises right-ventricular afterload (standard physiology). Numeric guard now cited: `[N11]` below.

## Highest-safe-PEEP ceilings, floors and gates  `[N9]` `[N10]` `[N11]` (sub-problem 1, 2026-09-28 — encoded in `engine/safe_peep.py`)
- **Plateau ≤ 30 cmH₂O** `[E3]`; **airway driving pressure ≤ 15 cmH₂O** and **transpulmonary driving pressure ≤ 11.7 cmH₂O** — `[N9]` Chiumello D, et al. *Airway driving pressure and lung stress in ARDS patients.* Crit Care 2016;20:276 (150 sedated, paralysed ARDS patients at PEEP 5 and 15; ΔP > 15 and ΔP_L > 11.7 at PEEP 15 correlated with critical lung stress; ΔP tracks lung stress, chest-wall elastance can blur it). Q1. Strength: physiological cohort. The mortality weight of ΔP: `[E4]` Amato 2015 (RR 1.41 per ~7 cmH₂O; no hard threshold given there).
- **Elastance-ratio estimate** ΔP_L ≈ ΔP × E_L/E_RS with E_L/E_RS ≈ **0.70** `[ASSUMPTION — population average; in Chiumello's cohort the implied ratio was ≈ 0.78 (11.7/15)]`. With 0.70, the ΔP ≤ 15 rule already implies ΔP_L ≤ 10.5, so the transpulmonary check only bites when a **measured** ΔP_L (esophageal balloon; MIMIC codes 224746/224747) is supplied.
- **Raised intracranial pressure:** treat ICP **> 22 mmHg** — `[N10]` Carney N, et al. *Guidelines for the Management of Severe Traumatic Brain Injury, 4th ed.* (Brain Trauma Foundation) Neurosurgery 2017;80:6–15 (level II B). Our gate: no PEEP increase above 22; caution whenever ICP is monitored.
- **Mean arterial pressure floor:** initial target **MAP ≥ 65 mmHg** — `[N11]` Evans L, et al. *Surviving Sepsis Campaign: International Guidelines 2021.* Crit Care Med 2021;49:e1063–e1143 (moderate-quality evidence). Our gate: no PEEP increase while MAP < 65; caution while a vasopressor runs.
- **Oxygenation goal** SpO₂ 88–95% / PaO₂ 55–80 mmHg `[E3]` — used as *status*, never as a reason to override a ceiling.
- **Cautious worst-case margin:** when projecting the plateau at a higher PEEP without a prediction model, compliance is assumed to be able to **fall 5% per cmH₂O of PEEP increase (capped at 50%)** — `[ASSUMPTION — from our own demo (step 1b): lower-quartile response ≈ −7% for a 3-cmH₂O step, worst cases ≈ −30%; to be replaced by the full-MIMIC H5 result]`.
- **Chest tube present → caution (air leak)** `[ASSUMPTION — clinical convention]`; **auto-PEEP ≥ 1 cmH₂O measured → caution** (3τ rule `[E5]`); **spontaneous breaths or support mode → mechanics invalid** (standard: plateau needs a passive patient).

## Data source for validation  `[M]`
- MIMIC-IV (v3.1) via the PhysioNet "Temporal Dataset for Respiratory Support" (v1.1.0). Credentialed; **local-only handling** (see `_Data_Access.md` + CLAUDE.md governance).

---
### Legend
`[M]` manuscript · `[E#]` external ref (manuscript numbering) · `[N#]` new Phase-1 ref · `[ASSUMPTION]` our guess, flagged · resolved tags moved from `[TO-RESEARCH]` → cited above.
