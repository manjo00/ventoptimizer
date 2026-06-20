# Evidence Base — every clinical number, with a source

**Rule:** if a number is used in code or docs, it must appear here with a citation. `[M]` = Ahmed's manuscript (`reference/Manuscript_V3.pdf`). External refs use the manuscript's numbers where possible; new refs added in Phase 1 are marked `[N#]`.

---

## Why we minimize Mechanical Power (the whole premise)  `[M]`
- In 18,980 ventilated MIMIC-IV adults, each **+1 J/min** of time-weighted MP raised the **adjusted odds of 28-day death by ~9%** (OR 1.09, 95% CI 1.09–1.10). `[M]`
- Risk is **graded, not threshold** — 28-day survival fell stepwise across MP quartiles (~89% → 86% → 83% → **70%**), and **every quartile boundary sat below 17 J/min**, so harm accrues even in the "acceptable" range. `[M]`
- Held across oxygenation, lung size, and age (ORs 1.08–1.10). `[M]`
- **Implication:** no safe MP floor to "aim for" — lower is better all the way down, subject to safety limits. Objective = *minimize MP*, not *get under 17*.

## The Mechanical Power equation  `[E1] = ref 6` · validated `[E2] = ref 7`
```
MP (J/min) = 0.098 × RR × VT(L) × [ Ppeak − ½(Ppeak − PEEP) ]
```
- `[E1]` Gattinoni L, et al. Ventilator-related causes of lung injury: the mechanical power. Intensive Care Med 2016;42(10):1567–75.
- `[E2]` Chiumello D, et al. Bedside calculation of mechanical power… Crit Care 2020;24:417. (Validated this surrogate; notes peak pressure adds a resistive component.)
- Cohort MP range 0.24–109.6 J/min, mean 13.45. `[M]`

## Lung-protective safety limits
- **Plateau ≤ 30 cmH₂O** and **VT 4–8 mL/kg PBW** — `[E3] = ref 3` Brower RG, et al. (ARDS Network). NEJM 2000;342:1301–8 (6 mL/kg, Pplat cap 30; mortality 39.8%→31.0%).
- **Driving pressure (Pplat − PEEP)** is the ventilator variable most tied to mortality — `[E4] = ref 4` Amato MBP, et al. NEJM 2015;372:747–55. **Decision:** keep MP as the primary objective; evaluate adding driving pressure as a co-monitor/limit in Track C (with data), not bolt it on blindly.

## Recruitment-to-Inflation (R/I) index  `[N1]` — concept & 0.5 threshold now CITED
- `[N1]` Chen L, Del Sorbo L, Grieco DL, et al. *Potential for Lung Recruitment Estimated by the Recruitment-to-Inflation Ratio in ARDS. A Clinical Trial.* Am J Respir Crit Care Med 2020;201(2):178–187.
- The **R/I = 0.5 cut-off** (the cohort median) separates **low (≤0.5)** vs **high (>0.5)** recruitability. → our >0.5 "recruitable" rule is grounded.
- ⚠️ **Was an `[ASSUMPTION]`:** our compliance formula `C_new = C × (1 + (R/I−0.5)×0.1×ΔPEEP)`. The `×0.1` was invented — Chen gives no PEEP→compliance equation.
- **DATA UPDATE (demo, 2026-06-20):** measured a population recruitment slope **β ≈ 0.083 per cmH₂O** (compliance +40% when PEEP↑, −23% when PEEP↓); a `C×(1+β·ΔPEEP)` correction cut PEEP-change plateau error **28%** on held-out patients. So the `×0.1` magnitude is **data-supported (ballpark-correct)**, not arbitrary — confirm on full MIMIC-IV before changing production. See `_Research_Log`.

## Lung compliance is NONLINEAR (the model's biggest weakness)  `[N2]`
- The ARDS pressure–volume curve has **three segments** with a **lower** and an **upper inflection point**; compliance changes with pressure/recruitment — it is **not a single constant**. `[N2]` Hickling KG. *The pressure–volume curve is greatly modified by recruitment. A mathematical model of ARDS lungs.* Am J Respir Crit Care Med 1998;158(1):194–202 (plus the inflection-point P–V literature).
- **Consequence:** our fixed (linear) compliance can mis-predict plateau pressure — most at high/low PEEP. This is **Research Agenda Q1** and the prime Track-C fix (build each patient's own P–V curve).

## Dead space ≈ 2.2 mL/kg — used, but weakly validated  `[N3]`
- Origin: `[N3a]` Radford EP. *Ventilation standards for use in artificial respiration.* J Appl Physiol 1955 — anatomic dead space ≈ **1 mL/lb = 2.2 mL/kg**.
- ⚠️ Caution: `[N3b]` *Anatomic Dead Space Cannot Be Predicted by Body Weight* (Respir Care 2021) found the weight estimate barely correlates with measured dead space (r² ≈ 0.0002; mean error 60 ± 54 mL). So 2.2 mL/kg is a **rough convention**, a real accuracy weakness, and a Track-C candidate (better estimate, or measure it).

## Gas-exchange pH & permissive hypercapnia  `[E6]`
- Henderson–Hasselbalch (pH = 6.1 + log10(HCO₃ / (0.03 × PaCO₂))) is standard physiology.
- **pH floors 7.30 / 7.20:** the widely accepted lowest acceptable pH in permissive hypercapnia is **~7.20** (acknowledged as somewhat arbitrary; no proven hard limit). ARDSNet `[E3]` raised RR / gave bicarbonate when pH < 7.30, tolerating ~7.15–7.30. → our floors are pragmatic, ARDSNet-aligned conventions, not hard physiologic lines.

## Auto-PEEP / time constants  `[E5]`
- A lung empties exponentially; **3 time constants ≈ 95% emptying** (math: 1 − e⁻³ = 0.95). τ = Resistance × Compliance. Standard respiratory mechanics. The "1 s inspiration" inside `Te = 60/RR − 1` is an `[ASSUMPTION]` (typical, not patient-specific).

## Oxygenation substitution (for validation)  `[E7] = ref 21`
- SpO₂/FiO₂ is a validated stand-in for PaO₂/FiO₂ when no arterial gas is available — Pandharipande PP, et al. CCM 2009;37:1317–21.

## Data source for validation  `[M]`
- MIMIC-IV (v3.1) via the PhysioNet "Temporal Dataset for Respiratory Support" (v1.1.0). Credentialed; **local-only handling** (see `_Data_Access.md` + CLAUDE.md governance).

---
### Legend
`[M]` manuscript · `[E#]` external ref (manuscript numbering) · `[N#]` new Phase-1 ref · `[ASSUMPTION]` our guess, flagged · resolved tags moved from `[TO-RESEARCH]` → cited above.
