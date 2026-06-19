"""
optimizer.py — the search.

Plain-language: this is the part that tries thousands of ventilator settings,
asks physiology.py "what would happen?", throws out anything unsafe, and keeps
the safe setting that delivers the LEAST Mechanical Power (energy to the lungs).

It is a "grid search": we just list out reasonable values for each knob and try
every combination. No AI, no black box — you can follow exactly why it chose what
it chose. That transparency is on purpose (see Mega-Prompt "white-box" goal).

Run it directly to see the example:   python engine/optimizer.py
"""

from dataclasses import dataclass
from typing import Optional

from physiology import (
    PatientCase, Baseline, Prediction,
    baseline_mechanics, predict,
)


# Candidate values for each knob (ported from the v2.4 prototype).
CAND_RR = list(range(15, 31))                       # respiratory rates 15–30
CAND_PEEP = [5, 8, 10, 12, 14, 16]                  # PEEP options
CAND_VT = [350, 380, 400, 420, 450, 480]            # tidal volumes (VC mode)
CAND_PINSP = [15, 18, 20, 22, 24, 26, 28, 30]       # inspiratory pressures (PC mode)


@dataclass
class Limits:
    """Hard safety gates. A candidate is rejected if it breaks any of these."""
    min_ph: float       # lowest acceptable blood pH
    max_pplat: float = 30.0   # plateau pressure cap (ARDSNet) — _Evidence_Base
    max_vt_kg: float = 8.0    # upper tidal-volume limit (mL/kg PBW)
    min_vt_kg: float = 4.0    # lower tidal-volume limit (mL/kg PBW)


@dataclass
class OptimizerResult:
    setting: Optional[dict]        # the chosen knobs (or None if nothing was safe)
    prediction: Optional[Prediction]
    baseline_mp: float
    explanation: str


def optimize(pt: PatientCase, base: Baseline, mode: str = "VC") -> OptimizerResult:
    """Find the lowest-Mechanical-Power safe setting for this patient."""
    mech = baseline_mechanics(pt, base)
    limits = Limits(min_ph=7.20 if pt.permissive else 7.30)

    recruitable = pt.ri_index > 0.5
    hypoxic = pt.pf_ratio < 150

    # In VC we sweep tidal volumes; in PC we sweep inspiratory pressures.
    primary_values = CAND_VT if mode == "VC" else CAND_PINSP

    best_score = float("inf")
    best_setting = None
    best_pred = None

    # Try every combination of (primary knob, rate, PEEP).
    for value in primary_values:
        for rr in CAND_RR:
            for peep in CAND_PEEP:
                pred = predict(value, rr, peep, base.peep, pt, mech, mode)

                # ---- Safety gates (reject if any fails). See docs/_Schema.md ----
                if pred.pplat > limits.max_pplat:
                    continue
                vt_per_kg = pred.vt / pt.pbw
                if vt_per_kg > limits.max_vt_kg or vt_per_kg < limits.min_vt_kg:
                    continue
                if pred.ph < limits.min_ph:                # too acidic
                    continue
                if pred.te < 3 * pred.tau:                 # not enough time to exhale → air-trapping
                    continue
                if (not recruitable) and peep > base.peep:  # don't over-distend a stiff lung
                    continue
                if recruitable and hypoxic and peep < base.peep:  # don't drop PEEP on a sick recruitable lung
                    continue

                # ---- Score: Mechanical Power + a small "don't stray too far" penalty ----
                if mode == "VC":
                    deviation = abs(pred.vt - base.vt) * 0.01
                else:
                    deviation = abs(pred.pplat - base.pplat) * 0.5
                penalty = deviation + abs(rr - base.rr) * 0.5 + abs(peep - base.peep) * 1.0
                score = pred.mp + penalty

                if score < best_score:
                    best_score = score
                    best_setting = {"vt": pred.vt, "rr": rr, "peep": peep, "pinsp": pred.pplat, "mode": mode}
                    best_pred = pred

    return OptimizerResult(
        setting=best_setting,
        prediction=best_pred,
        baseline_mp=mech.base_mp,
        explanation=_explain(best_setting, best_pred, mech.base_mp, recruitable, mode, limits),
    )


def _explain(setting, pred, base_mp, recruitable, mode, limits) -> str:
    """Build a plain-language explanation a clinician (or Ahmed) can read."""
    if setting is None:
        return ("No safe setting was found within the limits "
                "(plateau pressure, tidal volume, pH, or air-trapping). "
                "The patient may need a different strategy — review manually.")

    saved = base_mp - pred.mp
    pct = (saved / base_mp * 100) if base_mp else 0
    direction = "below" if saved >= 0 else "ABOVE"
    knob = f"VT {round(setting['vt'])} mL" if mode == "VC" else f"Pinsp {round(setting['pinsp'])} cmH2O"
    warn = "  ⚠ still high power (>25 J/min) — review." if pred.mp > 25 else ""

    return (
        f"Suggested ({mode}): {knob} · RR {setting['rr']} · PEEP {setting['peep']}.\n"
        f"  Mechanical Power {pred.mp:.1f} J/min — {abs(saved):.1f} J/min ({abs(pct):.0f}%) {direction} the current {base_mp:.1f}.{warn}\n"
        f"  Predicted: plateau {pred.pplat:.0f}, driving pressure {pred.driving_p:.0f} cmH2O, pH {pred.ph:.2f} (floor {limits.min_ph:.2f}).\n"
        f"  Logic: {'recruitable' if recruitable else 'non-recruitable'} lung; kept inside all safety limits.\n"
        f"  NOTE: this is a suggestion for a clinician to review — not a decision."
    )


# ---------------------------------------------------------------------------
# Example run (the same default case as the v2.4 prototype).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    patient = PatientCase(pbw=70, pf_ratio=140, ri_index=0.8,
                          base_paco2=70, hco3=24, permissive=True)
    baseline = Baseline(vt=430, rr=20, peep=5, pplat=25, ppeak=30)

    print("=== VentOptimizer (research engine) — example case ===\n")
    result = optimize(patient, baseline, mode="VC")
    print(result.explanation)
