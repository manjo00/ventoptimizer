# _Compact.md — the whole project state on one page
**Read this FIRST after any `/compact`, resume, or new session (then `_Current_Task.md`). Keep it ≤ ~1 page. Refresh it at the end of EVERY task (with `_Task_History.md`).**
Last refreshed: 2026-09-28 (after sub-problem 1 v1)

## 📋 Repeatable prompts (copy-paste)
- **Before compacting (refresh the state):** `Refresh docs/_Compact.md with everything from this session, then commit + push.`
- **To compact:** `/compact Read docs/_Compact.md — it is the authoritative project state. Keep this summary consistent with it and preserve the CORE GOAL, locked decisions, key numbers, next steps and open items.`
- **To resume (any new session):** `Read CLAUDE.md, then docs/_Compact.md, then docs/_Current_Task.md, and continue from "Where we are / next".`

## 1. What this is
**VentOptimizer** — a decision-support **prototype** (not a medical device) that recommends ventilator settings minimizing mechanical power within safety limits, for **all** ventilated patients (not ARDS-only). **Math-only, on pre-recorded data.** Python engine (`engine/`) = source of truth; `app/ventoptimizer.html` = front-end demo. Repo: `manjo00/ventoptimizer` (main). Owner: Ahmed (RT student, not a coder → teaching mode). Plain-language pitch for the team/supervisor: `docs/_Team_Brief.md` (refresh it when the state changes).

## 2. THE CORE GOAL (locked)
Solve **PEEP** via math on recorded data: **(1) choose the highest SAFE PEEP** (recruit without overdistension) — ✅ v1 built (`engine/safe_peep.py`); **(2) predict the PEEP→compliance change → compute the resulting mechanical power** — ⏳ full-MIMIC run pending. A dataset must carry every math input. Live-patient testing = possible future only.

