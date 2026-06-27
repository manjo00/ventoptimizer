# Research Log — the lab notebook

Append-only, detailed record of every experiment and decision, so the model's
development is reproducible and the eventual write-up is ready. **Aggregate results
only — NEVER patient data** (see CLAUDE.md governance). Newest at the bottom.

### Entry template
```
## YYYY-MM-DD — <title>
**Question:** what are we testing?
**Method:** what we did (files, dataset, sample size — aggregate only).
**Result:** the aggregate numbers Ahmed pasted back.
**Decision:** what we concluded / changed next.
**Commit:** <hash or "Phase X — task">
```

---

## 2026-06-20 — Track A: literature pass on the model's assumptions
**Question:** Which of the model's clinical numbers are real/cited, and which are guesses that could make it inaccurate?
**Method:** Reviewed each formula in `_Clinical_Logic.md` against the literature (targeted web searches + the manuscript). Resolved every `[ASSUMPTION]`/`[TO-RESEARCH]` tag in `_Evidence_Base.md`.
**Result (findings):**
- ✅ **Mechanical Power equation** — cited & validated (Gattinoni 2016; Chiumello 2020).
- ✅ **Safety limits** (Pplat ≤ 30, VT 4–8 mL/kg) — ARDSNet (Brower 2000).
- ✅ **Recruitment threshold R/I > 0.5** — now cited (Chen 2020). ⚠️ but the `×0.1` PEEP→compliance multiplier is **invented** (no source) → replace in Track C.
- ⚠️ **Linear compliance = confirmed the model's biggest weakness.** The ARDS P–V curve is nonlinear (lower + upper inflection points; Hickling 1998). One fixed compliance can mis-predict plateau pressure. → **top Track-C fix** (per-patient P–V curve).
- ⚠️ **Dead space 2.2 mL/kg = weakly validated.** Origin Radford 1955, but measured dead space barely correlates with body weight (r² ≈ 0.0002; Respir Care 2021). → Track-C candidate (improve or measure).
- ✅ **pH floors 7.30 / 7.20** — pragmatic ARDSNet-aligned conventions; ~7.20 widely accepted (if arbitrary).
- ✅ **3τ ≈ 95% emptying** — standard math (1 − e⁻³ = 0.95).
**Decision:** Two priorities for Track C once we have data — (1) replace linear compliance with each patient's own P–V curve; (2) improve/measure dead space. Keep MP as the objective; evaluate driving pressure (Amato 2015) as a co-limit *with data*. Every formula now traces to a citation in `_Evidence_Base.md`.
**Commit:** Phase 1 — Track A literature pass

## 2026-06-20 — Scouting lower-friction validation datasets
**Question:** Is there a more open / lower-friction dataset than full MIMIC-IV (credentialed, unshareable with Claude)?
**Method:** Web search of public ICU/ventilation datasets and their access models.
**Result:**
- **MIMIC-IV demo** (100 patients) = fully open (ODbL), downloadable now, likely shareable → ideal for BUILDING/testing the harness immediately.
- Richer respiratory DBs (AmsterdamUMCdb 23k; HiRID; eICU) all need equal-or-greater credentialing (Amsterdam even needs a reference intensivist) → **not** lower friction.
- VitalDB = open but OR/anaesthesia population (healthy lungs) → physics checks only.
- **No large, ARDS-rich, fully-open ventilator dataset exists.**
- Cross-dataset caveat: measured plateau pressure is rarely charted anywhere.
**Decision (pending Ahmed's pick):** build + smoke-test `validate_mimic.py` on the open MIMIC-IV demo now (no waiting on credentialing); run the real accuracy validation on full MIMIC-IV (already accessible) or AmsterdamUMCdb later.
**Commit:** Phase 1 — dataset scouting

## 2026-06-20 — First shadow test on the open MIMIC-IV demo (BASELINE accuracy)
**Question:** How accurate is the current model's physiology on real ventilated patients?
**Method:** Built `engine/validate_mimic.py` (aggregate-only); ran on the open MIMIC-IV demo. Cohort = ventilated snapshots with VT + PEEP + Pplat present = **8,480 snapshots, 56 patients**. Two experiments.
**Result (aggregate only):**
- **Exp 1 — compliance stability:** within-patient compliance varies a **median 19.2%** (mean 21.0%) over each patient's course → the constant/linear-compliance assumption is meaningfully wrong (confirms Research Agenda Q1).
- **Exp 2 — plateau prediction after a settings change** (1,056 paired changes): **MAE 3.05 cmH₂O**, bias +0.51, within 2 cmH₂O 51.8%, within 5 cmH₂O 83.9%.
**Decision:** Baseline established. Plateau MAE 3.05 is above our provisional ≤2 target, and the ~19% compliance drift is the likely cause. **Track C target #1 = replace constant compliance with a per-patient/updated compliance, then re-measure (goal: cut the MAE).** Demo numbers are indicative; Ahmed re-runs on full MIMIC-IV later.
**Commit:** Phase 1 — first demo shadow test

## 2026-06-20 — Track C attempt #1: robust compliance + diagnostic split
**Question:** Can a noise-robust compliance (median of recent readings) cut the plateau-prediction error below the 3.05 baseline? And where does the error actually come from?
**Method:** Added an "improved" predictor (median of last 5 compliance readings) alongside the baseline (single last reading); also split the baseline error by whether PEEP changed. Same demo cohort (1,056 setting-changes).
**Result (aggregate):**
- Robust compliance did **NOT** help: MAE **3.07** vs **3.05** baseline (−0.9%, marginally worse) → the error is **not random noise**.
- **Diagnostic split (the key finding):** VT-only changes (n=873) MAE **2.68**; PEEP changes (n=183) MAE **4.80** — nearly double.
**Decision:** Smoothing rejected. The error concentrates in PEEP changes → it's a **recruitment effect** (compliance measured at the old PEEP doesn't hold at the new PEEP). This is Research Agenda Q2. **Next: measure how compliance actually changes with PEEP from the data, then build a PEEP-aware (recruitment) compliance — not smoothing.**
**Commit:** Phase 1 — Track C attempt #1 (compliance)

