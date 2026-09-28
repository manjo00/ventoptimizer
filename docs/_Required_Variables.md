# Required Variables — what the PEEP math needs, and whether MIMIC-IV has it

**Status:** step 1 of THE CORE GOAL — **done 2026-09-28** on the open demo; full-MIMIC numbers pending Ahmed's local run.
**Rule (CLAUDE.md):** a dataset must carry *every* input the math needs, confirmed *before* we commit to it. This file is the human list; `engine/check_coverage.py` is the same list in code and the re-runnable check:
```bash
python engine/check_coverage.py --mimic data/mimic-iv-clinical-database-demo-2.2
```
Keep the two in sync (the `VARIABLES` table at the top of the script mirrors §2 here).

---

## 0. Verdict in one paragraph
**MIMIC-IV carries every input the PEEP math needs** — mechanics, gases, oxygenation, hemodynamics, gates, demographics, timing and outcomes — with one true gap: an **absolute pleural-pressure reference** for the "collapse side" of PEEP. Even that gap is partial: MIMIC-IV charts **esophageal-derived transpulmonary pressure** (codes 224746/224747) in a small subset (**2 of 67** ventilated demo stays, ≈3%; likely ~1,000 stays in full MIMIC-IV), which becomes the natural *validation subset* for any no-balloon estimate. → **MIMIC-IV is confirmed as the prototype dataset.** Three practical limits shape the work: **(1)** plateau pressure is charted at ~1 vent check in 3 and only ~half of ventilated time is in controlled modes, so only **~15% of PEEP changes are trustworthy before/after pairs** (28 of 183 in the demo — thousands in full MIMIC); **(2)** height (→ predicted body weight) is missing at the bedside in ~30% of ventilated stays (~12% after the outpatient fallback); **(3)** an arterial gas sits within ±2 h of only ~12% of PEEP changes, so oxygenation response will lean on SpO₂/FiO₂ (available around 99%/93% of changes).

**⚠ Side-finding that changes earlier results:** our validation harness forward-fills the plateau in time. After a PEEP change, a carried plateau is a number measured at the *old* PEEP; treating it as the "after" measurement **manufactures a compliance change in exactly the direction we reported**. Only **13%** of the 183 demo PEEP events had a plateau actually charted at the change row. → the recruitment slope β≈0.083, the "+40% / −23%" compliance shifts, the 28% prediction gain, and possibly the "PEEP changes are the crux (MAE 4.80)" split are **SUSPECT until re-run on usable pairs** (§3). Logged in `_Research_Log.md`; re-run is the next task.

---

## 1. The math — and the inputs each equation consumes
Plain-language reminder of terms: **VT** tidal volume (breath size) · **RR** breaths per minute · **PEEP** pressure kept in the lung between breaths · **Pplat** plateau pressure (pressure inside the lung at end-inspiration, measured with a brief hold) · **Ppeak** highest airway pressure in the breath · **Crs** compliance (how much volume you get per unit pressure = "stretchiness") · **ΔP** driving pressure (Pplat − PEEP) · **MP** mechanical power (energy the ventilator delivers per minute).

### 1a. Mechanics at one timepoint (only valid in a passive, controlled breath)
```
Crs (mL/cmH₂O) = VT ÷ (Pplat − PEEP_total)          PEEP_total = set PEEP + auto-PEEP
ΔP (cmH₂O)     = Pplat − PEEP_total
auto-PEEP      = Total PEEP (224700) − PEEP set (220339)      [0 when total PEEP is not charted — ASSUMPTION]
```
`[STANDARD; _Clinical_Logic §2; ΔP: E4]`
**Inputs:** VT observed · Pplat · PEEP set · (Total PEEP) · **validity inputs:** ventilator mode ∈ controlled, spontaneous RR = 0 (or a neuromuscular-blocker infusion), not APRV.

