# Research Agenda — Phase 1 (Model Accuracy)

**Principle: let the data decide, don't guess.** The optimizer already runs; what we don't know is whether its *predictions are true*. Phase 1 measures that, then fixes the weakest links. The headline deliverable is a **validation report**.

---

## The open accuracy questions (ranked by likely impact)

### Q1 — Is "linear compliance" good enough?  `[biggest risk]`
- **We assume:** one fixed compliance across all pressures.
- **Why it may be wrong:** real pressure–volume curves bend (lower/upper inflection points); a single line can mis-predict plateau pressure and therefore MP.
- **Test:** on MIMIC cases, compare predicted Pplat (from baseline compliance) vs actually-charted Pplat at different settings. Measure the error.
- **Fix if wrong:** piecewise/nonlinear compliance from the patient's own data points.
- **MEASURED (demo, 2026-06-20):** within-patient compliance varies **~19% median**; plateau-prediction **MAE 3.05 cmH₂O** (1,056 changes). → confirmed weak; Track-C fix #1.

### Q2 — Is the recruitment formula defensible?
- **We assume:** `C_new = C × (1 + (R/I − 0.5)×0.1×ΔPEEP)` — the `0.1` is invented.
- **Test:** find cases with PEEP changes; see whether compliance actually moved the way the formula predicts.
- **Fix if wrong:** replace the heuristic with a data-derived or published relationship; cite it.
- **MEASURED (demo, 2026-06-20):** plateau-prediction error concentrates in PEEP changes — **MAE 4.80 cmH₂O for PEEP changes vs 2.68 for VT-only.** Recruitment is real and the current model ignores it when PEEP moves. → now the #1 Track-C fix (was Q1). Next: characterize compliance-vs-PEEP from data.
- **RESULT (demo, 2026-06-20):** a data-learned PEEP-aware compliance `C×(1+β·ΔPEEP)`, **β≈0.083/cmH₂O**, **cut PEEP-change plateau error 28%** (4.48→3.21) on held-out test patients. Measured recruitment: **+40%** (PEEP↑) / **−23%** (PEEP↓). The prototype's guessed ×0.1 was close. → implement in `physiology.py` after full-MIMIC confirmation (Phase 2).

### Q3 — Are the CO₂ / pH predictions accurate?
- **We assume:** dead space = 2.2 mL/kg; CO₂ scales inversely with alveolar ventilation.
- **Test:** predict PaCO₂/pH after a settings change vs the next ABG in MIMIC.
- **Fix if wrong:** better dead-space estimate; consider **EtCO₂ as a real-time proxy** (solves the "ABG lag" problem).
- **LITERATURE (2026-06-20):** the inverse CO₂↔alveolar-ventilation rule is standard physiology (valid). But our **anatomic 2.2 mL/kg dead space badly underestimates physiological dead space** (ARDS Vd/Vt 0.5–0.7; Nuckton NEJM 2002) → likely the main CO₂/pH error. Fix = ventilatory-ratio-based physiological dead space. See `_Literature_Validation` T9.
- **Candidate fixes (papers, 2026-06-20):**
  1. **Ventilatory Ratio (VR)** = (measured minute ventilation × PaCO₂) ÷ (PBW×100 × 37.5). Needs only VT, RR, PaCO₂, PBW — all in MIMIC. Validated, mortality-predictive (Sinha). ★ simplest.
  2. **Harris–Benedict estimated VD/VT** (Beitler, Crit Care Med 2015): estimate CO₂ production from the Harris–Benedict energy equation, back-out VD/VT via the Enghoff–Bohr rearrangement. **Unbiased** (0.59 vs 0.60 measured; within ±0.10 in 70%). Needs age/sex/weight/PaCO₂/minute-ventilation — all available. ★ best accuracy; gives a directly-usable fraction.
  3. **EtCO₂ alveolar dead-space fraction** AVDSf = (PaCO₂ − EtCO₂) ÷ PaCO₂ (or Frankenfield eq.). Captures alveolar dead space **and is real-time** (also tackles the ABG-lag goal) — but EtCO₂ is sparse in MIMIC (demo: 202 rows). Partial-coverage add-on.
- **Accuracy hierarchy (2026-06-20):**
  - **Most accurate = direct measurement (volumetric capnography / Bohr dead space).** NOT in MIMIC → unavailable retrospectively; the true accuracy ceiling needs a dataset that records it (prospective/Vcap). Note the Enghoff/PaCO₂ version conflates shunt, so it's a gas-exchange index, not pure dead space.
  - **Among feasible (routine-data) estimates the literature is MIXED** — HB was unbiased in one study but *not* mortality-linked in another; VR tracked outcomes better in some. → no clear winner; let **our** data pick.
  - ★ **Best feasible route for OUR goal (predicting the next CO₂): learn each patient's *effective* dead space from their own data** — same trick as the PEEP-aware compliance: fit the dead space that makes the patient's own CO₂↔ventilation changes consistent. Likely beats any population equation for prediction.
