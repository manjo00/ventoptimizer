# Evidence Base — every clinical number, with a source

**Rule:** if a number is used in code or docs, it must appear here with a citation. `[M]` = Ahmed's manuscript (`reference/Manuscript_V3.pdf`). External refs use the manuscript's reference numbers where possible.

---

## Why we minimize Mechanical Power (the whole premise)  `[M]`
- In 18,980 ventilated MIMIC-IV adults, each **+1 J/min** of time-weighted MP raised the **adjusted odds of 28-day death by ~9%** (OR 1.09, 95% CI 1.09–1.10; p<.001). `[M]`
- Risk is **graded, not threshold** — 28-day survival fell stepwise across MP quartiles (~89% → 86% → 83% → **70%**), and **every quartile boundary sat below 17 J/min**, so harm accrues even in the "acceptable" range. `[M]`
- Held across oxygenation, lung size, and age (no subgroup spared; ORs 1.08–1.10). `[M]`
- **Implication for the optimizer:** there is no safe MP floor to "aim for" — lower is better all the way down, subject to safety limits. So the objective is *minimize MP*, not *get under 17*.

## The Mechanical Power equation  `[E1] = ref 6` · validated `[E2] = ref 7`
```
MP (J/min) = 0.098 × RR × VT(L) × [ Ppeak − ½(Ppeak − PEEP) ]
```
- `[E1]` Gattinoni L, et al. *Ventilator-related causes of lung injury: the mechanical power.* Intensive Care Med 2016;42(10):1567–75.
- `[E2]` Chiumello D, et al. *Bedside calculation of mechanical power…* Crit Care 2020;24:417 — validated this surrogate vs the gold-standard pressure–volume method; also notes peak-pressure adds a resistive component.
- Observed range in the manuscript cohort: 0.24–109.6 J/min, mean 13.45. `[M]`

## Lung-protective safety limits
- **Plateau pressure ≤ 30 cmH₂O** and **tidal volume 4–8 mL/kg PBW** — `[E_ARDSNet] = ref 3` Brower RG, et al. (ARDS Network). *Lower tidal volumes…* NEJM 2000;342:1301–8. (6 mL/kg, Pplat cap 30; cut mortality 39.8%→31.0%.)
- **Driving pressure (Pplat − PEEP)** is the single ventilator variable most tied to mortality — `[E_Amato] = ref 4` Amato MBP, et al. *Driving pressure and survival in ARDS.* NEJM 2015;372:747–55. → strong candidate to add to the optimizer's objective (Phase 1).

## Recruitment-to-Inflation index  `[E4]`
- Concept is published (R/I ratio distinguishes recruitable vs non-recruitable lungs). **The `0.1 × ΔPEEP` compliance formula in our code is NOT from any paper — it is an `[ASSUMPTION]`** and a Phase 1 research target.
- `[TO-RESEARCH: add primary R/I citation — e.g., Chen et al., recruitment-to-inflation ratio]`

## Auto-PEEP / time constants  `[E5]`
- "~3 time constants ≈ 95% lung emptying" is standard respiratory mechanics. `[TO-RESEARCH: cite a physiology text/review for the file.]`

## Gas exchange / pH  `[E6]`
- Henderson–Hasselbalch (pH = 6.1 + log10(HCO₃ / (0.03 × PaCO₂))) is standard.
- Dead space ≈ 2.2 mL/kg PBW is a rough rule `[ASSUMPTION]`.
- Permissive-hypercapnia pH floors (7.30 / 7.20): `[TO-RESEARCH: cite — ARDSNet protocol allowed pH 7.30–7.45 with bicarbonate; document the permissive lower bound source.]`

## Oxygenation substitution (for validation work)  `[E7] = ref 21`
- SpO₂/FiO₂ is a validated stand-in for PaO₂/FiO₂ when no arterial gas is available — Pandharipande PP, et al. CCM 2009;37:1317–21. (Used in the manuscript; useful for MIMIC shadow testing.)

## Data source for validation  `[M]`
- MIMIC-IV (v3.1) via the PhysioNet "Temporal Dataset for Respiratory Support" (v1.1.0); hourly ventilator + ABG data; credentialed access already obtained for the manuscript. This is the natural dataset for Phase 1 shadow testing.

---
### Legend
`[M]` manuscript · `[E#]` external citation · `[ASSUMPTION]` our guess, no source · `[TO-RESEARCH]` citation still owed.
