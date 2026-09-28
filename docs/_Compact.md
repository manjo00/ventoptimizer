# _Compact.md — the whole project state on one page
**Read this FIRST after any `/compact`, resume, or new session (then `_Current_Task.md`). Keep it ≤ ~1 page. Refresh it at the end of EVERY task (with `_Task_History.md`).**
Last refreshed: 2026-09-28 (after core-goal step 1)

## 📋 Repeatable prompts (copy-paste)
- **Before compacting (refresh the state):** `Refresh docs/_Compact.md with everything from this session, then commit + push.`
- **To compact:** `/compact Read docs/_Compact.md — it is the authoritative project state. Keep this summary consistent with it and preserve the CORE GOAL, locked decisions, key numbers, next steps and open items.`
- **To resume (any new session):** `Read CLAUDE.md, then docs/_Compact.md, then docs/_Current_Task.md, and continue from "Where we are / next".`

## 1. What this is
**VentOptimizer** — a decision-support **prototype** (not a medical device) that recommends ventilator settings minimizing mechanical power within safety limits, for **all** ventilated patients (not ARDS-only). **Math-only, on pre-recorded data.** Python engine (`engine/`) = source of truth; `app/ventoptimizer.html` = front-end demo. Repo: `manjo00/ventoptimizer` (main). Owner: Ahmed (RT student, not a coder → teaching mode).

## 2. THE CORE GOAL (locked)
Solve **PEEP** via math on recorded data: **(1) choose the highest SAFE PEEP** (recruit without overdistension); **(2) predict the PEEP→compliance change → compute the resulting mechanical power.** A dataset must carry every math input. Live-patient testing = possible future only.

## 3. Locked decisions
- **Objective metric:** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098×RR×VT×½(Pplat−PEEP)` = the tidal-elastic part of Gattinoni's MP (`_Required_Variables` §1b); report absolute MP alongside. **Never compare by absolute MP** (it rises ~+1 J/min per cmH₂O PEEP → would derecruit).
- **Corrected hypothesis:** in recruitable lungs, PEEP up to an optimum ↑compliance and ↓tidal/per-unit power, though absolute power rises; past the optimum both worsen (U-shaped).
- **Dataset: MIMIC-IV confirmed (2026-09-28)** — every required input present; only gap = absolute pleural reference (partly covered: esophageal-derived transpulmonary pressure charted in ~3% of stays = validation subset). AmsterdamUMCdb optional later.
- **Evidence rule:** every clinical number cited; prefer Q1 journals; label strength (RCT > observational > our data). *Association ≠ intervention. Prediction ≠ clinical titration* (ART trial: compliance-titrated PEEP ↑mortality).
- **Data governance:** credentialed data never to Claude; local-only loop; aggregates only; never commit patient data.
- **Data-handling rule (new):** never carry a measured value (plateau) across a setting change it wasn't measured under — forward-fill only while settings are unchanged.
- **Overrides:** measured dead space always wins; practitioner-set pH/CO₂ limit (stricter of manual vs evidence floor). HB dead space is **opt-in** (`use_hb`) — it worsened CO₂ prediction.
- Git checkpoint + **push after every task**.

## 4. Key findings (demo = open MIMIC-IV, 100 pts / 140 ICU stays / 67 ventilated)
- **Coverage (share of ventilated stays):** VT/PEEP/RR/mode/FiO₂/SpO₂ 100%, Ppeak 99%, **Pplat 84%**, chart gases 87% (lab ABG 94%), **height 72% → 88%** with outpatient `omr`, vent episodes 90%, MAP 99% (cuff), CVP 49%, vasopressors 63%, ICP 3%, transpulmonary pressure 3% (2 stays). Modes ≈50% controlled.
- **Feasibility:** 8,040 compliance snapshots but only 495 with a fresh plateau; 183 PEEP-change events → **only 24 (13%) had a plateau charted at the change; 28 (15%) are trustworthy pairs** (fresh ≤4 h at new PEEP + controlled). 17 stays with ≥2 fresh PEEP levels. Gas ±2 h near events 12%; SpO₂ 99%; FiO₂ 93%; MAP 94%. Full MIMIC ≈ ×500 → ~10k usable pairs.
- **⚠ SUSPECT (stale-plateau artifact, found 2026-09-28):** β≈0.083/cmH₂O, +40%/−23% compliance shifts, the −28% held-out error, and "PEEP changes MAE 4.80 vs VT-only 2.68" — all computed on forward-filled plateaus. Re-run on usable pairs = next task (1b). Compliance varying ~19% within a patient: likely real but re-check.
- MP savable by VT↔RR redistribution ≈ **0** (median 0.1 J/min) → PEEP + permissive hypercapnia are the real levers. HB dead space **worsened** CO₂ prediction (14.4→33.6 mmHg).
- **CVP** spot-only (pleural swing needs waveform data). **No-balloon lung stress:** elastance ratio `(Pplat−PEEP)×0.7`; PEEP-step method.
- Manuscript anchor: OR **1.09**/J·min; quartile survival 89→70%; harm below 17 J/min. Theories T1–T12 graded in `_Literature_Validation.md`.

## 5. Where we are / next
- **Phase 1, centered on PEEP. Step 1 (required variables + dataset) DONE.** Next: **(1b)** re-run exp2/exp3 on usable pairs only (honest β / shifts / gain / error split); **(2)** prototype sub-problem 2 (PEEP→compliance→MP_tidal) on usable pairs, per-patient slope where possible; **(3)** sub-problem 1 (highest safe PEEP) via ceilings + oxygenation + gates.
- PEEP design options A–E in `_Research_Agenda`; full input list + gaps in `_Required_Variables.md`.
- Secondary (after PEEP): permissive-hypercapnia lever, driving pressure as explicit target (Costa: 4× RR), per-patient dead space.
- Noticed, not fixed: MP formula docs-vs-code mismatch (peak-only surrogate vs plateau form); `validate_mimic.py` must switch to chunked reading before a full-MIMIC run; README line stale.

## 6. Open with Ahmed
- **Run `engine/check_coverage.py --mimic <full MIMIC-IV folder>` locally; paste the printed output** (aggregate only).
- Who is PhysioNet-credentialed (runs full-MIMIC locally).
- Pick the paper-title angle (tidal-vs-absolute insight / individualized-PEEP method / no-balloon hook).
- Folder rename `research poster day` → `VentOptimizer` (manual; cosmetic).

## 7. Guardrails (never)
Push PEEP up just for compliance (ART) · permissive mode without a raised-ICP gate · uncited clinical numbers · patient data in git or to Claude · claim a survival benefit (only association) · forward-fill a measurement across the setting change it depends on.

## 8. Re-entry checklist
1) `CLAUDE.md` (goal + rules) → 2) this file → 3) `docs/_Current_Task.md` → 4) act → 5) at task end refresh this file + `_Task_History.md`, commit, push.
