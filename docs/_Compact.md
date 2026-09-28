# _Compact.md — the whole project state on one page
**Read this FIRST after any `/compact`, resume, or new session (then `_Current_Task.md`). Keep it ≤ ~1 page. Refresh it at the end of EVERY task (with `_Task_History.md`).**
Last refreshed: 2026-09-28

## 📋 Repeatable prompts (copy-paste)
- **Before compacting (refresh the state):** `Refresh docs/_Compact.md with everything from this session, then commit + push.`
- **To compact:** `/compact Read docs/_Compact.md — it is the authoritative project state. Keep this summary consistent with it and preserve the CORE GOAL, locked decisions, key numbers, next steps and open items.`
- **To resume (any new session):** `Read CLAUDE.md, then docs/_Compact.md, then docs/_Current_Task.md, and continue from "Where we are / next".`

## 1. What this is
**VentOptimizer** — a decision-support **prototype** (not a medical device) that recommends ventilator settings minimizing mechanical power within safety limits, for **all** ventilated patients (not ARDS-only). **Math-only, on pre-recorded data.** Python engine (`engine/`) = source of truth; `app/ventoptimizer.html` = front-end demo. Repo: `manjo00/ventoptimizer` (main). Owner: Ahmed (RT student, not a coder → teaching mode).

## 2. THE CORE GOAL (locked)
Solve **PEEP** via math on recorded data: **(1) choose the highest SAFE PEEP** (recruit without overdistension); **(2) predict the PEEP→compliance change → compute the resulting mechanical power.** A dataset must carry every math input. Live-patient testing = possible future only.

## 3. Locked decisions
- **Objective metric:** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power**; report absolute MP alongside. **Never compare by absolute MP** (it rises ~+1 J/min per cmH₂O PEEP → would derecruit).
- **Corrected hypothesis:** in recruitable lungs, PEEP up to an optimum ↑compliance and ↓tidal/per-unit power, though absolute power rises; past the optimum both worsen (U-shaped).
- **Evidence rule:** every clinical number cited; prefer Q1 journals; label strength (RCT > observational > our data). *Association ≠ intervention. Prediction ≠ clinical titration* (ART trial: compliance-titrated PEEP ↑mortality).
- **Data governance:** credentialed data never to Claude; local-only loop; aggregates only; never commit patient data.
- **Overrides:** measured dead space always wins; practitioner-set pH/CO₂ limit (stricter of manual vs evidence floor). HB dead space is **opt-in** (`use_hb`) — it worsened CO₂ prediction.
- Git checkpoint + **push after every task**.

## 4. Key findings (demo = open MIMIC-IV, 100 pts)
- 8,480 vent snapshots / 56 pts. Compliance varies **~19%** within a patient (not constant).
- Plateau prediction MAE **3.05**; VT-only **2.68** (good); **PEEP changes 4.80 = the crux.** Smoothing didn't help.
- PEEP-aware compliance (β≈**0.083**/cmH₂O; recruitment **+40%** PEEP↑ / **−23%** PEEP↓): **−28%** error on held-out pts (population avg; individual response = the hard part).
- MP savable by VT↔RR redistribution ≈ **0** (median 0.1 J/min; 7.6% ≥1) → PEEP + permissive hypercapnia are the real levers.
- HB dead space **worsened** CO₂ prediction (14.4→33.6 mmHg).
- **CVP** in demo (itemid 220074, ~39 stays) but **spot-only**; the pleural "swing" needs waveform data (MIMIC-IV Waveform / HiRID). EtCO₂ sparse (202 rows).
- **No-balloon lung stress:** elastance ratio `(Pplat−PEEP)×0.7`; PEEP-step method; **183 PEEP changes** available. Absolute end-expiratory transpulmonary (collapse target) still needs a pleural reference.
- Manuscript anchor: OR **1.09**/J·min; quartile survival 89→70%; harm below 17 J/min. Theories T1–T12 graded in `_Literature_Validation.md`.

## 5. Where we are / next
- **Phase 1, centered on PEEP.** Next: **(1)** define the required-variable list + confirm dataset (MIMIC-IV covers all but the hi-res pleural signal); **(2)** prototype sub-problem 2 (PEEP→compliance→tidal MP) toward per-patient prediction; **(3)** sub-problem 1 (highest safe PEEP) via overdistension ceilings + oxygenation.
- PEEP design options A–E recorded in `_Research_Agenda` (E = transpulmonary target + CVP surrogate).
- Secondary (after PEEP): permissive-hypercapnia lever, driving pressure as explicit target (Costa: 4× RR), per-patient dead space.

## 6. Open with Ahmed
- Who is PhysioNet-credentialed (runs full-MIMIC locally).
- Pick the paper-title angle (tidal-vs-absolute insight / individualized-PEEP method / no-balloon hook).
- Folder rename `research poster day` → `VentOptimizer` (manual; cosmetic).

## 7. Guardrails (never)
Push PEEP up just for compliance (ART) · permissive mode without a raised-ICP gate · uncited clinical numbers · patient data in git or to Claude · claim a survival benefit (only association).

## 8. Re-entry checklist
1) `CLAUDE.md` (goal + rules) → 2) this file → 3) `docs/_Current_Task.md` → 4) act → 5) at task end refresh this file + `_Task_History.md`, commit, push.