### 1b. Mechanical power — absolute, and the *tidal* part we optimize
```
MP_abs (J/min) = 0.098 × RR × VT(L) × [ Ppeak − ½ (Pplat − PEEP) ]                 [E1]
               = 0.098 × RR × VT(L) × [ PEEP  +  (Ppeak − Pplat)  +  ½ ΔP ]        (same thing, split into parts)
                                        static     resistive        tidal-elastic
MP_tidal (J/min) = 0.098 × RR × VT(L) × ½ ΔP  =  0.098 × RR × VT² ÷ (2 × Crs)     ← the LOCKED objective (2026-09-27)
```
The split is pure algebra on `[E1]`: `Ppeak − ½(Pplat − PEEP) = PEEP + (Ppeak − Pplat) + ½(Pplat − PEEP)`. The **static** part rises with PEEP no matter what the lung does; the **tidal-elastic** part is the "∝ RR × VT²/compliance" term that recruitment lowers. We minimize and compare by **MP_tidal**, and report **MP_abs** alongside (CLAUDE.md → objective caveat). Whether the resistive part joins the objective is a build-time detail — it needs no extra inputs.
**Inputs:** RR · VT · Pplat · PEEP · Ppeak (Ppeak only for MP_abs).

### 1c. Predicting compliance after a PEEP change (sub-problem 2)
```
population rule (current, SUSPECT — see §3):  Crs_new = Crs_old × (1 + β × ΔPEEP)
per-patient rule (target):                    the patient's OWN slope from ≥ 2 PEEP levels, each with a plateau measured AT that PEEP
```
A **usable PEEP-step pair** is the derived variable everything rests on: *same stay · PEEP_old with a plateau measured while PEEP_old was in force · PEEP_new with a plateau charted within ≤ 4 h at PEEP_new · controlled mode on both sides · VT known on both sides.*
**Candidate recruitability inputs** (which recorded values might predict *how much* compliance moves; evidence `[N6]`, direction still `[ASSUMPTION]` outside CT-defined ARDS): baseline P/F (PaO₂/FiO₂, or SpO₂/FiO₂ `[E7]`), PaCO₂ (dead-space burden), baseline Crs, BMI (chest wall; needs height + weight), days on the ventilator (from ventilation episodes), ARDS diagnosis code (optional stratifier — only 1 coded admission in the demo).
**Response checks after a step** (was the change good?): Δ(SpO₂/FiO₂) · ΔPaCO₂ at unchanged minute ventilation (a rise = dead space ↑ = overdistension signal) · ΔMAP / vasopressor change.

### 1d. Choosing the highest SAFE PEEP (sub-problem 1)
- **Ceilings (overdistension side):** Pplat ≤ 30 `[E3]`; ΔP ceiling (`_Research_Agenda` uses < 15 from `[E4]`/the Q1 elastance paper — **formally cite in `_Evidence_Base` before it enters code** `[TO-CITE]`); lung *stress* via the elastance-ratio method ≈ ΔP × 0.7 (`_Research_Agenda`; population ratio → `[ASSUMPTION]` for an individual); **data signals of overdistension:** Crs falls at the higher PEEP (PEEP-step), PaCO₂ rises at unchanged VE, MAP falls / pressors rise.
- **Conventional envelope:** the ARDSNet lower-PEEP `[E3]` and ALVEOLI higher-PEEP `[N7]` PEEP/FiO₂ tables bound the *usual* PEEP for a given FiO₂ — a sanity range, not a target.
- **Floors (oxygenation):** ARDSNet targets SpO₂ 88–95% / PaO₂ 55–80 mmHg `[E3]`.
- **Gates:** raised ICP (`_Literature_Validation` T10 — no permissive hypercapnia; PEEP caution) · chest tube / air leak `[clinical convention — ASSUMPTION]` · hemodynamic instability (MAP, vasopressor dose — **thresholds `[TO-CITE]`**, `[N-hemo note in _Evidence_Base]`) · spontaneous effort (RR spont > 0 → mechanics invalid) · auto-PEEP → the 3τ rule `[E5]`.
- **Collapse side (the "how much PEEP" target ≈ end-expiratory transpulmonary 0, EPVent):** needs a pleural reference → only in the **transpulmonary subset** (224746/224747) or via **spot-CVP** proxies (49% of stays; low-strength). Everything else on the collapse side is inference from the response checks above.

