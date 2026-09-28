"""
optimizer.py — the search.

Plain-language: this is the part that tries many ventilator settings, asks
physiology.py "what would happen?", throws out anything unsafe, and keeps the
safe setting that delivers the LEAST tidal power (the energy of the breath
itself — the comparison metric locked on 2026-09-27).

It is a "grid search": we just list out reasonable values for each knob and try
every combination. No AI, no black box — you can follow exactly why it chose what
it chose. That transparency is on purpose (see Mega-Prompt "white-box" goal).

What changed on 2026-09-28 — how PEEP is handled now:
  * The optimizer no longer "optimizes" PEEP. Our research found no validated way to
    predict how a given lung's compliance responds to a PEEP change (docs/_Research_Log.md,
    steps 1b and 2a), so tidal volume and rate are optimized at the CURRENT PEEP, where the
    prediction is trustworthy (plateau error ≈ 2.7 cmH2O for tidal-volume changes).
  * PEEP gets its own guidance block instead:
      1. the CEILING — the highest PEEP that keeps every cited limit (engine/safe_peep.py),
         with the reasons and the safety gates;
      2. for each possible step inside [current PEEP, ceiling]: the RANGE of what it might
         do to compliance, plateau and tidal power (a placeholder range until the
         full-MIMIC state model exists);
      3. the TEST-STEP protocol (option C): take the smallest step, measure, keep or reverse.
    A ceiling is never a recommendation to go there.

Run it directly to see the example:   python engine/optimizer.py
"""

import math
from dataclasses import dataclass
from typing import Optional

from physiology import (
    PatientCase, Baseline, Prediction, RESPONSE_RANGE_LABEL,
    baseline_mechanics, predict,
)
from safe_peep import State, SafePeepResult, highest_safe_peep, explain as explain_ceiling, DP_MAX


# Candidate values for each knob (ported from the v2.4 prototype).
CAND_RR = list(range(15, 31))                       # respiratory rates 15–30
CAND_VT = [350, 380, 400, 420, 450, 480]            # tidal volumes (VC mode)
CAND_PINSP = [15, 18, 20, 22, 24, 26, 28, 30]       # inspiratory pressures (PC mode)
PEEP_STEPS = [2, 4, 6]                              # PEEP steps shown with their range (protocol choice, not a clinical claim)
DP_NOISE = 2.0                                      # a driving-pressure change below this is within measurement noise
                                                    # (our demo: plateau re-measurement error 1.41 cmH2O with nothing changed — _Research_Log 1b)


@dataclass
class Limits:
    """Hard safety gates. A candidate is rejected if it breaks any of these."""
    min_ph: float             # lowest acceptable blood pH                      [E3][E6]
    max_pplat: float = 30.0   # plateau pressure cap                           [E3] ARDSNet
    max_vt_kg: float = 8.0    # upper tidal-volume limit (mL/kg PBW)           [E3]
    min_vt_kg: float = 4.0    # lower tidal-volume limit (mL/kg PBW)           [E3]


@dataclass
class OptimizerResult:
    setting: Optional[dict]          # the chosen knobs (or None if nothing was safe)
    prediction: Optional[Prediction]
    baseline_power: dict             # the three baseline power numbers (mp, mp_dyn, mp_tidal)
    explanation: str
    peep_ceiling: SafePeepResult     # the safe-PEEP ceiling with its reasons
    peep_guidance: str               # ceiling + ranges for each step + the test-step protocol


def ceiling_for(base: Baseline) -> SafePeepResult:
    """Build the safe-PEEP State straight from the baseline form and compute the ceiling."""
    s = State(vt_ml=base.vt, pplat=base.pplat, peep=base.peep, fio2=base.fio2, spo2=base.spo2, pao2=base.pao2,
              ppeak=base.ppeak, peep_total=base.peep_total, rr_spont=base.rr_spont, controlled_mode=base.controlled_mode,
              map_mmHg=base.map_mmHg, vasopressor_running=base.vasopressor_running, icp=base.icp,
              chest_tube=base.chest_tube, dpl_measured=base.dpl_measured)
    return highest_safe_peep(s)