## 3. Locked decisions
- **Objective metric:** minimize **and** compare by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098×RR×VT×½(Pplat−PEEP)`; report absolute MP alongside. **Never compare by absolute MP.**
- **MP formula (2026-09-28):** engine uses Gattinoni's plateau form (a) when a plateau exists; the manuscript's peak-only surrogate (b) `[M][N8]` as fallback and always reported alongside, labelled (`_Evidence_Base` [E1]).
- **Corrected hypothesis:** in recruitable lungs, PEEP up to an optimum ↑compliance and ↓tidal/per-unit power, though absolute power rises; past the optimum both worsen (U-shaped).
- **Dataset: MIMIC-IV confirmed** — every required input present; only gap = absolute pleural reference (esophageal-derived transpulmonary pressure in ~3% of stays = validation subset).
- **Design for sub-problem 2 (Ahmed — option (c)):** state-predictor model + uncertainty range on full MIMIC (**frozen plan `docs/_Analysis_Plan_FullMIMIC.md`**, code `engine/state_predictor.py`, H1: plateau-MAE gain ≥ 15% AND 80%-interval coverage ≥ 75%, n ≥ 300, grouped-by-patient CV) **+ option C test step as the safety net** (primary if H1 fails). **Retracted/retired:** population β (1b), own-last-step slope (2a). Never a constant β; never a prediction without its range; never change a frozen criterion after seeing results.
- **Sub-problem 1 (2026-09-28):** the ceiling = highest PEEP with plateau ≤ 30 `[E3]`, ΔP ≤ 15 `[N9][E4]`, ΔP_L ≤ 11.7 `[N9]` under a cautious margin (compliance may fall 5%/cmH₂O `[ASSUMPTION]` — to be replaced by H5), capped by the PEEP/FiO₂ envelope `[E3][N7]`; vetoes: ICP > 22 `[N10]`, MAP < 65 `[N11]`, spontaneous effort, already over a limit; cautions: vasopressor, chest tube, auto-PEEP. A ceiling is never a recommendation to go there; it bounds sub-problem 2's search.
- **Evidence rule:** every clinical number cited; prefer Q1; label strength. *Association ≠ intervention. Prediction ≠ clinical titration* (ART).
- **Data governance:** credentialed data never to Claude; local-only loop; aggregates only (cells < 10 suppressed); never commit patient data.
- **Data-handling rule:** never carry a measured plateau across a setting change — **usable pair** = two real plateaus, one PEEP step, 'after' ≤4 h, controlled both sides.
- **Overrides:** measured dead space wins; practitioner pH/CO₂ limit; HB dead space opt-in. Git checkpoint + **push after every task**.

## 4. Key findings (demo = open MIMIC-IV, 67 ventilated stays)
- **Coverage:** VT/PEEP/RR/mode/FiO₂/SpO₂ 100%, Ppeak 99%, **Pplat 84%**, gases 87% (lab 94%), **height 72% → 88%** with `omr`, MAP 99%, CVP 49%, vasopressors 63%, ICP 3%, transpulmonary 3%. Modes ≈50% controlled. Only 495 of 8,040 compliance snapshots carry a real plateau.
- **Honest PEEP-step results (1b, 27 usable pairs / 13 stays):** PEEP↑ → compliance **+8.6%** [IQR −7 to +31]; PEEP↓ → **−4.1%** [−30 to +35]; **β 0.026** (95% −0.038 to +0.089); no held-out gain. **Retracted:** +40%/−23%, β 0.083, 28% gain.
- **Per-patient pilot (2a):** spread = **3.2×** the noise floor (IQR −9 to +7) → response real; direction repeats **43%**, Spearman 0.09; own-last-step MAE 8.70 vs baseline 4.01.
- **Safe-PEEP ceiling (sub-problem 1, 488 real controlled moments):** **32% vetoed** (MAP < 65: 70, effort 55, ΔP > 15: 39); where an increase is allowed, headroom **median 5 cmH₂O (IQR 2–6)**, **11% none**; binding limit **ΔP 50%**, plateau 38%, envelope 12%; cautions: vasopressor 38%, auto-PEEP 25%, chest tube 21%; charted PEEP within the ALVEOLI envelope 84%, below 16%, above 0%; SpO₂ above target 83%.
- **Survives:** compliance varies **17.7%** within a patient; PEEP changes hardest to predict (MAE 4.19 vs VT-only 2.71 vs noise floor 1.41). MP savable by VT↔RR ≈ **0**. HB dead space worsened CO₂ prediction. Elastance ratio `(Pplat−PEEP)×0.7` = no-balloon stress.
- Manuscript anchor: OR **1.09**/J·min; harm below 17 J/min (`[N8]` agrees). T1–T12 graded in `_Literature_Validation.md`.
- Full MIMIC ≈ ×500 → ~10k usable pairs = the decisive run (`state_predictor.py` pipeline-tested; UNDERPOWERED on the demo by design).

## 5. Where we are / next
- **Waiting on Ahmed's full-MIMIC run** (four scripts, plan §12) → apply the frozen decision rules (§10); H5 replaces the safe-PEEP margin.
- **Next build (independent):** wire the ceiling into `optimizer.py` (candidate PEEPs ∈ [current, ceiling]; vetoes/cautions in the explanation; MP (a) + MP_dyn (b) labelled; MP_tidal as the comparison); implement the peak-only MP fallback in `physiology.py`; add the option C output (compliance-change **range** + test-step protocol).
- Later: `safe_peep.py` v2 (patient-specific elastance ratio in the transpulmonary subset; per-level margins from H5).
- Secondary: permissive-hypercapnia lever, driving pressure as explicit target (Costa: 4× RR), per-patient dead space.
- Noticed, not fixed: exp4/exp5 on carried plateaus; `_Data_Access` download target; chest-tube caution is coarse (needs a cited air-leak criterion).

## 6. Open with Ahmed
- **Run the four scripts on full MIMIC-IV, paste the printed output** (aggregates only); MIMIC-IV version; who is credentialed.
- Pick the paper-title angle (tidal-vs-absolute insight / individualized-PEEP method / no-balloon hook).
- Folder rename `research poster day` → `VentOptimizer` (manual; cosmetic).

## 7. Guardrails (never)
Push PEEP up just for compliance (ART) · treat a ceiling as a target · permissive mode without a raised-ICP gate · uncited clinical numbers · patient data in git or to Claude · claim a survival benefit · forward-fill a measurement across the setting change it depends on · a population recruitment constant · a compliance prediction without its range · changing a frozen criterion after seeing results.

## 8. Re-entry checklist
1) `CLAUDE.md` (goal + rules) → 2) this file → 3) `docs/_Current_Task.md` → 4) act → 5) at task end refresh this file + `_Task_History.md`, commit, push.