### 1e. Pairing, timing, cohort
`stay_id` + `charttime` for every reading · **ventilation episodes** (`procedureevents` 225792 start/end → time on vent, ventilator-free days) · **mode text** to keep controlled breaths · labs attached to a stay by admission id + time inside the stay window.

### 1f. Patient descriptors
```
PBW (kg) = 50 + 0.91 × (height_cm − 152.4)   male        45.5 + 0.91 × (height_cm − 152.4)   female     [E3, ARDSNet protocol]
BMI      = weight_kg ÷ height_m²
```
**Inputs:** height (bedside, or outpatient `omr` fallback), sex, age, weight.

### 1g. Outcomes — for *validation only*, never an input to the math
In-hospital death (`admissions.hospital_expire_flag`), date of death (`patients.dod` → 28-day mortality from ICU admission), ventilator-free days (from episodes).

---

## 2. The master list (tiered) — with demo coverage
**Tier:** **REQUIRED** = the math cannot run without it · **RECOMMENDED** = safer/more accurate, has a fallback · **OPTIONAL** = cross-check or rare-but-valuable. **Coverage** = readings / ventilated stays with ≥ 1 reading (share of the **67 ventilated stays** in the demo). Codes are in `_Data_Dictionary.md`.

| Group | Variable | Feeds | Codes | Tier | Demo coverage | Fallback if missing |
|---|---|---|---|---|---|---|
| A | Tidal volume (observed) | Crs, ΔP, MP | 224685 | REQUIRED | 1,331 / 67 (100%) | set VT 224684 (93%) |
| A | PEEP (set) | Crs, ΔP, MP, the PEEP axis | 220339 | REQUIRED | 1,447 / 67 (100%) | — |
| A | Plateau pressure | Crs, ΔP, ceilings | 224696 | REQUIRED | 510 / 56 (**84%**) | none — stays without it drop out of mechanics |
| A | Peak pressure | MP_abs (resistive) | 224695 | REQUIRED | 1,319 / 66 (99%) | MP_tidal needs no Ppeak |
| A | Respiratory rate | MP, VE | 220210 (vital) / 224690 (vent) | REQUIRED | 100% / 100% | — |
| A | Ventilator mode (text) | controlled-breath filter; VC vs PC formula | 223849 / 229314 | REQUIRED | 100% | — |
| A | Total PEEP | auto-PEEP, true ΔP | 224700 | RECOMMENDED | 490 / 55 (82%) | assume auto-PEEP = 0 `[ASSUMPTION]` |
| A | RR spontaneous / RR set | passivity check | 224689 / 224688 | RECOMMENDED | 99% / 94% | mode text + NMB |
| A | Inspiratory time · I:E · flow | Te, resistance → τ | 224738 · 226873/226871 · 224691 | OPTIONAL | 97% · 75% · 28% | Ti = 1 s `[ASSUMPTION, E5]` |
| A | Minute volume · mean airway P | cross-checks | 224687 · 224697 | OPTIONAL | 100% · 100% | computed |
| A | PSV level · APRV P-high/low | mode flags | 224701 · 224705/224706 | OPTIONAL | 88% · 5% | mode text |
| A | Vent-computed compliance / resistance / auto-PEEP | cross-checks | 229661 · 220283/229665/229664 · 224699 | OPTIONAL | 0% in demo | our own Crs |
| A | **Transpulmonary pressure (esophageal-derived)** | the pleural reference (collapse target) | 224746 / 224747 | OPTIONAL★ | 26 / 2 (**3%**) | elastance ratio (stress side only); CVP proxy |
| B | FiO₂ | P/F, S/F, PEEP/FiO₂ envelope | 223835 | REQUIRED | 1,660 / 67 (100%) | — |
| B | SpO₂ | oxygenation response (hourly) | 220277 | REQUIRED | 9,815 / 67 (100%) | — |
| B | PaCO₂ · pH (chart ABG) | CO₂ lever, pH floor, dead-space signal | 220235 · 223830 | REQUIRED | 567 / 58 (**87%**) | lab ABG 50818 / 50820 (94%) |
| B | PaO₂ (chart ABG) | P/F, recruitability | 220224 | RECOMMENDED | 567 / 58 (87%) | SpO₂/FiO₂ `[E7]` |
| B | HCO₃ (TCO₂ / serum / lab) | Henderson–Hasselbalch | 225698 · 227443 · 50882 | RECOMMENDED | 87% · 99% · 97% | any of the three |
| B | Lab ABG panel (+ vent fields at gas time) | second timed gas source | 50820/50818/50821/50804/50802 (+50819/50826/50827) | RECOMMENDED | 3,336 / 63 (94%) (+42%) | chart ABG |
| B | EtCO₂ · SaO₂ · lactate | dead-space fraction · cross-check · perfusion | 228640 · 220227 · 50813 | OPTIONAL | 19% · 46% · 90% | — |
| C | Mean BP (invasive / cuff) | hemodynamic guard for PEEP steps | 220052 / 220181 | RECOMMENDED | 67% / 99% | either |
| C | Vasopressor infusions | instability gate | 221906 221749 222315 221289 221662 221653 | RECOMMENDED | 42 stays (63%) | absence = none charted |
| C | Spot CVP | PEEP-transmission / pleural proxy | 220074 | RECOMMENDED | 33 / 67 (49%) | none |
| C | Heart rate | guard | 220045 | OPTIONAL | 100% | — |
| D | Intracranial pressure | raised-ICP gate | 220765 / 227989 | REQUIRED *when present* | 2 stays (3%) | absence = no monitor = gate not triggered |
| D | Chest tube (output / site / placed) | air-leak gate | 226588 226589 · 223993 224438 · 225433 | RECOMMENDED | 24 stays (36%) | absence = none |
| D | Neuromuscular-blocker infusion | guarantees passive mechanics | 221555 / 222062 | RECOMMENDED | 0 in demo (codes exist) | RR spont = 0 + controlled mode |
| E | Height | PBW → VT/kg limits | 226730 / 226707 | REQUIRED | 48 / 67 (**72%**) | outpatient `omr` height → **88%**; else exclude/flag |
| E | Sex · age | PBW formula | `patients` | REQUIRED | 100% | — |
| E | Weight | BMI (chest wall) | 226512 / 224639 | RECOMMENDED | 99% | `omr` weight |
| F | Invasive-ventilation episodes | time on vent, VFDs, cohort | 225792 | REQUIRED | 60 / 67 (**90%**) | infer from first/last vent setting |
| F | Intubation / extubation events | episode boundaries | 224385 / 227194 | OPTIONAL | 75% | episodes |
| G | Mortality (hospital flag, date of death) | validation outcome | `admissions`, `patients` | REQUIRED (validation) | 100% (14 deaths = 20.9%) | — |

