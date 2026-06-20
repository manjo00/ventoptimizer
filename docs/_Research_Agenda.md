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

### Q3 — Are the CO₂ / pH predictions accurate?
- **We assume:** dead space = 2.2 mL/kg; CO₂ scales inversely with alveolar ventilation.
- **Test:** predict PaCO₂/pH after a settings change vs the next ABG in MIMIC.
- **Fix if wrong:** better dead-space estimate; consider **EtCO₂ as a real-time proxy** (solves the "ABG lag" problem).

### Q4 — Are the safety limits the right ones?
- Plateau ≤30, VT 4–8 mL/kg are well-cited. **Driving pressure** (Amato) is *not yet* an explicit objective/limit — should it be? The manuscript shows MP harm with no safe floor, so should the score weight driving pressure too?
- **Action:** decide whether the objective becomes "minimize MP **and** driving pressure," and add citations for the pH floors.

### Q5 — Permissive-hypercapnia floor citation
- Document the real source for pH 7.30 / 7.20 cutoffs (currently uncited).

---

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
