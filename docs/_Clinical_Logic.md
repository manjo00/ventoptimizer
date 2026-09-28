# Clinical Logic — the physiology the engine uses

Each block has an **accuracy tag**: `[VALIDATED]` (published + checked), `[STANDARD]` (textbook physiology), `[ASSUMPTION]` (our simplification, may be wrong), `[TO-RESEARCH]` (Phase 1 will test it). Citations like `[E#]` point to `_Evidence_Base.md`.

---

## 1. Mechanical Power — the cost we minimize  `[VALIDATED] [E1][E2]`
The energy delivered to the lungs per minute, in joules/min. Two forms (decision 2026-09-28, see `_Evidence_Base` [E1]/[N8]):
```
(a) with a plateau (engine default):   MP     = 0.098 × RR × VT(L) × [ Ppeak − ½ × (Pplat − PEEP) ]      [E1]
    the same split into parts:         MP     = 0.098 × RR × VT(L) × [ PEEP + (Ppeak − Pplat) + ½ ΔP ]    static + resistive + tidal-elastic
    the part we OPTIMIZE:              MP_tidal = 0.098 × RR × VT(L) × ½ ΔP                                (locked objective, 2026-09-27)
(b) peak-only surrogate (fallback):    MP_dyn = 0.098 × RR × VT(L) × [ Ppeak − ½ × (Ppeak − PEEP) ]      [M][N8]
```
- (b) is Ahmed's manuscript's equation (uses **peak** pressure only, so it works from hourly charting without a hold maneuver); the engine uses (a) whenever a plateau exists and always reports (b) alongside, labelled, for the link to the manuscript's mortality result.
- **Why VT matters more than RR:** raising VT raises both the volume *and* the pressure term, so its effect on power is roughly **squared**; RR enters only **linearly**. → the optimizer naturally prefers **smaller breaths, faster rate**.
- Caveat `[E2]`: peak pressure includes airway *resistance*, so in stiff-airway patients MP can be over-estimated vs a plateau-based version.

## 2. Lung compliance — how stretchy the lung is  `[ASSUMPTION → known wrong, N2]`
```
Static compliance  C = VT ÷ (Pplat − PEEP)        (mL per cmH₂O)
```
- We assume compliance is **constant (linear)** across pressures. The ARDS pressure–volume curve is **not** linear — it has a lower and an upper inflection point `[N2]`, so compliance changes with pressure and recruitment.
- **This is the model's biggest known weakness.** Track C will measure the error and replace "linear" with each patient's own P–V curve. (Research Agenda Q1.)

## 3. Recruitment — does adding PEEP help or hurt?  `[concept cited N1; NO validated magnitude — 2026-09-28]`
The physiology: in a **recruitable** lung (R/I > 0.5 `[N1]`) raising PEEP opens collapsed units → compliance improves → driving pressure and tidal power can *fall*; in a **non-recruitable** lung it overstretches → compliance worsens → they *rise*. The direction is real; **the size is not predictable from routine data yet.**
- **History:** the prototype used `C_new = C × (1 + (R/I − 0.5) × 0.1 × ΔPEEP)`; the demo then seemed to confirm a population slope β ≈ 0.083 and a 28% prediction gain — **both were artifacts of carried (forward-filled) plateaus and were retracted** (`_Research_Log` 2026-09-28, step 1b). On real measurements β = 0.026 with an interval including zero, and a patient's own previous step did not predict the next one either (step 2a).
- **Current math (engine, 2026-09-28):** point estimate = **compliance unchanged** across a PEEP step (it beat every alternative on real data); every PEEP step carries a **range** — placeholder IQRs from the open demo (PEEP↑: −7% to +31%; PEEP↓: −30% to +35%; n = 27) until the full-MIMIC state model passes its pre-set criterion (`_Analysis_Plan_FullMIMIC.md`, H1). A measured R/I, if the maneuver was done, is shown as information only.
- **Consequence for the optimizer:** PEEP is **not** searched; VT/rate are optimized at the current PEEP; PEEP gets the ceiling (§8), the range for each step, and the test-step protocol (option C).
- 🟥 **Prediction only, never titration.** A compliance change with PEEP is *not* a recruitment measure, and titrating PEEP to "best compliance" increased mortality (ART trial, JAMA 2017). The optimizer must never raise PEEP just to chase compliance. See `_Literature_Validation.md` T7.
- 🟥 **Use it for PREDICTION only.** A compliance change with PEEP is *not* a recruitment measure, and titrating PEEP to "best compliance" increased mortality (ART trial, JAMA 2017). The optimizer must keep minimizing MP within ARDSNet limits — never raise PEEP just to chase compliance. See `_Literature_Validation.md` T7.

## 4. Auto-PEEP / breath-stacking guard  `[STANDARD] [E5]`
A lung empties on an exponential curve with time constant `τ = Resistance × Compliance`. It takes ~3 time constants to empty 95%.
```
τ  = R_aw × (C ÷ 1000)          (seconds)
Te = (60 ÷ RR) − 1.0            (expiratory time, assumes ~1 s inspiration)
Rule: reject any setting where  Te < 3 × τ   (not enough time to exhale → air traps)
```
Protects obstructive/COPD patients from breath-stacking. The "1.0 s inspiration" is an `[ASSUMPTION]`.