def optimize(pt: PatientCase, base: Baseline, mode: str = "VC") -> OptimizerResult:
    """Find the lowest-tidal-power safe VT/RR (or Pinsp/RR) at the current PEEP,
    then attach the PEEP guidance (ceiling, ranges, test-step protocol)."""
    mech = baseline_mechanics(pt, base)
    limits = Limits(min_ph=7.20 if pt.permissive else 7.30)
    ceiling = ceiling_for(base)
    peep = base.peep     # held: no validated model of the lung's response to PEEP (see module docstring)

    # In VC we sweep tidal volumes; in PC we sweep inspiratory pressures.
    primary_values = CAND_VT if mode == "VC" else CAND_PINSP

    best_score = float("inf")
    best_setting = None
    best_pred = None

    for value in primary_values:
        for rr in CAND_RR:
            pred = predict(value, rr, peep, base.peep, pt, mech, mode)

            # ---- Safety gates (reject if any fails). See docs/_Schema.md ----
            if pred.pplat > limits.max_pplat:
                continue
            vt_per_kg = pred.vt / pt.pbw
            if vt_per_kg > limits.max_vt_kg or vt_per_kg < limits.min_vt_kg:
                continue
            if pred.ph < limits.min_ph:                # too acidic
                continue
            if pred.te < 3 * pred.tau:                 # not enough time to exhale → air-trapping [E5]
                continue

            # ---- Score: TIDAL power + a small "don't stray too far" penalty ----
            if mode == "VC":
                deviation = abs(pred.vt - base.vt) * 0.01
            else:
                deviation = abs(pred.pplat - base.pplat) * 0.5
            penalty = deviation + abs(rr - base.rr) * 0.5
            score = pred.mp_tidal + penalty

            if score < best_score:
                best_score = score
                best_setting = {"vt": pred.vt, "rr": rr, "peep": peep, "pinsp": pred.pplat, "mode": mode}
                best_pred = pred

    baseline_power = {"mp": mech.base_mp, "mp_dyn": mech.base_mp_dyn, "mp_tidal": mech.base_mp_tidal}
    violations = _baseline_violations(pt, base, limits)
    guidance = _peep_guidance(pt, base, mech, best_setting, ceiling, mode)
    return OptimizerResult(
        setting=best_setting, prediction=best_pred, baseline_power=baseline_power,
        explanation=_explain(pt, best_setting, best_pred, baseline_power, mode, limits, violations),
        peep_ceiling=ceiling, peep_guidance=guidance,
    )


def _baseline_violations(pt, base, limits) -> list:
    """Which limits do the CURRENT settings already break? (If any, the suggestion may use MORE power.)"""
    out = []
    base_ph = 6.1 + math.log10(pt.hco3 / (0.03 * pt.base_paco2))     # Henderson–Hasselbalch [E6]
    if base_ph < limits.min_ph:
        out.append(f"pH {base_ph:.2f} is below the floor {limits.min_ph:.2f}")
    if base.pplat > limits.max_pplat:
        out.append(f"plateau {base.pplat:g} is above the cap {limits.max_pplat:g}")
    vt_kg = base.vt / pt.pbw
    if vt_kg > limits.max_vt_kg or vt_kg < limits.min_vt_kg:
        out.append(f"tidal volume {vt_kg:.1f} mL/kg is outside {limits.min_vt_kg:g}–{limits.max_vt_kg:g}")
    return out


def _explain(pt, setting, pred, basep, mode, limits, violations) -> str:
    """Build a plain-language explanation a clinician (or Ahmed) can read."""
    if setting is None:
        return ("No safe setting was found within the limits "
                "(plateau pressure, tidal volume, pH, or air-trapping). "
                "The patient may need a different strategy — review manually.")

    saved = basep["mp_tidal"] - pred.mp_tidal
    pct = (saved / basep["mp_tidal"] * 100) if basep["mp_tidal"] else 0
    direction = "below" if saved >= 0 else "ABOVE"
    why_above = ""
    if violations:
        why_above = ("\n  ⚠ The CURRENT settings break a limit (" + "; ".join(violations) +
                     "), so the suggestion is the lowest tidal power that keeps EVERY limit — power may rise.")
    knob = f"VT {round(setting['vt'])} mL" if mode == "VC" else f"Pinsp {round(setting['pinsp'])} cmH2O"
    warn = "  ⚠ still high absolute power (>17 J/min, the level where risk rises [N8]) — review." if pred.mp > 17 else ""
    dp_flag = f"  ⚠ driving pressure {pred.driving_p:.0f} > {DP_MAX:g} cmH2O [N9] — lung stress remains high." if pred.driving_p > DP_MAX else ""
    ri = ""
    if pt.ri_index is not None:
        ri = (f"\n  Measured R/I index {pt.ri_index:.2f} → {'recruitable' if pt.ri_index > 0.5 else 'poorly recruitable'} lung [N1] "
              f"(information only — it does not change the math).")

    return (
        f"Suggested ({mode}): {knob} · RR {setting['rr']} · PEEP {setting['peep']:g} (held — see PEEP guidance).\n"
        f"  Tidal power (the comparison metric): {pred.mp_tidal:.1f} J/min — {abs(saved):.1f} J/min ({abs(pct):.0f}%) {direction} the current {basep['mp_tidal']:.1f}.{why_above}\n"
        f"  Absolute power, Gattinoni plateau form: {pred.mp:.1f} vs current {basep['mp']:.1f} J/min; "
        f"manuscript surrogate (peak-only): {pred.mp_dyn:.1f} vs current {basep['mp_dyn']:.1f} J/min.{warn}\n"
        f"  Predicted: plateau {pred.pplat:.0f}, driving pressure {pred.driving_p:.0f} cmH2O, pH {pred.ph:.2f} (floor {limits.min_ph:.2f}).{dp_flag}{ri}\n"
        f"  NOTE: this is a suggestion for a clinician to review — not a decision."
    )


