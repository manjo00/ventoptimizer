# Clinical Logic — the physiology the engine uses

Each block has an **accuracy tag**: `[VALIDATED]` (published + checked), `[STANDARD]` (textbook physiology), `[ASSUMPTION]` (our simplification, may be wrong), `[TO-RESEARCH]` (Phase 1 will test it). Citations like `[E#]` point to `_Evidence_Base.md`.

---

## 1. Mechanical Power — the cost we minimize  `[VALIDATED] [E1][E2]`
The energy delivered to the lungs per minute, in joules/min:
```
MP = 0.098 × RR × VT(litres) × [ Ppeak − ½ × (Ppeak − PEEP) ]
```
- Same equation as Ahmed's manuscript (Gattinoni dynamic surrogate, uses **peak** pressure so no special maneuver needed).
- **Why VT matters more than RR:** raising VT raises both the volume *and* the pressure term, so its effect on power is roughly **squared**; RR enters only **linearly**. → the optimizer naturally prefers **smaller breaths, faster rate**.
- Caveat `[E2]`: peak pressure includes airway *resistance*, so in stiff-airway patients MP can be over-estimated vs a plateau-based version.

## 2. Lung compliance — how stretchy the lung is  `[ASSUMPTION → known wrong, N2]`
```
Static compliance  C = VT ÷ (Pplat − PEEP)        (mL per cmH₂O)
```
- We assume compliance is **constant (linear)** across pressures. The ARDS pressure–volume curve is **not** linear — it has a lower and an upper inflection point `[N2]`, so compliance changes with pressure and recruitment.
- **This is the model's biggest known weakness.** Track C will measure the error and replace "linear" with each patient's own P–V curve. (Research Agenda Q1.)

## 3. Recruitment — does adding PEEP help or hurt?  `[concept cited N1; magnitude data-supported]`
Uses the Recruitment-to-Inflation (R/I) index:
- **R/I > 0.5 (recruitable):** raising PEEP opens collapsed lung → compliance improves → driving pressure and MP can *fall*.
- **R/I < 0.5 (non-recruitable):** raising PEEP overstretches → compliance worsens → MP *rises*.
- Current math: `C_new = C × (1 + (R/I − 0.5) × 0.1 × ΔPEEP)`. The **R/I concept and the 0.5 cut-off are cited** `[N1]` (Chen 2020). The `×0.1` magnitude is now **data-supported**: the demo shows a population recruitment slope **β ≈ 0.083/cmH₂O**, and a PEEP-aware correction cut plateau error **28%** on held-out patients (see `_Research_Log`). Confirm on full MIMIC-IV before changing the production model.
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

---

## How these become the optimizer (see `engine/optimizer.py`)
1. Build a grid of candidate settings (ranges of VT/Pinsp, RR, PEEP).
2. For each: predict compliance (§2–3), pressures (§5), MP (§1), pH (§6), auto-PEEP (§4).
3. **Reject** any that break a limit in `_Schema.md`.
4. **Score** survivors = MP + a small penalty for drifting far from the patient's current settings.
5. Return the lowest score, with a plain-language reason.