## 5. Volume control (VC) vs Pressure control (PC)  `[STANDARD]`
- **VC:** you set the breath size (VT); the model predicts the pressure → `Pplat = PEEP + VT/C`. Rejects if Pplat too high.
- **PC:** you set the pressure (Pinsp); the model predicts the breath size → `VT = (Pinsp − PEEP) × C`. Rejects if VT causes volutrauma (>8 mL/kg). PC skips airflow modelling entirely (Ohm's-law style).

## 6. Gas exchange & pH — don't suffocate the patient  `[STANDARD] [E6]`
CO₂ is cleared by *alveolar* ventilation (total breath minus wasted "dead space"):
```
Dead space ≈ 2.2 mL × PBW(kg)            [rough convention: Radford N3a; weakly validated N3b]
Alveolar ventilation Va = RR × (VT − dead space)
Predicted CO₂  = (baseline Va × baseline CO₂) ÷ new Va     (inverse rule)
Predicted pH   = 6.1 + log10( HCO₃ ÷ (0.03 × CO₂) )        (Henderson–Hasselbalch)
```
- **Permissive hypercapnia:** we let CO₂ rise but only to a pH floor (7.30 standard, 7.20 permissive) — ARDSNet-aligned pragmatic conventions `[E3, E6]`; ~7.20 is the widely accepted (if somewhat arbitrary) lower bound. ⚠️ **Contraindicated with raised intracranial pressure / brain injury** (CO₂ raises ICP) — permissive mode needs a safety gate (`_Literature_Validation` T10).
- 🟥 **Dead space is the weak link `[N4]`:** real *physiological* dead space in ARDS is 0.5–0.7 of VT (vs ~0.36 from our anatomic 2.2 mL/kg) and predicts mortality (Nuckton, NEJM 2002) → CO₂/pH predictions are biased in sick lungs. Track-C fix: a physiological estimate (ventilatory ratio). See `_Literature_Validation` T9.

## 7. The baseline plateau pressure is mandatory  `[STANDARD]`
Everything keys off the measured `Pplat` (via an inspiratory hold) because that's what gives the starting compliance `C`. Without it, the model has no anchor and cannot predict.

## 8. The highest SAFE PEEP — the ceiling (sub-problem 1)  `[E3][N7][N9][N10][N11]` + two `[ASSUMPTION]`s  (`engine/safe_peep.py`, 2026-09-28)
This answers "how high could PEEP go right now without over-stretching the lung or tripping a safety gate?" **using only the current chart, with no prediction of the lung's response.**
```
compliance now          C = VT ÷ (Pplat − PEEP_total)
cautious projection     C(PEEP_new) = C × (1 − 0.05 × ΔPEEP)   capped at −50%      [ASSUMPTION — demo lower-quartile response]
projected plateau       Pplat(PEEP_new) = PEEP_new + VT ÷ C(PEEP_new)
ceiling                 the highest PEEP_new (≤ 24) with  Pplat ≤ 30 [E3],  ΔP ≤ 15 [N9][E4],  ΔP × 0.7 ≤ 11.7 [N9]
                        then capped by the top of the ARDSNet PEEP/FiO₂ envelope for the FiO₂ in use [E3][N7]
```
- **Gates that forbid any increase:** plateau already > 30 · driving pressure already > 15 · ICP > 22 mmHg `[N10]` · MAP < 65 mmHg `[N11]` · support mode or spontaneous breaths (plateau invalid).
- **Cautions (no veto):** ICP monitored · vasopressor running · chest tube (air leak) · measured auto-PEEP (3τ rule `[E5]`).
- **Oxygenation** (SpO₂ 88–95% / PaO₂ 55–80 `[E3]`) is reported as *status* — it can motivate a change within the ceiling, never override it.
- The margin makes the ceiling **conservative when the lung recruits** (real plateau would be lower) and **protective when it over-distends**. The full-MIMIC H5 result (`_Analysis_Plan_FullMIMIC.md`) replaces the margin with measured worst-case responses by PEEP level.
- 🟥 A ceiling is **not** a recommendation to go there. Sub-problem 2 (state model + test step) decides where, inside `[current PEEP, ceiling]`, the tidal power is lowest.

---

## How these become the optimizer (see `engine/optimizer.py`, rewired 2026-09-28)
1. Compute the **safe-PEEP ceiling** (§8) from the current state — with its vetoes and cautions.
2. Build a grid of candidate settings (ranges of VT/Pinsp and RR) **at the current PEEP** — PEEP is held, because no validated model predicts the lung's response to a PEEP step (§3).
3. For each: pressures (§5), the three power numbers (§1), pH (§6), auto-PEEP (§4).
4. **Reject** any that break a limit in `_Schema.md`; flag driving pressure > 15.
5. **Score** survivors = **tidal power** (§1) + a small penalty for drifting far from the current VT/rate. Return the lowest, with a plain-language reason that shows tidal power vs current, and both absolute forms labelled.
6. **PEEP guidance:** for each step inside `[current PEEP, ceiling]`, show the **range** of compliance, plateau and tidal power (§3), then the **test-step protocol** (option C): smallest step → re-measure the plateau → keep if driving pressure fell or is unchanged (within the 2 cmH₂O noise) and SpO₂/MAP are acceptable → reverse if it rose, plateau > 30, MAP < 65, or SpO₂ fell. A ceiling is never a recommendation to go there.
