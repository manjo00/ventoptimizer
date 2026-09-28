# _Compact.md — the whole project state on one page
**Read this FIRST after any `/compact`, resume, or new session (then `_Current_Task.md`). Keep it ≤ ~1 page. Refresh it at the end of EVERY task (with `_Task_History.md`).**
Last refreshed: 2026-09-28 (after core-goal step 2a)

## 📋 Repeatable prompts (copy-paste)
- **Before compacting (refresh the state):** `Refresh docs/_Compact.md with everything from this session, then commit + push.`
- **To compact:** `/compact Read docs/_Compact.md — it is the authoritative project state. Keep this summary consistent with it and preserve the CORE GOAL, locked decisions, key numbers, next steps and open items.`
- **To resume (any new session):** `Read CLAUDE.md, then docs/_Compact.md, then docs/_Current_Task.md, and continue from "Where we are / next".`

## 1. What this is
**VentOptimizer** — a decision-support **prototype** (not a medical device) that recommends ventilator settings minimizing mechanical power within safety limits, for **all** ventilated patients (not ARDS-only). **Math-only, on pre-recorded data.** Python engine (`engine/`) = source of truth; `app/ventoptimizer.html` = front-end demo. Repo: `manjo00/ventoptimizer` (main). Owner: Ahmed (RT student, not a coder → teaching mode).

## 2. THE CORE GOAL (locked)
Solve **PEEP** via math on recorded data: **(1) choose the highest SAFE PEEP** (recruit without overdistension); **(2) predict the PEEP→compliance change → compute the resulting mechanical power.** A dataset must carry every math input. Live-patient testing = possible future only.