---

## 3. Feasibility of the actual PEEP math (demo numbers)
| What the math needs | Demo count | Comment |
|---|---|---|
| Snapshots with VT + PEEP + Pplat (compliance computable) | **8,040** in 56 stays | but only **495** carry a *freshly charted* plateau; **3,539** are in a controlled mode |
| PEEP-change events with a plateau on both sides (the old "183") | **183** in 37 stays (82 up / 101 down) | as defined by exp2/exp3 |
| … 'before' plateau measured under the OLD PEEP | 88 (48%) | the other half carried a plateau from an even earlier PEEP |
| … 'after' plateau charted **at the change row** | **24 (13%)** | ← what exp2/exp3 silently used as the observation |
| … 'after' plateau charted within 4 h at the NEW PEEP | 44 (24%) | the honest "after" measurement |
| **Usable pairs** (before valid AND fresh after ≤ 4 h) | **30 (16%)** | |
| **Usable AND controlled mode both sides** | **28 (15%)** | **the trustworthy set for sub-problem 2** |
| Stays with ≥ 2 PEEP levels (own slope possible) | 37 (≥ 3 levels: 19) | fresh-plateau only: **17** (≥ 3: 5) |
| Events with an arterial gas ± 2 h before AND after | 22 (12%) | CO₂-response checks will be sparse |
| Events with SpO₂ ± 1 h before AND after | 182 (99%) | oxygenation response = SpO₂/FiO₂ `[E7]` |
| Events with FiO₂ within ± 4 h | 170 (93%) | FiO₂ is a setting → forward-fill is legitimate |
| Events with a mean BP ± 1 h before AND after | 172 (94%) | hemodynamic guard feasible |
| Stays with esophageal-derived transpulmonary pressure | 2 | validation subset (full MIMIC ≈ ×500) |
| Stays with spot CVP | 39 (33 ventilated) | coarse PEEP-transmission proxy only |
| Mode rows in a controlled mode | ≈ 50% | half of ventilated time is support/spontaneous |

