# Current Task — THE CORE GOAL: solve PEEP (math-only, recorded data)

**Date:** 2026-09-28
**Phase:** 1 (centered on the PEEP goal)
**Status:** step 1 DONE → step 1b (re-run on usable pairs) is next

## The goal (see CLAUDE.md → THE CORE GOAL)
The project can't proceed without solving PEEP, **math-only on pre-recorded data**:
1. **Choose the highest SAFE PEEP** — recruit/open the lung without over-stretching it.
2. **Predict how a PEEP change alters COMPLIANCE** → compute the resulting Mechanical Power.
Scope = a prototype on recorded datasets; live-patient testing is a possible future, not now.

**Objective metric (locked 2026-09-27):** minimize **and** compare optimized-vs-baseline by the **tidal / driving-pressure mechanical power** `MP_tidal = 0.098 × RR × VT × ½(Pplat − PEEP)` (breath energy, not the static PEEP baseline); report absolute MP alongside. Never compare by absolute MP. (Derivation: `_Required_Variables.md` §1b.)

## Step 1 — DONE 2026-09-28: required-variable list + dataset coverage
- **Deliverables:** `docs/_Required_Variables.md` (the tiered list, the math each input feeds, gaps/fallbacks, verdict) + `engine/check_coverage.py` (re-runnable, chunked, aggregate-only coverage check for any MIMIC-IV folder). `_Data_Dictionary.md` expanded to all variable groups.
- **Verdict:** **MIMIC-IV confirmed as the prototype dataset.** Every REQUIRED input present (demo: Pplat 84%, gases 87%, height 72%→88% with the `omr` fallback); the only true gap is an absolute pleural reference — and MIMIC even charts esophageal-derived transpulmonary pressure in ~3% of stays (validation subset).
- **⚠ Artifact found:** `validate_mimic.py` forward-fills the plateau; exp2/exp3 used the plateau at the change row, which was actually charted in only **13%** of the 183 PEEP events. A stale plateau at a new PEEP fakes a compliance change in the reported direction. **Only 28 (15%) events are trustworthy pairs** (plateau charted at the new PEEP ≤4 h, controlled mode both sides, valid 'before'). → β≈0.083, +40%/−23%, the 28% gain, and the 4.80-vs-2.68 split are **SUSPECT** (flagged in every doc that quotes them).

## Immediate next steps
1b. **Re-run exp2/exp3 on usable pairs only** (define "usable pair" in `validate_mimic.py` exactly as `check_coverage.peep_change_events` does: 'before' plateau measured under the old PEEP; 'after' plateau charted within ≤4 h at the new PEEP; controlled mode both sides). Re-derive β, the up/down shifts, the held-out gain, and the VT-only vs PEEP-change error split — honestly, whatever they turn out to be.
2. **Prototype sub-problem 2** (PEEP → compliance → MP_tidal) on usable pairs; per-patient slope where ≥2 fresh PEEP levels exist (17 demo stays); candidate predictors per `_Required_Variables` §1c.
3. **Sub-problem 1** (highest safe PEEP): overdistension ceilings (Pplat, ΔP, elastance-ratio stress) + oxygenation floors + gates (ICP, air leak, hemodynamics, effort, auto-PEEP).

## Guardrails
- Compliance-guided PEEP ≈ the **ART** strategy that *increased* mortality → frame as **prediction/prototype**, not clinical titration (`_Literature_Validation` T7). Prefer Q1 evidence; label strength.
- Never push PEEP up just to chase compliance. Permissive mode needs a raised-ICP gate.
- Never carry a measured value (plateau) across a setting change it was not measured under.

## Validated so far (revised 2026-09-28)
- Every theory paper-validated (`_Literature_Validation.md`) — unaffected.
- MP savings from VT↔RR redistribution ≈ **0** → PEEP (+ permissive hypercapnia) are the real levers — unaffected.
- VT-only plateau prediction MAE 2.68 — probably fine (the stale-plateau error is small for VT changes) but re-check in 1b.
- **PEEP-change results (β, ±%, 28%, 4.80) — SUSPECT, pending 1b.**

## Noticed (not fixing now)
1. **MP formula: docs vs code mismatch.** `_Evidence_Base` [E1] and `_Clinical_Logic` §1 print the manuscript's peak-only surrogate `Ppeak − ½(Ppeak − PEEP)`; `physiology.py`, `validate_mimic.py` and the HTML use `Ppeak − ½(Pplat − PEEP)`. Decide one (Gattinoni's plateau form when Pplat is known; the surrogate as fallback), cite it, align all four.
2. `validate_mimic.py` loads the whole `chartevents` table at once — will not fit in memory on full MIMIC-IV. Reuse the chunked `read_filtered` from `check_coverage.py` before Ahmed's full run.
3. `engine/README.md` still calls `validate_mimic.py` "a skeleton with fake demo data" — stale.
4. `_Task_History.md` rows are not in date order (the 2026-09-28 rows sit between 2026-06-20 rows) — cosmetic.

## Secondary (after PEEP)
- Permissive-hypercapnia MP lever (+ manual practitioner pH/CO₂ limit), driving pressure as target, per-patient dead space.

## Open with Ahmed
- **Run the coverage check on full MIMIC-IV** and paste the printed output (aggregate only): `python engine/check_coverage.py --mimic <folder> --csv coverage_full.csv`.
- After 1b + chunking: run `validate_mimic.py` on full MIMIC-IV locally; paste aggregates.
- Pick the paper-title angle; folder rename (cosmetic).
