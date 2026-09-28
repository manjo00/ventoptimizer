# _Compact.md — the whole project state on one page
**Read this FIRST after any `/compact`, resume, or new session (then `_Current_Task.md`). Keep it ≤ ~1 page. Refresh it at the end of EVERY task (with `_Task_History.md`).**
Last refreshed: 2026-09-28 (after core-goal step 2b)

## 📋 Repeatable prompts (copy-paste)
- **Before compacting (refresh the state):** `Refresh docs/_Compact.md with everything from this session, then commit + push.`
- **To compact:** `/compact Read docs/_Compact.md — it is the authoritative project state. Keep this summary consistent with it and preserve the CORE GOAL, locked decisions, key numbers, next steps and open items.`
- **To resume (any new session):** `Read CLAUDE.md, then docs/_Compact.md, then docs/_Current_Task.md, and continue from "Where we are / next".`

## 1. What this is
**VentOptimizer** — a decision-support **prototype** (not a medical device) that recommends ventilator settings minimizing mechanical power within safety limits, for **all** ventilated patients (not ARDS-only). **Math-only, on pre-recorded data.** Python engine (`engine/`) = source of truth; `app/ventoptimizer.html` = front-end demo. Repo: `manjo00/ventoptimizer` (main). Owner: Ahmed (RT student, not a coder → teaching mode).

## 2. THE CORE GOAL (locked)
Solve **PEEP** via math on recorded data: **(1) choose the highest SAFE PEEP** (recruit without overdistension); **(2) predict the PEEP→compliance change → compute the resulting mechanical power.** A dataset must carry every math input. Live-patient testing = possible future only.

## 3. Locked decisions
- **Objective metric:** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098×RR×VT×½(Pplat−PEEP)` (`_Required_Variables` §1b); report absolute MP alongside. **Never compare by absolute MP.**
- **Corrected hypothesis:** in recruitable lungs, PEEP up to an optimum ↑compliance and ↓tidal/per-unit power, though absolute power rises; past the optimum both worsen (U-shaped).
- **Dataset: MIMIC-IV confirmed** — every required input present; only gap = absolute pleural reference (esophageal-derived transpulmonary pressure in ~3% of stays = validation subset).
- **Design for sub-problem 2 (2026-09-28, Ahmed — option (c)):** state-predictor model + uncertainty range on full MIMIC (**frozen plan `docs/_Analysis_Plan_FullMIMIC.md`**, code `engine/state_predictor.py`, primary criterion H1: plateau-MAE gain ≥ 15% AND 80%-interval coverage ≥ 75%, n ≥ 300, grouped-by-patient CV) **+ option C test step as the safety net** (primary if H1 fails). **Retracted/retired:** population β (1b), own-last-step slope (2a). Never a constant β in `physiology.py`; never a prediction without its range; never change a frozen criterion after seeing results.
- **Evidence rule:** every clinical number cited; prefer Q1; label strength. *Association ≠ intervention. Prediction ≠ clinical titration* (ART).
- **Data governance:** credentialed data never to Claude; local-only loop; aggregates only (cells < 10 suppressed); never commit patient data.
- **Data-handling rule:** never carry a measured plateau across a setting change — **usable pair** = two real plateaus, one PEEP step, 'after' ≤4 h, controlled both sides (`validate_mimic.usable_peep_pairs`).
- **Overrides:** measured dead space wins; practitioner pH/CO₂ limit; HB dead space opt-in. Git checkpoint + **push after every task**.

## 4. Key findings (demo = open MIMIC-IV, 67 ventilated stays)
- **Coverage:** VT/PEEP/RR/mode/FiO₂/SpO₂ 100%, Ppeak 99%, **Pplat 84%**, gases 87% (lab 94%), **height 72% → 88%** with `omr`, vent episodes 90%, MAP 99%, CVP 49%, vasopressors 63%, ICP 3%, transpulmonary 3%. Modes ≈50% controlled. Only 495 of 8,040 compliance snapshots carry a real plateau.
- **Honest PEEP-step results (1b, 27 usable pairs / 13 stays):** PEEP↑ → compliance **+8.6%** [IQR −7 to +31]; PEEP↓ → **−4.1%** [−30 to +35]; **β 0.026** (95% −0.038 to +0.089); LOSO MAE 3.57 baseline vs 3.73 PEEP-aware (no gain). **Retracted:** +40%/−23%, β 0.083, 28% gain (carried-plateau artifacts).
- **Per-patient pilot (2a):** spread = **3.2×** the no-change noise floor (IQR −9 to +7) → response real; direction repeats **43%**, Spearman 0.09; own-last-step MAE 8.70 vs baseline 4.01 → amplifies noise.
- **Survives:** compliance varies **17.7%** within a patient; PEEP changes hardest to predict (MAE 4.19 vs VT-only 2.71 vs noise floor 1.41).
- MP savable by VT↔RR ≈ **0** → PEEP + permissive hypercapnia are the real levers. HB dead space worsened CO₂ prediction. CVP spot-only. Elastance ratio `(Pplat−PEEP)×0.7` = no-balloon stress (upper side).
- Manuscript anchor: OR **1.09**/J·min; harm below 17 J/min. T1–T12 graded in `_Literature_Validation.md`.
- **Step 2b pipeline test:** `state_predictor.py` runs end-to-end on the demo and labels itself UNDERPOWERED (27 < 300); full MIMIC ≈ ×500 → ~10k pairs = the decisive run.

## 5. Where we are / next
- **Waiting on Ahmed's full-MIMIC run** (four scripts, `_Analysis_Plan_FullMIMIC.md` §12); then apply the frozen decision rules (§10).
- **Next task (independent): sub-problem 1 — the highest SAFE PEEP** → `engine/safe_peep.py`: ceilings (Pplat ≤ 30 `[E3]`, driving-pressure ceiling `[TO-CITE]`, elastance-ratio stress `[ASSUMPTION]`), oxygenation floors (`[E3]`, PEEP/FiO₂ envelope `[E3][N7]`), gates (ICP, air leak, hemodynamics `[TO-CITE]`, effort, auto-PEEP); validate on the demo (charted PEEP vs ceiling). H5 from the full run later sharpens the overdistension ceiling.
- Then: implement the winning branch (model + interval, or option C range + test step) in `physiology.py` / `optimizer.py`.
- Secondary: permissive-hypercapnia lever, driving pressure as explicit target (Costa: 4× RR), per-patient dead space.
- Noticed, not fixed: MP formula docs-vs-code mismatch (settle before sub-problem 1's MP reporting); exp4/exp5 on carried plateaus; `_Data_Access` download target to reconcile.

## 6. Open with Ahmed
- **Run the four scripts on full MIMIC-IV, paste the printed output** (aggregates only); which MIMIC-IV version; who is credentialed.
- Pick the paper-title angle (tidal-vs-absolute insight / individualized-PEEP method / no-balloon hook).
- Folder rename `research poster day` → `VentOptimizer` (manual; cosmetic).

## 7. Guardrails (never)
Push PEEP up just for compliance (ART) · permissive mode without a raised-ICP gate · uncited clinical numbers · patient data in git or to Claude · claim a survival benefit · forward-fill a measurement across the setting change it depends on · a population recruitment constant · a compliance prediction without its range · changing a frozen criterion after seeing results.

## 8. Re-entry checklist
1) `CLAUDE.md` (goal + rules) → 2) this file → 3) `docs/_Current_Task.md` → 4) act → 5) at task end refresh this file + `_Task_History.md`, commit, push.