## 3. Locked decisions
- **Objective metric:** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098×RR×VT×½(Pplat−PEEP)` (`_Required_Variables` §1b); report absolute MP alongside. **Never compare by absolute MP** (it rises ~+1 J/min per cmH₂O PEEP → would derecruit).
- **Corrected hypothesis:** in recruitable lungs, PEEP up to an optimum ↑compliance and ↓tidal/per-unit power, though absolute power rises; past the optimum both worsen (U-shaped).
- **Dataset: MIMIC-IV confirmed (2026-09-28)** — every required input present; only gap = absolute pleural reference (partly covered: esophageal-derived transpulmonary pressure in ~3% of stays = validation subset). AmsterdamUMCdb optional later.
- **No population recruitment rule (step 1b):** `C×(1+β·ΔPEEP)` retracted. **No own-last-step rule either (step 2a):** option B retired. Sub-problem 2 needs **state predictors** (PEEP level, direction, baseline mechanics, gases) or multi-point per-patient curves on full MIMIC, with **prediction intervals**; **option C (predict a range + verify with a small reversible test step)** is the fallback design. Do not implement a constant β in `physiology.py`.
- **Evidence rule:** every clinical number cited; prefer Q1 journals; label strength (RCT > observational > our data). *Association ≠ intervention. Prediction ≠ clinical titration* (ART trial: compliance-titrated PEEP ↑mortality).
- **Data governance:** credentialed data never to Claude; local-only loop; aggregates only; never commit patient data.
- **Data-handling rule:** never carry a measured value (plateau) across a setting change it wasn't measured under — a **usable pair** = two real plateaus, one PEEP step between, 'after' ≤4 h, controlled mode both sides (`validate_mimic.usable_peep_pairs`).
- **Overrides:** measured dead space always wins; practitioner-set pH/CO₂ limit (stricter of manual vs evidence floor). HB dead space is **opt-in** (`use_hb`) — it worsened CO₂ prediction.
- Git checkpoint + **push after every task**.

## 4. Key findings (demo = open MIMIC-IV, 100 pts / 140 ICU stays / 67 ventilated)
- **Coverage (share of ventilated stays):** VT/PEEP/RR/mode/FiO₂/SpO₂ 100%, Ppeak 99%, **Pplat 84%**, chart gases 87% (lab ABG 94%), **height 72% → 88%** with outpatient `omr`, vent episodes 90%, cuff MAP 99%, CVP 49%, vasopressors 63%, ICP 3%, transpulmonary pressure 3%. Modes ≈50% controlled. Only 495 of 8,040 compliance snapshots carry a real plateau.
- **Honest PEEP-step results (step 1b, 27 usable pairs / 13 stays):** PEEP↑ → compliance **+8.6%** median [IQR −7 to +31]; PEEP↓ → **−4.1%** [−30 to +35]; only **56%** move the expected way; **β = 0.026**/cmH₂O (95% −0.038 to +0.089, includes 0); LOSO plateau MAE **3.57 baseline vs 3.73 PEEP-aware (no gain)**. **Retracted (carried-plateau artifacts):** +40%/−23%, β 0.083, the 28% gain.
- **Per-patient pilot (step 2a):** PEEP-step spread = **3.2×** the no-change noise floor (IQR −9 to +7) → the individual response is **real**; but consecutive steps agree in direction only **43%** (Spearman 0.09; 5 stays / 14 step pairs); predicting later steps: baseline MAE **4.01** < population 4.42 < blend 5.40 < **own last step 8.70** < own 24-h curve 10.59 → own history amplifies noise.
- **Survives on real plateaus:** compliance varies **17.7%** within a patient; PEEP changes are the hardest to predict (MAE **4.19** vs VT-only **2.71** vs noise floor **1.41**).
- MP savable by VT↔RR redistribution ≈ **0** (median 0.1 J/min) → PEEP + permissive hypercapnia are the real levers. HB dead space **worsened** CO₂ prediction (14.4→33.6 mmHg).
- **CVP** spot-only (pleural swing needs waveform data). **No-balloon lung stress:** elastance ratio `(Pplat−PEEP)×0.7`; PEEP-step method.
- Manuscript anchor: OR **1.09**/J·min; quartile survival 89→70%; harm below 17 J/min. Theories T1–T12 graded in `_Literature_Validation.md`.
- Scale-up: full MIMIC-IV ≈ ×500 → ~10k usable pairs → the decisive experiment for state predictors of the individual response.

## 5. Where we are / next
- **Phase 1, centered on PEEP. Steps 1, 1b, 2a DONE.** Next: **(2b)** pre-specified full-MIMIC analysis plan (usable-pair extraction + sensitivity; β distribution; state-predictor model with by-patient hold-out and prediction intervals; U-shaped per-patient curves where ≥3 real levels) → Ahmed runs the three scripts locally. **(3)** sub-problem 1 (highest safe PEEP) via ceilings + oxygenation + gates — independent of prediction, can start now.
- PEEP design options A–E in `_Research_Agenda` (B retired; C = fallback); input list + gaps in `_Required_Variables.md`.
- Secondary (after PEEP): permissive-hypercapnia lever, driving pressure as explicit target (Costa: 4× RR), per-patient dead space.
- Noticed, not fixed: MP formula docs-vs-code mismatch; exp4/exp5 still on carried plateaus (conclusions robust).

## 6. Open with Ahmed
- **Strategic call:** (a) state-predictor model on full MIMIC, (b) shift to option C "predict a range + verify with a test step", or (c) both — model first, test-step as the safety net. Recommendation: **(c)**.
- **After step 2b: run `check_coverage.py`, `validate_mimic.py`, `peep_response_pilot.py` on full MIMIC-IV locally; paste the printed output** (aggregate only).
- Who is PhysioNet-credentialed (runs full-MIMIC locally).
- Pick the paper-title angle (tidal-vs-absolute insight / individualized-PEEP method / no-balloon hook).
- Folder rename `research poster day` → `VentOptimizer` (manual; cosmetic).

## 7. Guardrails (never)
Push PEEP up just for compliance (ART) · permissive mode without a raised-ICP gate · uncited clinical numbers · patient data in git or to Claude · claim a survival benefit (only association) · forward-fill a measurement across the setting change it depends on · implement a population recruitment constant · show a compliance prediction without its uncertainty.

## 8. Re-entry checklist
1) `CLAUDE.md` (goal + rules) → 2) this file → 3) `docs/_Current_Task.md` → 4) act → 5) at task end refresh this file + `_Task_History.md`, commit, push.
