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

## 2026-09-27 — Idea (Ahmed): PEEP via transpulmonary-pressure target from limited data
**Idea:** set PEEP by transpulmonary pressure (target end-expiratory ≈ 0) — a *dose*, which R/I can't give — and derive it from limited data.
**Evidence checked (Q1):** EPVent-1 (Talmor NEJM 2008) positive for oxygenation; **EPVent-2 (Beitler JAMA 2019) negative** for mortality/VFDs vs empirical high PEEP; AJRCCM 2021 reanalysis — mortality lowest at transpulmonary ≈ 0, benefit only in less-sick patients. So principle sound, balloon strategy unproven.
**Limited-data lead:** transpulmonary normally needs an esophageal balloon (not in MIMIC), BUT CVP swings may surrogate pleural pressure (J Clin Monit Comput 2024); CVP is routinely charted (likely in MIMIC) → a no-balloon route that is passively recorded and potentially MIMIC-validatable. `[low-strength — one small study]`
**Decision:** recorded as PEEP **Option E** in `_Research_Agenda` (PEEP stays parked). Strong candidate for when we resume — check CVP in the data, test the estimate, quantify MP impact.
**Sources:** EPVent-2 (JAMA 2019); reanalysis (AJRCCM 2021); Talmor (NEJM 2008); CVP-surrogate (J Clin Monit Comput 2024).
**Commit:** docs — PEEP Option E (transpulmonary target + CVP surrogate)

## 2026-09-27 — PIVOT: PEEP is the core goal (un-parked); math-only on recorded data
**Decision (Ahmed):** the project can't proceed without solving PEEP. Two sub-problems, **math-only, on pre-recorded datasets:** (1) choose the highest *safe* PEEP (no overdistension); (2) predict the PEEP→compliance change to compute MP. A dataset **must carry every value the math needs**. Scope = prototype on recorded data; live-patient testing is a possible future, not now.
**Actions:** enshrined in `CLAUDE.md` → THE CORE GOAL; un-parked in `_Research_Agenda` + added the required-input list & the pleural-signal gap; refocused `_Current_Task` on the two PEEP sub-problems; CO₂/dead-space demoted to secondary.
**Commit:** docs — enshrine PEEP as THE CORE GOAL in CLAUDE.md

## 2026-09-27 — Stress-testing THE hypothesis: absolute MP vs per-unit MP (critical)
**Question (Ahmed):** Is "recruitable → ↑PEEP → ↑compliance → ↓mechanical power" correct?
**Finding (Q1):** **Partly wrong as stated.** *Absolute* MP **RISES** with PEEP (~+1 J/min per cmH₂O), even in recruitable lungs (*Lung recruitability determines the impact of PEEP on mechanical power*, Crit Care 2026; bedside PEEP-MP post hoc PMC13515540). The protective effect is on **power/strain per AERATED lung unit**, which recruitment lowers; recruitability (R/I) sets the sign; the PEEP↔protection relationship is **U-shaped** (optimal PEEP; Intensive Care Med 2025).
**Implication (big):** minimizing *absolute* MP over PEEP would **derecruit** → the project's objective must be redefined — (a) tidal/dynamic (driving-pressure) power, (b) per-aerated-unit/strain, or (c) absolute-MP-with-recruitment-constraint. The user's instinct is right for the *tidal/per-unit* power, wrong for *absolute* MP.
**Actions:** added the ⚠ objective-function caveat to CLAUDE.md → THE CORE GOAL, and the full "PEEP: the objective-function problem" entry + corrected hypothesis to `_Research_Agenda`.
**Sources:** Crit Care 2026 (recruitability & PEEP MP); bedside PEEP-MP post hoc (PMC13515540); Intensive Care Med 2025 (U-shaped PEEP).
**Commit:** docs — objective-function caveat (absolute vs per-unit MP)

## 2026-09-27 — DECISION: objective = tidal/driving-pressure MP (compare by same; report absolute)
**Decision (Ahmed):** the tool minimizes, and compares optimized vs un-optimized by, the **tidal / driving-pressure mechanical power** (breath energy; excludes the static PEEP baseline). Absolute MP is reported alongside for transparency + the manuscript link. Same metric on both sides → recruitment shows as a win; comparing by absolute MP would penalize correct recruitment.
**Actions:** locked in CLAUDE.md → THE CORE GOAL (objective-function caveat) and `_Research_Agenda` (option (a) chosen); noted in `_Current_Task`.
**Commit:** docs — lock objective (tidal/driving-pressure MP)