- **Plan:** head-to-head CO₂/pH shadow test on held-out patients — **(a)** fixed 2.2 mL/kg (baseline) vs **(b)** HB-estimated VD/VT vs **(c)** per-patient learned dead space — keep whichever predicts best. Same method as the PEEP win.
- **RESULT (demo, 2026-06-20):** HB tested vs fixed on 164 VT-change ABG pairs — **HB was worse** (MAE 33.6 vs 14.4 mmHg): its high dead space amplifies CO₂ sensitivity, the resting-VCO₂ estimate is off in ICU patients, and CO₂ prediction over hours breaks steady state. HB kept but **opt-in** (`use_hb`); manual override always wins. → next = **(c) per-patient learned dead space**.

### Q4 — Are the safety limits the right ones?
- Plateau ≤30, VT 4–8 mL/kg are well-cited. **Driving pressure** (Amato) is *not yet* an explicit objective/limit — should it be? The manuscript shows MP harm with no safe floor, so should the score weight driving pressure too?
- **Action:** decide whether the objective becomes "minimize MP **and** driving pressure," and add citations for the pH floors.

### Q5 — Permissive-hypercapnia floor citation
- Document the real source for pH 7.30 / 7.20 cutoffs (currently uncited).

---

## ⭐ The PEEP problem — the genuinely hard core (Ahmed's insight, 2026-06-20)
**Ahmed (from his own work):** PEEP response is **heterogeneous and individual** — higher PEEP *lowers* mechanical power in some patients and *raises* it in others. The R/I (recruitment-to-inflation) index isn't enough because (1) it must be **measured by a bedside maneuver** — inconvenient for practitioner and patient; and (2) even when it says "recruitable," it does **not** tell you **how much** PEEP to add.

**This matches our data + the literature:** our demo showed exactly this heterogeneity (compliance +40% PEEP↑ in some, −23% PEEP↓ in others); the population slope β≈0.083 we fit is just an *average* that fits no individual well. Literature: no bedside method cleanly predicts individual recruitability — EIT, esophageal/transpulmonary pressure, and respiratory-mechanics methods give *different* "optimal" PEEPs and none tracked recruitability well (Ann Intensive Care 2024). ART (JAMA 2017): getting PEEP wrong kills.

