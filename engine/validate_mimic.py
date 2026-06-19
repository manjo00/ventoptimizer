"""
validate_mimic.py — the shadow-testing harness (Phase 1 deliverable).

THIS IS A SKELETON. The structure and the comparison logic are here and runnable
(on a tiny made-up example), but loading REAL MIMIC-IV patients is still to do —
that's the open question in docs/_Current_Task.md.

Plain-language: "shadow testing" means we replay real patients. For each one we
know (a) their state at one moment and (b) what actually happened next. We let the
model predict what it *thinks* would happen, then compare prediction vs reality.
The gap is the model's error — exactly what Phase 1 needs to measure.

What we compare (for now): predicted vs observed plateau pressure, Mechanical
Power, and pH after a settings change.
"""

from dataclasses import dataclass

from physiology import PatientCase, Baseline, baseline_mechanics, predict


@dataclass
class ShadowCase:
    """One replayed patient: a baseline, a later setting the clinician used,
    and what was actually observed at that later setting."""
    pt: PatientCase
    base: Baseline
    # the later setting the clinician actually chose:
    later_vt: float
    later_rr: float
    later_peep: float
    # what was actually measured at that later setting (the "truth"):
    observed_pplat: float
    observed_ph: float


def shadow_test(cases):
    """Predict each later state from the baseline, compare to what was observed."""
    rows = []
    for i, c in enumerate(cases, 1):
        mech = baseline_mechanics(c.pt, c.base)
        # Predict the later state, in VC mode, using the clinician's later VT/RR/PEEP.
        pred = predict(c.later_vt, c.later_rr, c.later_peep, c.base.peep,
                       c.pt, mech, mode="VC")
        rows.append({
            "case": i,
            "pplat_pred": pred.pplat, "pplat_obs": c.observed_pplat,
            "pplat_err": pred.pplat - c.observed_pplat,
            "ph_pred": pred.ph, "ph_obs": c.observed_ph,
            "ph_err": pred.ph - c.observed_ph,
        })

    # Summary: average absolute error per variable.
    n = len(rows)
    mae_pplat = sum(abs(r["pplat_err"]) for r in rows) / n
    mae_ph = sum(abs(r["ph_err"]) for r in rows) / n

    print(f"Shadow test on {n} case(s):\n")
    for r in rows:
        print(f"  case {r['case']}: "
              f"plateau predicted {r['pplat_pred']:.1f} vs observed {r['pplat_obs']:.1f} "
              f"(off by {r['pplat_err']:+.1f}) | "
              f"pH predicted {r['ph_pred']:.2f} vs observed {r['ph_obs']:.2f} "
              f"(off by {r['ph_err']:+.2f})")
    print(f"\n  Average error — plateau pressure: {mae_pplat:.1f} cmH2O | pH: {mae_ph:.2f}")
    print("  (Lower is better. Big plateau errors would point at the linear-compliance assumption — see _Research_Agenda Q1.)")
    return rows


# ---------------------------------------------------------------------------
# TODO (Phase 1, next task): replace this synthetic demo with real loading from
# the MIMIC-IV respiratory dataset (the same source as the manuscript).
#   def load_mimic_cases(path) -> list[ShadowCase]: ...
# Decision still needed: MIMIC-IV (recommended — you have access) vs MIMIC-III.
# ---------------------------------------------------------------------------

def _demo_cases():
    """Two made-up patients, just so this file runs and shows the output format."""
    return [
        ShadowCase(
            pt=PatientCase(pbw=70, pf_ratio=140, ri_index=0.5, base_paco2=45, hco3=24, permissive=False),
            base=Baseline(vt=420, rr=18, peep=8, pplat=22, ppeak=28),
            later_vt=450, later_rr=20, later_peep=8,
            observed_pplat=24.0, observed_ph=7.36,
        ),
        ShadowCase(
            pt=PatientCase(pbw=60, pf_ratio=110, ri_index=0.7, base_paco2=50, hco3=26, permissive=True),
            base=Baseline(vt=360, rr=22, peep=10, pplat=26, ppeak=33),
            later_vt=380, later_rr=24, later_peep=12,
            observed_pplat=27.5, observed_ph=7.30,
        ),
    ]


if __name__ == "__main__":
    print("=== MIMIC shadow-testing harness (SKELETON — synthetic data) ===\n")
    shadow_test(_demo_cases())
