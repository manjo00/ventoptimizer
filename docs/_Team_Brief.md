# VentOptimizer — where we are (team brief, 28 September 2026)

*For the team and the supervisor. Written for respiratory therapists; no coding, statistics or advanced math assumed.*

**In one sentence.** We are building a prototype that suggests the ventilator settings that deliver the **least mechanical power** to the lungs while staying inside safety limits. It is tested only on recorded ICU data, never on live patients, and it advises a clinician; it never decides.

**Why mechanical power.** Our own MIMIC-IV study (the ICM draft, Sep 2026; 19,801 ventilated adults) showed that moving from the lower to the upper quarter of mechanical power (8.2 to 13.6 joules per minute) raised the odds of death within 28 days by about half, that the risk kept rising across the whole range with no safe floor or breakpoint, and that the signal sat mainly in the *respiratory rate*, not the tidal volume. So the tool's job is simple to state: find the safe setting that delivers the least energy — without lowering the number by cutting breath size and raising the rate, which the study warns may not reduce harm at all (an open design question, Q6).

**The key insight so far: PEEP is the whole game.** Shuffling tidal volume and rate while keeping CO2 clearance the same barely changes the power (median saving 0.1 joule per minute in real patients). The energy of each breath only falls if the lung becomes easier to inflate. That is exactly what a good PEEP change does in a recruitable lung, and the opposite of what it does in a non-recruitable one. So the tool must do two things: **(1)** find the highest PEEP that is still safe, and **(2)** predict how a PEEP change will alter compliance. One detail we settled: we compare settings by the *breath* part of the power (the driving-pressure part), not total power, because total power always rises with PEEP and would push the tool toward too little PEEP.

**What we have built.**
- An organized project with its own memory files and a GitHub backup, so nothing is lost between work sessions.
- Every rule the tool uses is traced to a published paper, with the strength of the evidence labelled. Low tidal volume and plateau pressure of 30 or less are trial-proven; the link between power and death is a strong association, not a trial.
- A dataset check: MIMIC-IV contains every number the math needs. The only gap is a pleural-pressure reference, which exists only for the roughly 3% of patients who had an esophageal balloon; those patients become the test set for our no-balloon method.
- Scripts that read the data on the credentialed computer and print totals only. No patient information ever leaves that computer, which is what the PhysioNet data agreement requires.

**What the first tests showed (the free 100-patient sample, 67 of them ventilated).**
- **We caught our own mistake.** Early on, the code carried an old plateau pressure forward in time. After a PEEP change it compared the new PEEP against the old plateau, which made compliance look like it improved by 40% with more PEEP. We retracted that result. Using only plateaus truly measured at each PEEP, the average improvement is 8.6%, and that is not distinguishable from zero.
- **Patients truly differ.** The spread of responses to a PEEP change is about three times wider than the measurement noise, so the differences are real physiology. But a patient's own last response does not predict the next one: the direction agrees only 43% of the time. So neither an average rule nor "learn from the patient's history" works.
- **What survives.** Compliance is not a constant (it varies about 18% within one patient), and PEEP changes are the hardest thing to predict.

| Key number | Value |
|---|---|
| Clean before-and-after PEEP changes in the sample | 27 in 13 patients |
| Spread of responses compared with measurement noise | about 3 times wider |
| How often a patient's next response matches the last | 43% |
| Clean PEEP changes expected in the full MIMIC-IV | roughly 10,000 |

**Our decision (option c).** Build a model that predicts the compliance response from the patient's **state before the change** (PEEP level, direction of the change, lung stiffness, oxygenation, CO2, body size, days on the ventilator) and always shows a **range**, never a single number. And keep a **small reversible test step** as the safety net: change PEEP a little, measure the real response, then decide. If the model fails its pass mark, the test-step approach becomes the primary design. All of this is written in a frozen analysis plan with pass/fail criteria decided **before** we look at the full data, so we cannot fool ourselves again.

**What we need from the data lead.** Run four scripts on the full MIMIC-IV folder (the exact commands are in `docs/_Analysis_Plan_FullMIMIC.md`, section 12) and send back what they print. The scripts print totals only and hide any group smaller than ten patients. Please do not send any file with one row per patient, any IDs, or any dates. Also tell us the MIMIC-IV version you hold. Expect tens of minutes per script.

**What we ask the supervisor.** Review the plan's five hypotheses and their pass marks, the safety framing (this is prediction on recorded data, never bedside titration; the ART trial showed that compliance-guided PEEP can harm), and the angle for the paper. Edits are welcome now. Once the full run starts, the plan is frozen.

**Next steps.**
1. The full-data run, then apply the pre-set decision rules.
2. In parallel, the highest-safe-PEEP side: pressure ceilings, oxygenation floors and safety gates. This does not depend on prediction.
3. Put the winning approach into the engine and the bedside prototype.
4. Write up.

*Where to read more:* `CLAUDE.md` (goals and rules), `docs/_Compact.md` (one-page state), `docs/_Analysis_Plan_FullMIMIC.md` (the frozen plan), `docs/_Research_Log.md` (every experiment, with numbers), `docs/_Literature_Validation.md` (which claims are proven and how strongly).