**Scale-up expectation:** full MIMIC-IV has ~500× the demo's ICU stays → on the order of **10,000+ usable pairs**, hundreds of transpulmonary-pressure stays. Ahmed confirms by running the script locally.

---

## 4. Gaps and fallbacks (honest list)
1. **Absolute pleural reference** (collapse-side PEEP target) — *gap.* Fallbacks: elastance-ratio stress (upper bound only) · the transpulmonary-pressure subset as a validation set · spot-CVP PEEP-transmission proxy `[low-strength]`. Waveform-level CVP would need MIMIC-IV Waveform / HiRID — not needed for the prototype.
2. **Plateau sparsity + support modes** → only ~15% of PEEP changes are trustworthy pairs. Not fixable — it is the honest denominator; full MIMIC makes it large enough.
3. **Height missing** in ~30% (bedside) / ~12% (after `omr`) of ventilated stays → no PBW → those stays are excluded from VT/kg logic (or flagged).
4. **Arterial-gas timing** — gases sit near only ~12% of PEEP changes → CO₂ response is a small-sample check; oxygenation uses SpO₂/FiO₂ `[E7]`.
5. **Direct recruitability measures** (R/I index, EIT, CT, stress index) — in no routine dataset → replaced by the patient's own PEEP-step response (usable pairs) plus candidate predictors `[N6]`.
6. **Neuromuscular blockers** 0% in the demo (codes exist) → passivity comes from mode + RR spont in the demo; full MIMIC will have infusions.
7. **Ventilator-computed compliance / resistance** 0% in the demo → we compute our own.
8. **Docs-vs-code MP formula mismatch** (noticed, not fixed): `_Evidence_Base`/`_Clinical_Logic` print the manuscript's peak-only surrogate `Ppeak − ½(Ppeak − PEEP)`, while the engine uses `Ppeak − ½(Pplat − PEEP)` when Pplat is known. Decide one, cite it, align — logged in `_Current_Task` → Noticed.

---

## 5. Decision and next steps
- **Dataset:** **MIMIC-IV (clinical tables) confirmed** as the prototype dataset. AmsterdamUMCdb stays an optional second dataset later (vent + CVP + mortality present per `_Research_Agenda`).
- **Next (top priority, blocks sub-problem 2):** re-run exp2/exp3 in `validate_mimic.py` on **usable pairs only** (plateau charted at the new PEEP ≤ 4 h, controlled mode both sides, 'before' plateau measured under the old PEEP). Re-derive β, the up/down compliance shifts, and the prediction gain honestly; also re-check the VT-only vs PEEP-change error split.
- Then: prototype sub-problem 2 on usable pairs → per-patient slope where ≥ 2 fresh levels exist; then sub-problem 1 (ceilings + oxygenation + gates).
- **Ahmed:** run `check_coverage.py` on full MIMIC-IV; paste the printed output (aggregate only — the `--csv` file is per-variable counts, safe to share; never patient rows).

## 6. How to re-run and what to paste back
```bash
python engine/check_coverage.py --mimic <path to MIMIC-IV folder with icu/ and hosp/> --csv coverage_full.csv
```
Reads the big tables in chunks (safe on the full data; expect tens of minutes). Paste the **whole printed output**. If the script prints "mode strings not yet classified", paste those too so the controlled-mode list can be extended.
