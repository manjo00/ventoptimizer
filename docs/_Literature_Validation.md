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

## ⚠️ Two honesty pillars (carry these into every claim and every output)
1. **Association ≠ intervention.** Minimizing MP is strongly *associated* with survival but not RCT-*proven* to cause it. Frame the tool as evidence-based decision support, **not** proven treatment.
2. **Prediction ≠ titration.** Our PEEP-aware compliance makes *predictions* accurate. It is **not** a recruitment measure and must never justify "raise PEEP for better compliance" — ART showed that harms. The objective stays: **minimize MP within the ARDSNet-proven limits.**

## 🚩 Design-safety flag (for the optimizer)
The prototype's recruitment logic ("recruitable → raising PEEP improves compliance → lowers MP → favor it") could recommend higher PEEP. Given ART, the optimizer must be constrained so it does **not** recommend aggressive PEEP increases justified only by modeled compliance gains. Revisit in Phase 2/3. (Logged in `_Current_Task` Noticed.)

---
*Built 2026-06-20 from a focused literature pass. Full source links in the commit message + `_Research_Log.md`.*
