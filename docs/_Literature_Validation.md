# Literature Validation — does the evidence prove our theories?

**Principle:** every theory and modeling decision must be backed by published papers,
and we label **how strong** that proof is. Strongest = randomized controlled trial (RCT);
then large observational; then our own demo data (indicative, not proof).

**Strength legend:** 🟩 RCT-proven · 🟦 strong observational · 🟨 supported/plausible · 🟧 our demo only · 🟥 contested / can harm

---

## The claims register

### T1 — "Higher mechanical power → worse survival, so minimize it" (our north star)
- **Evidence:** multiple large cohorts — Serpa Neto 2018 (MIMIC-III + eICU; OR ≈1.06 per 5 J/min), Urner 2020 (Lancet Respir Med), Azizi 2023, several MIMIC-IV analyses, **and Ahmed's own manuscript** (+9% odds of death per J/min). A 2023 systematic review/meta-analysis: lower MP → better survival.
- **🟥 Caveat:** **No completed RCT proves that *lowering* MP saves lives.** Recent MP-guided trials are small / mixed / non-significant. The link is a strong *association* + plausible mechanism — not a proven intervention.
- **Verdict:** 🟦 strong observational association. **The tool reflects best current evidence, not proven therapy.**

### T2 — "Risk is graded; no safe MP threshold (harm accrues even < 17 J/min)"
- **Evidence:** Ahmed's manuscript (graded quartiles, harm below 17). Other studies cite a ~17–18 J/min danger zone.
- **Verdict:** 🟦 supported; we sit at the "lower is better all the way down" end — defensible, a step ahead of the fixed-threshold camp.

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
- **For PREDICTION (our use):** compliance does move with PEEP; correcting for it cut our plateau-prediction error **28%** on held-out demo patients. Direction matches the literature (e.g., COVID-ARDS compliance rose ~10% from PEEP 5→15).
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
- **Verdict:** 🟦 supported — cutting VT / driving pressure is the highest-value move; trading VT↓ for RR↑ reduces the dominant harm (RR isn't free, but smaller + auto-PEEP risk). → strongly consider making **driving pressure an explicit optimizer target** (with T5/Amato).

## ⚠️ Two honesty pillars (carry these into every claim and every output)
1. **Association ≠ intervention.** Minimizing MP is strongly *associated* with survival but not RCT-*proven* to cause it. Frame the tool as evidence-based decision support, **not** proven treatment.
2. **Prediction ≠ titration.** Our PEEP-aware compliance makes *predictions* accurate. It is **not** a recruitment measure and must never justify "raise PEEP for better compliance" — ART showed that harms. The objective stays: **minimize MP within the ARDSNet-proven limits.**

## 🚩 Design-safety flag (for the optimizer)
The prototype's recruitment logic ("recruitable → raising PEEP improves compliance → lowers MP → favor it") could recommend higher PEEP. Given ART, the optimizer must be constrained so it does **not** recommend aggressive PEEP increases justified only by modeled compliance gains. Revisit in Phase 2/3. (Logged in `_Current_Task` Noticed.)
- **Permissive-hypercapnia gate (T10):** the "Permissive CO₂" mode must not apply to patients with raised intracranial pressure / brain injury — hypercapnia raises ICP. The optimizer needs a contraindication flag before this mode lowers the pH floor.

---
*Built 2026-06-20 from a focused literature pass. Full source links in the commit message + `_Research_Log.md`.*