## 2026-06-20 — Track C attempt #2: PEEP-aware (recruitment) compliance — ✅ WORKS
**Question:** Does a data-learned PEEP-aware compliance cut the PEEP-change error (baseline 4.8)?
**Method:** From the demo PEEP-change events (n=183) measured how compliance moves with PEEP. Then an HONEST train/test: learned a recruitment slope β on even-id patients, scored the corrected prediction `C×(1+β·ΔPEEP)` on held-out odd-id patients (73 events) — so the model never grades its own homework.
**Result (aggregate):**
- Recruitment is real & sizable: compliance **+40% median when PEEP goes UP**, **−23% when PEEP goes DOWN**.
- Learned slope **β = 0.083 per cmH₂O** — strikingly close to the prototype's *guessed* ×0.1 (original instinct was about right; now data-grounded, and works WITHOUT needing R/I).
- Held-out test: baseline MAE 4.48 → **PEEP-aware MAE 3.21 = 28.3% improvement.**
**Decision:** First validated model improvement. Caveat: small demo (73 test events) → **Ahmed confirms on full MIMIC-IV before we change the production model** (`physiology.py`) in Phase 2. Per-patient R/I could refine β further later.
**Commit:** Phase 1 — Track C #2 (PEEP-aware compliance) validated

## 2026-06-20 — Literature validation of our core theories
**Question:** Do published papers actually prove our theories — and how strongly?
**Method:** Focused literature pass on each core claim; built `_Literature_Validation.md` (a theory→proof register with a strength grade).
**Result:**
- **MP→mortality (north star):** strongly supported by many cohorts + a meta-analysis + our manuscript — BUT **no RCT proves lowering MP saves lives** (recent MP-guided trials mixed). → strong *association*, not proven intervention.
- **Safety limits (Pplat≤30, VT~6):** RCT-proven (ARDSNet 2000). Driving pressure: strong (Amato 2015). MP equation: validated (Chiumello 2020). Compliance nonlinearity: supported (Hickling 1998).
- **Recruitment (our finding):** ⚠️ literature corroborates compliance shifts with PEEP *in direction* (~10% in one study; our demo ~40%, likely case-mix/measurement-inflated), but **compliance change ≠ recruitment** (Crit Care 2022) and **compliance-titrated PEEP INCREASED mortality** (ART trial, JAMA 2017).
**Decision:** Two standing honesty rules added to CLAUDE.md — (1) association ≠ intervention; (2) our PEEP-aware compliance is for **prediction only**, never PEEP titration. Logged an optimizer design-safety flag (don't push PEEP up to chase compliance).
**Sources:** Serpa Neto 2018; Urner 2020; Azizi 2023; Gattinoni 2016; Chiumello 2020; Brower/ARDSNet 2000; Amato 2015; Hickling 1998; Chen 2020; Cavalcanti/ART JAMA 2017; Crit Care 2022 (PMID 35918772).
**Commit:** Phase 1 — literature validation

## 2026-06-20 — Literature validation, part 2: gas exchange + remaining theories ("to everything")
**Question:** Paper-proof the rest of the model — gas exchange, dead space, permissive hypercapnia, the auto-PEEP rule, and the low-VT/high-RR strategy.
**Method:** Targeted literature pass; added T8–T12 to `_Literature_Validation.md`.
**Result:**
- **T8 Gas exchange:** our inverse CO₂↔alveolar-ventilation rule = standard physiology ✅ (caveats: constant CO₂ production + steady state).
- **T9 Dead space 🟥:** the *anatomic* 2.2 mL/kg (Vd/Vt ≈ 0.36) badly underestimates *physiological* dead space (ARDS 0.5–0.7), which predicts mortality (Nuckton NEJM 2002). **Biggest gas-side flaw** → fix with ventilatory-ratio dead space.
- **T10 Permissive hypercapnia:** pH ~7.20 floor OK, BUT contraindicated in raised ICP / brain injury → needs a gate.
- **T11 Auto-PEEP rule:** 3τ ≈ 95% emptying is standard & conservative (recent data: ~2.2τ). Our rule is safe.
- **T12 Low-VT/high-RR strategy ✅:** Costa 2021 — driving pressure's mortality impact is ~4× RR's → our bias is supported; make driving pressure an explicit target.
**Decision:** Two new design-safety flags (permissive-mode ICP gate; recruitment/PEEP from part 1) + driving-pressure-as-target. Next gas-side experiment should test a physiological dead-space estimate. Every core theory now graded in `_Literature_Validation.md`.
**Sources:** alveolar-ventilation physiology; Nuckton NEJM 2002; permissive-hypercapnia reviews; expiratory-time-constant reviews; Costa AJRCCM 2021.
**Commit:** Phase 1 — literature validation part 2

## 2026-06-20 — Searching the literature for a dead-space SOLUTION
**Question:** How do we estimate *physiological* dead space at the bedside, with the data we have (no volumetric capnography)?
**Method:** Literature search for bedside dead-space estimators + checked the demo for EtCO₂.
**Result — three candidates:**
1. **Ventilatory Ratio (VR)** — needs only VT, RR, PaCO₂, PBW (all in MIMIC). Validated, mortality-predictive. Simplest.
2. **Harris–Benedict estimated VD/VT** (Beitler 2015) — unbiased vs measured (0.59 vs 0.60; ±0.10 in 70%), gives a directly-usable fraction; needs age/sex/weight/PaCO₂/MV (all available). Best accuracy.
3. **EtCO₂ AVDSf** = (PaCO₂−EtCO₂)/PaCO₂ — captures alveolar dead space + real-time (ABG-lag bonus), but EtCO₂ sparse in demo (202 vs 623 PaCO₂ rows). Add-on, not backbone.
**Decision:** recommend building **HB-estimated VD/VT as the backbone** (accuracy + usable fraction) with **VR as a simple cross-check**, then validate by CO₂/pH shadow test vs the anatomic-2.2-mL/kg baseline on held-out patients. EtCO₂/AVDSf later for real-time. Recorded as candidate fixes in `_Research_Agenda` Q3.
**Sources:** Sinha (ventilatory ratio); Beitler CCM 2015 (estimated VD/VT); Yang/Morales (EtCO₂ AVDSf).
**Commit:** Phase 1 — dead-space solution scouting

## 2026-06-20 — "Is there a more proven / more accurate way?" — accuracy hierarchy
**Question:** Is there a more accurate/proven dead-space method than the estimation equations?
**Method:** Literature check on gold-standard measurement + head-to-head accuracy of estimates.
**Result:**
- **Yes — the gold standard is direct measurement (volumetric capnography / Bohr).** It's far more accurate than any estimate, BUT it's not recorded in MIMIC → unavailable to us retrospectively. (The Enghoff/PaCO₂ version also conflates shunt.)
- **Among routine-data estimates the evidence is genuinely mixed** — no single equation is clearly "most proven" (HB unbiased in one study, not mortality-linked in another; VR better in some cohorts).
- **Key reframe:** the accuracy limit is the *data*, not the equation. On routine retrospective data we're capped at estimates.
- ★ **Best feasible route for our prediction goal: learn each patient's *effective* dead space from their own CO₂ data** (like the PEEP-aware compliance), which should beat population equations for prediction.
**Decision:** Don't pick one estimate on faith — run a 3-way head-to-head on our data (fixed 2.2 vs HB vs per-patient-learned). For true gold-standard accuracy, flag that a volumetric-capnography dataset would be needed (Phase 2+ / prospective).
**Sources:** Vcap dead-space validation (Intensive Care Med 2011); estimated-VD/VT vs VR mortality comparison (Ann Intensive Care 2019).
**Commit:** Phase 1 — dead-space accuracy hierarchy

## 2026-06-20 — Built Harris–Benedict dead space + manual override; validated → HB WORSENED CO2 prediction
**Question:** Does the Harris–Benedict physiological dead space improve CO2 prediction vs the fixed 2.2 mL/kg?
**Method:** Built `dead_space_ml()` in physiology.py (priority: manual measured → HB → anatomic). Added a CO2 shadow test (Exp 4): predict the next ABG PaCO2 after a VT change, fixed vs HB. Demographics from patients/icustays/chartevents. 164 VT-change ABG pairs, 71 stays.
**Result (aggregate):**
- Fixed anatomic (2.2 mL/kg): MAE **14.42 mmHg**.
- Harris–Benedict: MAE **33.59 mmHg** — **~133% WORSE.**
**Why:** HB gives a much higher dead space (Vd/Vt ~0.5–0.73), making (VT − Vd) a small, noise-amplified number → CO2 predictions over-react to VT changes. Plus HB's resting-metabolism VCO2 estimate is off in non-resting ICU patients, and CO2 prediction over hours violates steady state (the fixed baseline MAE of 14 mmHg is already large — CO2 prediction is intrinsically noisy).
**Decision:** Built as requested, but **HB is OPT-IN (`use_hb=False` default)** so it can't silently degrade the model; **manual measured dead space always wins**; anatomic stays the default. **Lesson: a more physiologically accurate dead space ≠ a better CO2 prediction.** Next: per-patient *learned* dead space (fit from the patient's own CO2 data), which optimizes for prediction directly.
**Commit:** Phase 1 — HB dead space (built, opt-in; validation negative)