## 2026-09-28 — Core goal step 1: the required-variable list + MIMIC-IV coverage (and a plateau artifact found)
**Question:** Which recorded variables does the PEEP math need (sub-problems 1 & 2 + the locked tidal-MP objective), and does MIMIC-IV carry all of them?
**Method:** Derived the inputs equation by equation (`_Required_Variables.md` §1: Crs/ΔP, the MP split into static + resistive + tidal-elastic, the PEEP→compliance rule, ceilings/floors/gates, pairing, PBW, outcomes). Verified every code against the demo's `d_items` / `d_labitems`. Wrote `engine/check_coverage.py` (reads the big tables in chunks; aggregate output only) and ran it on the open demo: 140 ICU stays, **67 ventilated** (60 with an "Invasive Ventilation" procedure record).
**Result (coverage, share of ventilated stays):** every REQUIRED input present — VT 100%, PEEP 100%, RR 100%, mode 100%, FiO₂ 100%, SpO₂ 100%, Ppeak 99%, **Pplat 84%**, chart PaCO₂/pH 87% (lab ABG 94%), **height 72% → 88% with the outpatient `omr` fallback**, vent episodes 90%, outcome 100% (14 in-hospital deaths, 20.9%). RECOMMENDED: total PEEP 82%, invasive MAP 67% / cuff MAP 99%, CVP 49%, vasopressors 63%, chest tube 36%, NMB infusions 0% (codes exist). **New:** MIMIC-IV *does* chart esophageal-derived transpulmonary pressure (224746/224747) — 2 of 67 stays (3%). Modes: ≈50% of mode rows are controlled (CMV/ASSIST/AutoFlow, APV (cmv), CMV/ASSIST, P-CMV); the rest CPAP/PSV, SPONT, PSV/SBT, etc.
**Result (feasibility of the PEEP math):** 8,040 compliance-computable snapshots but only **495** carry a freshly charted plateau; **183** PEEP-change events (82 up / 101 down) → 'before' plateau measured under the old PEEP in 88 (48%); 'after' plateau charted **at the change row in only 24 (13%)**; within 4 h at the new PEEP in 44 (24%); **usable pairs 30 (16%); usable + controlled mode 28 (15%)**. Stays with ≥2 fresh PEEP levels: 17 (≥3: 5). Gas ±2 h around events: 12%; SpO₂ 99%; FiO₂ (±4 h) 93%; MAP 94%.
**⚠ Artifact discovered:** `validate_mimic.load_snapshots` forward-fills the plateau. exp2/exp3 took the plateau at the change row as the "after" observation — fresh in only 13% of events. A stale plateau at a new PEEP fakes a compliance change *by construction*: C = VT/(Pplat_old − PEEP_new) rises when PEEP rises and falls when PEEP falls — exactly the "+40% / −23%" pattern we reported; the PEEP-aware correction then partly fits that artifact. → **β≈0.083, +40%/−23%, the 28% held-out gain, and the "PEEP changes MAE 4.80 = crux" split are SUSPECT** until re-run on usable pairs. Lesson for the notebook: *forward-filling a measured variable creates fake observations; only carry a value while the settings it was measured under are unchanged.*
**Decision:** **MIMIC-IV confirmed as the prototype dataset** (all inputs present; the pleural reference only in a small subset + proxies). New top priority: re-run exp2/exp3 on usable pairs (fresh plateau at the new PEEP ≤4 h, controlled both sides, valid 'before'). Ahmed to run `check_coverage.py` on full MIMIC-IV and paste the output. Noticed (not fixed): docs print the peak-only MP surrogate while the engine uses the plateau form; `validate_mimic.py` loads all of chartevents at once (won't scale to full MIMIC — needs the chunked reader).
**Commit:** feat/docs — required-variable list + coverage checker (core goal step 1)

## 2026-09-28 — Step 1b: honest re-run of the PEEP experiments on REAL plateau measurements (usable pairs)
**Question:** Do the recruitment findings (β≈0.083; +40%/−23%; 28% held-out gain; PEEP-change MAE 4.80 vs VT-only 2.68) survive when only plateaus actually measured under each PEEP are used?
**Method:** `validate_mimic.py` rebuilt: sliced (chunked) reading of chartevents; every snapshot now carries `pplat_fresh` (a real plateau charted at that time) and `controlled` (ventilator mode in force ∈ controlled set, from the mode text). New unit of analysis = **real plateau measurements**: 495 plausible in 55 stays, 488 in controlled modes. **Usable pair** = two consecutive real plateaus in one stay, **exactly one PEEP step** between them, 'after' plateau **≤ 4 h** after the step, **controlled mode both sides**. Old exp1–3 kept and re-run for comparison — they reproduce exactly (183 events, +40.0%/−23.4%, β 0.0833, 28.3%), so the old numbers were reproducible but built on carried plateaus. Honest versions: **exp1b** (compliance variation on real controlled plateaus), **exp2b** (predict each real plateau from the previous real plateau's compliance, ≤ 12 h apart, split by what changed in between), **exp3b** (descriptives; β by least squares through the origin with a 2,000-sample bootstrap interval; leave-one-stay-out prediction test).
**Result — funnel:** 43 consecutive real-plateau pairs with a PEEP difference → 31 single-step → 28 within 4 h → **27 usable (13 stays; 18 PEEP↑ / 9 PEEP↓; median |ΔPEEP| 3 cmH₂O)**. Sensitivity: 23 with no spontaneous breaths charted; 27 with the 'before' plateau ≤ 12 h old.
- **exp1b:** 34 patients; median within-patient compliance variation **17.7%** (old method 19.2%) → *compliance is not constant* **HOLDS**.
- **exp2b** (n / MAE / within 2 cmH₂O): no change **113 / 1.41 / 81%** (= measurement noise floor); VT-only **255 / 2.71 / 58%**; PEEP change **33 / 4.19 / 33%** → *PEEP changes are the hardest to predict* **HOLDS** on real plateaus (n = 33 is small).
- **exp3b:** PEEP↑ → compliance **+8.6% median [IQR −7.4 to +31.1]**; PEEP↓ → **−4.1% [IQR −29.5 to +35.1]**; only **56%** of steps moved the 'expected' way in either direction; **β = 0.026 /cmH₂O, bootstrap 95% [−0.038, +0.089] — includes zero**; leave-one-stay-out plateau prediction: baseline MAE **3.57** vs PEEP-aware **3.73** (**−4.5%** = no gain; median abs error 2.95 vs 2.32 → the correction helps typical pairs and hurts a few badly).
**Decision / interpretation:** (1) The +40%/−23%, β≈0.083 and the 28% gain were **artifacts of carried plateaus — retracted.** (2) On honest data the *average* recruitment effect is small and **a population slope is not supported**; the prototype's `×0.1` is an `[ASSUMPTION]` and probably too large on average. (3) The **individual response is wildly heterogeneous** (same-direction IQR spanning −30% to +35%) — Ahmed's original clinical insight, now confirmed on clean data → **sub-problem 2 must be solved per patient** (own PEEP-step history, predictors of the individual response, physiology bounds), not with a constant. (4) The demo is far too small to fit predictors (27 pairs) → the **full-MIMIC run (≈ 500× the pairs) is the decisive experiment** and needs a pre-specified analysis plan before Ahmed runs it. Noticed: exp4/exp5 still use carried-plateau snapshots (conclusions robust — exp5 applies the same compliance to both sides of its comparison); re-run on fresh rows later.
**Commit:** feat: step 1b — honest re-run on usable pairs (validate_mimic 1b experiments)

## 2026-09-28 — Step 2a: per-patient PEEP-response pilot (option B) on usable pairs
**Question:** Can a patient's OWN charted history predict their next PEEP response better than a population slope? Three sub-questions: is the individual response real (above measurement noise)? is it stable from one step to the next? does own-history prediction beat baseline / population?
**Method:** `engine/peep_response_pilot.py` (reuses the usable pairs from `validate_mimic.py`: 27 pairs / 13 stays; 495 real plateaus / 55 stays). **6a noise floor** = compliance change between consecutive real controlled plateaus with NO setting change (same PEEP, VT within 10 mL, ≤ 12 h apart). **6b consistency** = per-cmH₂O slope of consecutive usable steps within a stay (sign agreement, Spearman rank correlation). **6c prediction** = for every usable step with ≥ 1 earlier usable step in the same stay (14 steps, 5 stays): baseline (C unchanged), population β from other stays, own previous step(s) β, own recent compliance-vs-PEEP linear fit (24 h, ≥ 2 levels; n = 10), 50/50 blend — scored by after-step plateau MAE, compliance-change MAE and direction hit-rate.
**Result:**
- **6a:** noise floor n = 113: median 0.0%, **IQR −9.3 to +7.1**, 21% beyond ±20%. PEEP↑ IQR −7.4 to +31.1 (61% beyond ±20%); PEEP↓ IQR −29.5 to +35.1 (67%). **IQR width ratio 3.2 (per-cmH₂O-adjusted 3.0)** → the spread across a PEEP step is ~3× the noise floor → **the individual response is real, not measurement noise.**
- **6b:** 5 stays, 14 consecutive step pairs: **direction repeats 43%; Spearman 0.09**; median |slope| 0.10 / 0.12 per cmH₂O → **no stable per-patient slope from one step to the next.**
- **6c** (14 later steps): baseline plateau MAE **4.01** (compliance-change MAE 35%); population **4.42** (direction 57%); blend 5.40; **own previous step(s) 8.70** (direction 50%); own 24-h curve (n = 10) **10.59** (direction 60%) → **own-history methods are worse than doing nothing** — they amplify single-step noise.
**Decision / interpretation:** (1) Heterogeneity is real (3× noise) — confirms 1b. (2) But a patient's response is **not a constant**: consecutive steps disagree in direction as often as they agree. Physiologically expected — the response depends on the PEEP *level* (U-shape: recruit low, overdistend high), the step *direction*, and the patient's evolving state — so **"learn the patient's slope from their last step" (option B, simple form) is not supported; retired.** (3) What can still work, to be tested on full MIMIC (the step-2b plan): a response model with *state* predictors (PEEP level, direction, baseline Crs / ΔP, P/F or S/F, PaCO₂, BMI, days on vent) fitted on thousands of pairs; per-patient *curves* with many points and a U-shape rather than 24-h linear fits; noise reduction (average repeated plateaus; steps ≥ 4 cmH₂O); and **prediction intervals** instead of point estimates. (4) Strategic implication for the core goal (raise with Ahmed): if prediction stays this uncertain at full scale, the honest design is **option C — predict a range, then verify with a small reversible test step** — still evaluable math-only on recorded data (usable pairs *are* recorded test steps). Demo n is tiny (14 steps / 5 stays); nothing here is final.
**Commit:** feat: step 2a — per-patient PEEP-response pilot

## 2026-09-28 — Step 2b: decision (c) and the pre-specified full-MIMIC analysis plan (+ its code)
**Decision (Ahmed):** option **(c)** — build a **state-predictor model** of the compliance response to a PEEP step on full MIMIC-IV, **and** keep option C (quote a range, verify with a small reversible test step) as the safety net.
**Deliverables:** `docs/_Analysis_Plan_FullMIMIC.md` — a pre-registration-style plan frozen before the full data is touched: hypotheses H1–H5 with pass/fail criteria (H1: state model cuts after-step plateau MAE ≥ 15% vs "no change" AND 80% interval coverage ≥ 75%, n ≥ 300, grouped-by-patient CV), cohort, the unchanged usable-pair definition + sensitivity definitions S1/S2/S4/S5, outcomes (Δ%C; plateau; real move = |Δ%C| > 10%; overdistension = fall > 10% on PEEP-up), the fixed predictor list with look-back windows, models M0/M1/M2 (ridge, penalty by inner grouped CV, clip −70…+150%) and optional M3, the test-step analysis (H3), the overdistension analysis (H5 → sub-problem 1), decision rules for every outcome, governance (aggregates only; cells < 10 suppressed), run instructions. `engine/state_predictor.py` — the same plan in code, aggregate output, enforcing the minimum-n and cell-suppression rules.
**Pipeline test (demo):** runs end-to-end; 27 pairs → prints UNDERPOWERED as designed (the state model overfits at n = 27 — exactly why the minimum-n rule exists); Q3/Q5 strata mostly suppressed (< 10). Structural outputs agree with 1b/2a (β 0.026; noise-floor IQR width 16.5 points vs 51.5 for steps < 4 cmH₂O, ratio 3.1). Even with a 12-h window, a pre-step gas is missing in about half the demo pairs → CO₂-side features will be partly imputed at scale too (documented as a limitation).
**Next:** Ahmed runs the four scripts locally on full MIMIC-IV (`_Analysis_Plan_FullMIMIC.md` §12) and pastes the printed output. Meanwhile **sub-problem 1** (highest safe PEEP: ceilings + oxygenation + gates) starts — it does not depend on prediction.
**Commit:** feat: step 2b — pre-specified full-MIMIC analysis plan + state_predictor.py

## 2026-09-28 — Sub-problem 1: the highest SAFE PEEP (`engine/safe_peep.py`) + the MP-formula decision
**Question:** From the current chart alone — no prediction of the lung's response — what is the highest PEEP at which every cited limit still holds, and how does that ceiling compare with what clinicians actually charted?
**Method:** Literature check first (new citations `[N8]`–`[N11]` in `_Evidence_Base`): Serpa Neto 2018 ICM (peak-only MP surrogate; harm above 17 J/min), Chiumello 2016 Crit Care (ΔP > 15 and transpulmonary ΔP > 11.7 ↔ critical lung stress), Brain Trauma Foundation 4th ed. (treat ICP > 22 mmHg), Surviving Sepsis 2021 (initial MAP target 65 mmHg); ARDSNet/ALVEOLI PEEP/FiO₂ table values confirmed. **MP-formula mismatch settled:** the engine uses Gattinoni's plateau form (a) when a plateau exists (it is the form that yields the tidal-elastic objective), the peak-only surrogate (b) `[M][N8]` as fallback, always reported alongside and labelled. Built `engine/safe_peep.py`: compliance now → cautious projection (compliance may fall 5%/cmH₂O of PEEP increase, capped 50% — `[ASSUMPTION from the 1b spread]`) → highest PEEP ≤ 24 with plateau ≤ 30 `[E3]`, ΔP ≤ 15 `[N9][E4]`, ΔP×0.7 ≤ 11.7 `[N9]` → capped by the PEEP/FiO₂ envelope `[E3][N7]` → gates: **veto** (plateau/ΔP already over, ICP > 22 `[N10]`, MAP < 65 `[N11]`, spontaneous breaths / support mode) and **caution** (vasopressor running, chest tube, auto-PEEP ≥ 1, ICP monitored). Validation on the demo: every real controlled plateau moment (488 in 54 stays) with the state attached (SpO₂ ≤ 4 h, FiO₂ ≤ 24 h, MAP ≤ 2 h, ICP ≤ 2 h, total PEEP ≤ 4 h, vasopressor running at that time, chest tube in the stay).
**Result:** **156 of 488 moments (32%) vetoed** for any increase; an increase was allowed in **332 (68%)**. Where allowed, **headroom (ceiling − charted PEEP): median 5 cmH₂O, IQR 2–6; 11% had no headroom at all.** Binding limit where allowed: **driving pressure 50%**, plateau 38%, PEEP/FiO₂ envelope 12%. Veto reasons (moments): MAP < 65: 70 · spontaneous breaths 55 · ΔP already > 15: 39 · plateau > 30: 4 · ICP > 22: 1. Cautions: vasopressor running 187 (38%) · auto-PEEP ≥ 1: 122 (25%) · chest tube 104 (21%) · ICP monitored 9. Oxygenation: SpO₂ **above** 95% in 83% of moments, within target 17%, below < 1%. Charted PEEP vs the ALVEOLI envelope: within 84%, below 16%, **above 0%**. PEEP-up usable pairs vs the pre-step ceiling: 7 went above (suppressed, < 10), 11 stayed at/below → compliance fell > 10% in 27%.
**Interpretation:** (1) The safe ceiling is usually close: where an increase is allowed at all, half the moments have ≤ 5 cmH₂O of headroom under the cautious margin and one in nine has none — **driving pressure, not plateau, is the limit that bites most**. (2) Clinicians never exceeded the ALVEOLI envelope and sat below it 14% of the time. (3) Oxygenation is above target most of the time, so "room to lower FiO₂" is far more common than "need more PEEP". (4) Gates fire in a third of moments — hemodynamics and spontaneous effort are the main reasons; the module must always surface them. (5) The 5%/cmH₂O margin is the load-bearing assumption; the full-MIMIC H5 result will replace it with measured worst-case responses by PEEP level.
**Decision:** sub-problem 1 v1 is built and fully cited. It defines the search interval **[current PEEP, ceiling]** inside which sub-problem 2 (state model + test step) looks for the lowest tidal power. Integrate with the optimizer after the full-MIMIC run; the above-vs-below-ceiling outcome check joins the H5 outputs once n allows.
**Commit:** feat: sub-problem 1 — safe_peep.py ceilings/gates (cited) + MP-formula decision
