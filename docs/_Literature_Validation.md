# Literature Validation — does the evidence prove our theories?

**Principle:** every theory and modeling decision must be backed by published papers,
and we label **how strong** that proof is. Strongest = randomized controlled trial (RCT);
then large observational; then our own demo data (indicative, not proof).

**Strength legend:** 🟩 RCT-proven · 🟦 strong observational · 🟨 supported/plausible · 🟧 our demo only · 🟥 contested / can harm

---

## The claims register

### T1 — "Higher mechanical power → worse survival, so minimize it" (our north star)
- **Evidence:** multiple large cohorts — Serpa Neto 2018 (MIMIC-III + eICU; OR ≈1.06 per 5 J/min), Urner 2020 (Lancet Respir Med), Azizi 2023, several MIMIC-IV analyses, **and the team's own manuscript `[M]`** (ICM draft Sep 2026: OR 1.52 per IQR 8.2 → 13.6 J/min, ≈ +8 % per J/min at the median; E-value 1.77 — the authors themselves say causal language is not warranted). A 2023 systematic review/meta-analysis, and Sato 2026 (Crit Care Med): lower MP → better survival.
- **🟥 Caveat:** **No completed RCT proves that *lowering* MP saves lives.** Recent MP-guided trials are small / mixed / non-significant. The link is a strong *association* + plausible mechanism — not a proven intervention.
- **Verdict:** 🟦 strong observational association. **The tool reflects best current evidence, not proven therapy.**

### T2 — "Risk is graded; no safe MP threshold (harm accrues even < 17 J/min)"
- **Evidence:** the team's manuscript `[M]` now tests this *formally*: restricted-cubic-spline dose–response (nonlinear p = 0.014, rising across the whole range, no plateau) and segmented regression with the Davies test (**no supported breakpoint**, p = 0.14); 75 % of the cohort sat at or below 13.6 J/min and risk rose through that range. Other studies cite a ~17–18 J/min danger zone (Serpa Neto `[N8]`, Manrique 2024); `[M]` reads those as points on a continuous curve. **Nuance `[M]`:** no *population* breakpoint ≠ no *individual* threshold (a porcine model shows a sharp structural limit at a mechanical-power ratio > 4.5); heterogeneity smooths individual limits into a graded curve — which fits our own "the response is individual" findings.
- **Verdict:** 🟦 supported, now with a formal threshold test; we sit at the "lower is better all the way down" end — defensible. *(The earlier quartile-survival evidence 89 → 70 % `[M-v3]` is superseded.)*

### T3 — "The Gattinoni mechanical-power equation is a valid measure"
- Gattinoni 2016 (concept); Chiumello 2020 (validated vs the gold-standard pressure–volume method).
- **Verdict:** 🟦 validated.

### T4 — "Cap tidal volume (~6 mL/kg) and plateau pressure (≤30) to protect the lung"
- ARDSNet / Brower 2000 — **RCT**, mortality 39.8% → 31.0%.
- **Verdict:** 🟩 RCT-proven. Our hard safety limits rest on this.

### T5 — "Driving pressure is a central injury driver"
- Amato 2015 — individual-patient meta-analysis of 9 RCTs.
- **Verdict:** 🟦 strong → candidate co-target/limit for the optimizer.

### T6 — "Lung compliance is nonlinear, not a constant"
- Hickling 1998; pressure–volume inflection-point literature; **our demo** (compliance varies ~19% within a patient).
- **Verdict:** 🟦 supported + 🟧 our demo agrees.

### T7 — "Compliance shifts when PEEP changes (recruitment) — so account for it"  ⚠️ READ THE CAVEAT
- **For PREDICTION (our use):** compliance does move with PEEP; correcting for it cut our plateau-prediction error **28%** on held-out demo patients. **⚠ 2026-09-28 (step 1b): that 28% was an artifact of carried plateaus — retracted. On real measurements the population correction gives NO gain (leave-one-stay-out MAE 3.57 → 3.73; β 0.026, interval includes 0). Compliance does still move with PEEP, but individually (same-direction IQR −30% to +35%). Verdict for a *population* rule: 🟥 not supported by our data; the direction claim stays literature-based, and the per-patient response is the real problem.** Direction matches the literature (e.g., COVID-ARDS compliance rose ~10% from PEEP 5→15).
- **🟥 Critical caveat:** a PEEP-induced compliance change is **NOT a reliable measure of recruitment** and can mislead (Coppola/Chiumello group, Crit Care 2022, PMID 35918772 — changes "reflect almost exclusively lung over-inflation, not alveolar recruitment"). **Titrating PEEP to "best compliance" INCREASED mortality** in the **ART trial** (Cavalcanti, JAMA 2017: 28-day 55.3% vs 49.3% with low PEEP).
- **Verdict:** 🟧 our correction is valid **only as a prediction/accuracy tool**. It must **not** be read as recruitment, and the optimizer must **not** push PEEP up to chase compliance — that contradicts RCT evidence.

---