## 2026-06-20 — Strategic: the PEEP problem is the hard core (Ahmed's domain insight)
**Insight (Ahmed):** PEEP response is heterogeneous (MP rises with PEEP in some patients, falls in others); R/I is impractical (needs a bedside maneuver) AND incomplete (doesn't say how *much* PEEP). 
**Cross-check:** matches our demo (heterogeneous compliance response; our β is a population average) and the literature (no bedside method cleanly predicts individual recruitability — EIT/esophageal/mechanics disagree; Ann Intensive Care 2024). 
**Options recorded in `_Research_Agenda`:** A) PEEP-humility (optimize VT/RR, hold PEEP — drops R/I); B) learn the patient's own PEEP response from charted history; C) closed-loop small test-step; D) EIT/esophageal (future). Standing rule: never raise PEEP just for compliance (ART). 
**Decision:** pending Ahmed's pick of direction. **Strong candidate = A as default + B when history exists.**
**Sources:** Ann Intensive Care 2024 (bedside PEEP methods vs recruitability); ART JAMA 2017.
**Commit:** Phase 1 — PEEP-problem design direction

## 2026-06-20 — Solvable win #1: how much MP can VT↔RR redistribution save? → almost none
**Question:** With PEEP held and CO2 clearance preserved, how much mechanical power can be safely saved by rebalancing VT↔RR within lung-protective limits, on real patients?
**Method:** Exp 5 on the demo — 3,077 ventilated snapshots; used each patient's OWN measured compliance + resistive gap; held alveolar ventilation constant (≈ constant CO2); VT 4–8 mL/kg, plateau ≤ 30.
**Result:** median delivered MP **15.7 J/min**; **median MP savable = 0.1 J/min** (mean 0.32); only **7.6%** of snapshots could save ≥1 J/min, **0.6%** ≥3.
**Why:** at constant CO2 clearance, lowering VT forces RR up (more breaths), and the fixed dead space per breath erodes the benefit — so MP is nearly flat across the allowed VT/RR range. The classic "low VT, high RR" benefit largely cancels once gas exchange is held constant; and many patients are already at protective VT, so the lever is mostly spent.
**Implication (important — reshapes the value proposition):** the SAFE knob (VT↔RR at constant ventilation) barely moves MP. Real MP reduction must come from **(a) permissive hypercapnia** (accept higher CO2 → less ventilation → lower MP; the prototype's actual main lever), or **(b) PEEP / driving pressure** (the parked hard problem).
**Decision:** next solvable experiment = quantify MP savings from **permissive hypercapnia** (reduce ventilation to a pH floor), where the achievable savings actually are — with the raised-ICP contraindication gate.
**Commit:** Phase 1 — MP-savings via VT/RR redistribution (near-zero)