**Design options (pick a direction):**
- **A — PEEP humility (default, safest):** optimize the knobs we predict *well* (VT, RR → plateau MAE 2.68) and **hold PEEP** at the clinician/guideline value; don't recommend PEEP moves the model can't stand behind. **Drops the need for R/I entirely.**
- **B — Learn the patient's OWN PEEP response from their charted history** (no maneuver; gives a per-patient magnitude, not just yes/no). Falls back to A when there's no PEEP history.
- **C — Closed-loop test-step:** suggest a *small reversible* PEEP step, read the *actual* MP/compliance response, then decide — test instead of predict.
- **D — (future/clinical):** EIT or esophageal pressure for direct individual response (needs special equipment; not in MIMIC).
- **E — Transpulmonary-pressure target (Ahmed's idea, 2026-09-27):** titrate PEEP to a real **dose target** — end-expiratory transpulmonary pressure ≈ 0 cmH₂O (lung held open without over-stretch). **This answers the "how much PEEP" question R/I couldn't.**
  - **Evidence:** EPVent-1 (Talmor, NEJM 2008) improved oxygenation/compliance; **EPVent-2 (Beitler, JAMA 2019, n≈200) found NO mortality or ventilator-free-day benefit** vs an empirical high-PEEP/FiO₂ table 🟥 (the definitive RCT was negative). Post-hoc reanalysis (AJRCCM 2021): mortality was **lowest when PEEP achieved transpulmonary ≈ 0**, and the strategy helped less-sick patients (APACHE-II < median, HR 0.43) but may have harmed sicker ones. → the *principle* (target ≈ 0) is sound; the balloon strategy isn't proven superior, and effect depends on severity.
  - **The "limited data" catch + the lead:** standard transpulmonary needs an **esophageal balloon** (more equipment, not less — and NOT in MIMIC). BUT emerging work suggests **central venous pressure (CVP) swings** can surrogate pleural pressure (filtered CVP ≈ esophageal-pressure swings; J Clin Monit Comput 2024) — and **CVP is routinely charted (likely in MIMIC)**. So a **no-balloon, CVP-based estimate** could be the "limited-data" route Ahmed is after. `[low-strength — one small study]`
  - **Why attractive for us:** gives a PEEP *dose*; the CVP surrogate needs no maneuver and no balloon; and — unlike R/I — CVP is *passively* recorded, so it could be **validated on MIMIC** when we return to PEEP.
  - **Status:** recorded (PEEP still parked). **CVP feasibility check (demo, 2026-09-27):** CVP IS present (itemid **220074**, ~39/100 stays, ~1,600 rows incl. alarm-limit itemids) — BUT charted as **spot values (hourly), not the beat-to-beat waveform.** The pleural-pressure surrogate needs the respiratory *swing* in CVP → the rigorous version likely needs the separate **MIMIC-IV Waveform** database, not the clinical tables. **Fallback to test:** a coarser **PEEP-transmission** proxy (how spot CVP shifts when PEEP changes) — spot data *can* give that.
  - **No-balloon alternatives that need NO CVP and work with OUR data (2026-09-27):**
    1. **Elastance-ratio method** — transpulmonary ≈ airway pressure × (E_L/E_rs), population ratio **≈ 0.70**; so transpulmonary *driving* pressure ≈ (Pplat−PEEP) × 0.7 (safe airway ΔP < 15 ↔ transpulmonary ΔP < 10). **Computable now from Pplat/PEEP/VT — no balloon, no CVP.** `[Q1: Crit Care 2023; ATM]` Caveat: population average, over-estimates overdistension in obesity; gives lung **stress** (overdistension side), NOT the absolute end-expiratory *collapse* target.
    2. **PEEP-step method** (Stenqvist/Lundin) — partition lung vs chest-wall elastance from the pressure response to a PEEP change; we already have **183 PEEP changes** in the demo to try it on. Balloon-free.
    - Honest limit: the **absolute end-expiratory transpulmonary** (EPVent's collapse/"how-much-PEEP" target) still needs an absolute pleural reference (balloon or CVP). The elastance methods give the overdistension/upper-limit side.
  - **Databases with vent + CVP + mortality:** **MIMIC-IV already has all three** (vent + spot CVP 220074 + mortality) — and a paper already linked CVP + ventilation + mortality in MIMIC-IV (*Crit Care Med 2022*). Higher-resolution CVP (toward the swing): **HiRID** (2-min resolution) or the **MIMIC-IV Waveform** DB; **AmsterdamUMCdb** / **eICU** also qualify. → **no new database strictly needed** for the spot-CVP / elastance work.
- **Standing rule:** never push PEEP up just to chase compliance (ART). See `_Literature_Validation` T7.

**Decision (2026-09-27): UN-PARKED — this IS the core goal** (see CLAUDE.md → THE CORE GOAL). The project can't proceed without it. Two sub-problems, **math-only on pre-recorded data**: **(1) choose the highest SAFE PEEP** (recruit without overdistension), **(2) predict the PEEP→compliance change** to compute Mechanical Power. Options above (esp. E + the elastance methods) feed this.

**Required math inputs — a dataset MUST have all of these:** per ventilated timepoint — VT, RR, PEEP, plateau pressure (Pplat), peak pressure; **paired PEEP changes** with Pplat (the compliance response); oxygenation (PaO₂/FiO₂ or SpO₂/FiO₂); demographics (age/sex/height/weight → PBW); mortality/outcome (to validate). **Gap:** an *absolute* pleural/transpulmonary reference for the *collapse* target (CVP swing/waveform or esophageal) — MIMIC clinical has only **spot** CVP. **MIMIC-IV covers everything except that high-resolution pleural signal**; the elastance-ratio method (`(Pplat−PEEP)×0.7`) gives the overdistension side with no extra data.

## The validation loop (the Phase 1 engine of progress)
1. **Shadow test:** pull real ventilated MIMIC-IV patients (`validate_mimic.py`).
2. For each, feed their state into `physiology.predict()`.
3. Compare **predicted vs observed** (Pplat, MP, pH) → error tables per Q above.
4. Optionally: compare the optimizer's *suggested* setting vs the clinician's *actual* setting vs the *outcome* — does lower-MP advice track with better outcomes? (echoes the manuscript).
5. Fix the worst-predicting block, re-test, repeat.

## Exit criteria for Phase 1
- A short **validation report**: prediction error for Pplat, MP, pH on a real cohort.
- A **prioritized fix list** (which assumption to replace first, with evidence).
- Every previously-uncited number either cited or explicitly flagged `[ASSUMPTION]`.

## Parked ideas (not now)
- EtCO₂ real-time integration · nonlinear P–V curve mapping from hold maneuvers · prospective comparison.