### T8 — "CO₂ rises/falls inversely with alveolar ventilation" (our pH/CO₂ prediction)
- Standard physiology: PaCO₂ = VCO₂ × 0.863 / V̇A, with V̇A = (VT − dead space) × RR. Our inverse-proportion prediction is exactly this.
- **Caveat:** assumes **constant CO₂ production** (VCO₂) and **steady state** (CO₂ takes time to re-equilibrate after a change).
- **Verdict:** 🟦 standard physiology (valid), with the constant-VCO₂ + steady-state caveats.

### T9 — "Dead space ≈ 2.2 mL/kg"  ⚠️ WEAK — biggest gas-side flaw
- Real **physiological** dead space in ARDS is high and predicts mortality: Vd/Vt **0.54 (survivors) vs 0.63 (non-survivors)**, risk ↑ per 0.05 increment (Nuckton, **NEJM 2002**); ARDS Vd/Vt is typically 0.5–0.7.
- Our **anatomic** 2.2 mL/kg gives Vd/Vt ≈ 0.36 — it badly **under-estimates** dead space in sick lungs (it ignores alveolar dead space from poor perfusion). → CO₂/pH predictions are systematically biased.
- **Verdict:** 🟥 weak — replace with a **physiological** dead-space estimate (e.g., the ventilatory ratio) or a measured value. (Dead space is itself prognostic.)

### T10 — "Permissive hypercapnia is OK down to pH ~7.20"
- Reasonable convention (ARDSNet), **but real contraindications**: raised intracranial pressure / brain injury (CO₂ → cerebral vasodilation → ↑ICP), cerebral edema, depressed cardiac function, arrhythmias, raised pulmonary vascular resistance.
- **Verdict:** 🟦 the floor is fine, but **permissive mode must be gated** — not for brain-injured / raised-ICP patients. → design-safety note below.

### T11 — "Expiratory time ≥ 3 time constants avoids air-trapping"
- 3τ ≈ 95% emptying is classic teaching; recent data show it's **conservative** (~2.2τ already gives 95%). High RR → auto-PEEP / dynamic hyperinflation.
- **Verdict:** 🟦 our rule is standard and conservative (safe; may slightly over-reject high-RR settings). The "1 s inspiration" in `Te = 60/RR − 1` is a simplification.

### T12 — "Favor low tidal volume, high rate" (the optimizer's bias)
- MP weights VT quadratically, RR linearly. Costa 2021 (AJRCCM): **driving pressure's mortality impact is ~4× respiratory rate's**; the elastic-dynamic (driving-pressure) component dominates, and a simple driving-pressure + RR model ≈ full MP.
- **Verdict (original):** 🟦 supported — cutting VT / driving pressure is the highest-value move; trading VT↓ for RR↑ reduces the dominant harm (RR isn't free, but smaller + auto-PEEP risk). → strongly consider making **driving pressure an explicit optimizer target** (with T5/Amato).
- **⚠ Counterweight (2026-10-01, `[M]`):** in the team's own cohort, with the peak-only surrogate (no plateau), **rate carried 87 %** of the components' mortality signal (OR per SD 1.71), peak pressure 13 %, **tidal volume 0 %** (0.99) — and at equal high power, small-breath/high-rate configurations carried *higher* odds (2.03 vs 1.35). The manuscript reconciles the two: Costa answers "which component injures when full mechanics are known" (ΔP), `[M]` answers "which routine variable carries the signal when they are not" (rate). Its clinical reading: **don't cut VT and raise rate just to lower the number**; treat a high rate as a signal to find its cause; where rate is controlled, lower the rate rather than raise VT.
- **Verdict (revised):** 🟦 the *driving-pressure* half stands (Amato, Costa — plateau-based); 🟨 the *"rate is cheap"* half is **contested by our own data** → the VT↔RR trade must not be presented as harm reduction until the objective is decided (`_Research_Agenda` Q6). Mitigations already in the engine: the 3τ air-trapping gate, the pH floor, the RR deviation penalty, and the demo finding that the savable VT↔RR power ≈ 0.

## ⚠️ Two honesty pillars (carry these into every claim and every output)
1. **Association ≠ intervention.** Minimizing MP is strongly *associated* with survival but not RCT-*proven* to cause it. Frame the tool as evidence-based decision support, **not** proven treatment.
2. **Prediction ≠ titration.** Our PEEP-aware compliance makes *predictions* accurate. It is **not** a recruitment measure and must never justify "raise PEEP for better compliance" — ART showed that harms. The objective stays: **minimize MP within the ARDSNet-proven limits.**

## 🚩 Design-safety flag (for the optimizer)
The prototype's recruitment logic ("recruitable → raising PEEP improves compliance → lowers MP → favor it") could recommend higher PEEP. Given ART, the optimizer must be constrained so it does **not** recommend aggressive PEEP increases justified only by modeled compliance gains. Revisit in Phase 2/3. (Logged in `_Current_Task` Noticed.)
- **Permissive-hypercapnia gate (T10):** the "Permissive CO₂" mode must not apply to patients with raised intracranial pressure / brain injury — hypercapnia raises ICP. The optimizer needs a contraindication flag before this mode lowers the pH floor.

---
*Built 2026-06-20 from a focused literature pass. Full source links in the commit message + `_Research_Log.md`.*