def _peep_guidance(pt, base, mech, setting, ceiling: SafePeepResult, mode) -> str:
    """The PEEP block: the ceiling, the range for each possible step, and the test-step protocol."""
    lines = ["PEEP guidance", "-------------", explain_ceiling(ceiling)]
    if setting is None or ceiling.peep_max_safe is None:
        return "\n".join(lines)

    top = ceiling.peep_max_safe
    steps = [s for s in PEEP_STEPS if base.peep + s <= top + 1e-9]
    if not steps:
        lines.append(f"No PEEP increase inside the safe interval [{base.peep:g}, {top:g}] — hold PEEP.")
        return "\n".join(lines)

    lines.append(f"Safe interval for PEEP: {base.peep:g} to {top:g} cmH2O. What each step might do at the suggested VT/RR:")
    lines.append(f"  ({RESPONSE_RANGE_LABEL})")
    value = setting["vt"] if mode == "VC" else setting["pinsp"]
    for s in steps:
        p = predict(value, setting["rr"], base.peep + s, base.peep, pt, mech, mode)
        lo, hi = p.compliance_range
        lines.append(
            f"  PEEP {base.peep + s:g} (+{s}): compliance {lo * 100:+.0f}% to {hi * 100:+.0f}% → "
            f"plateau {p.pplat_range[0]:.0f}–{p.pplat_range[1]:.0f} cmH2O, tidal power {p.mp_tidal_range[0]:.1f}–{p.mp_tidal_range[1]:.1f} J/min "
            f"(if unchanged: plateau {p.pplat:.0f}, tidal power {p.mp_tidal:.1f})"
            + ("  ⚠ worst case breaks the plateau cap" if p.pplat_range[1] > 30 else "")
        )
    lines += [
        "Test-step protocol (option C — the safety net; a suggestion for the clinician):",
        f"  1. Take the SMALLEST step (+{steps[0]} cmH2O) at the suggested VT/RR.",
        "  2. Once the ventilator has settled at the new PEEP, re-measure the plateau (inspiratory hold) and check SpO2 and blood pressure.",
        f"  3. KEEP it if driving pressure fell or is unchanged (within the {DP_NOISE:g} cmH2O measurement noise) and SpO2/MAP are acceptable.",
        f"     REVERSE it if driving pressure rose by ≥ {DP_NOISE:g} cmH2O (compliance fell = over-distension), plateau > 30 [E3], "
        "MAP < 65 [N11], or SpO2 fell below target [E3].",
        "  4. Only then consider the next step. Never raise PEEP just to chase compliance (ART trial — _Literature_Validation T7).",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Example run (the same default case as the v2.4 prototype, plus the state the ceiling needs).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    patient = PatientCase(pbw=70, base_paco2=70, hco3=24, permissive=True,
                          pf_ratio=140, ri_index=None,
                          age=60, sex="M", height_cm=175, weight_kg=80)
    # Dead space defaults to the anatomic rule. Best: pass a real measurement, e.g.
    # measured_vd_vt=0.6. Harris–Benedict is available via use_hb=True but our demo
    # validation showed it worsened CO2 prediction, so it is opt-in.
    baseline = Baseline(vt=430, rr=20, peep=5, pplat=25, ppeak=30,
                        fio2=0.6, spo2=93, rr_spont=0, map_mmHg=75, vasopressor_running=False)

    print("=== VentOptimizer (research engine) — example case ===\n")
    result = optimize(patient, baseline, mode="VC")
    print(result.explanation)
    print()
    print(result.peep_guidance)
