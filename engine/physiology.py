"""
physiology.py — the prediction models.

Plain-language: this file is the "what would happen if..." calculator.
Give it a patient and a proposed ventilator setting, and it predicts the
pressures, the Mechanical Power (energy to the lungs), and the blood pH.

It does NOT choose settings — that's optimizer.py's job. This file only predicts.

Every formula here is explained in docs/_Clinical_Logic.md (with citations in
docs/_Evidence_Base.md). The section numbers (§1–§6) below match that file.

Units: pressures in cmH2O, volumes in mL (litres where noted), rate in breaths/min.
"""

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# The data "forms" (see docs/_Schema.md). A dataclass is just a labelled form:
# a bundle of named fields you fill in.
# ---------------------------------------------------------------------------

@dataclass
class PatientCase:
    pbw: float          # predicted body weight (kg)
    pf_ratio: float     # oxygenation PaO2/FiO2 (lower = sicker lungs)
    ri_index: float     # recruitment-to-inflation index, 0–1 (>0.5 = recruitable)
    base_paco2: float   # current arterial CO2 (mmHg)
    hco3: float         # bicarbonate (mmol/L)
    permissive: bool    # allow higher CO2 (pH floor 7.20 instead of 7.30)?
    # --- optional: enable the Harris–Benedict physiological dead space (else we fall back) ---
    age: float = None             # years
    sex: str = None               # "M" or "F"
    height_cm: float = None       # height in cm
    weight_kg: float = None       # actual weight (kg); falls back to PBW if missing
    use_hb: bool = False          # opt-in Harris–Benedict dead space (OFF by default — our
                                  # demo validation showed it WORSENED CO2 prediction; see _Research_Log)
    # --- optional MANUAL overrides (use a real measurement if you have one) ---
    measured_deadspace_ml: float = None   # a measured dead space, in mL
    measured_vd_vt: float = None          # a measured dead-space fraction, 0–1


@dataclass
class Baseline:
    vt: float       # current tidal volume (mL)
    rr: float       # current respiratory rate (/min)
    peep: float     # current PEEP (cmH2O)
    pplat: float    # measured plateau pressure via inspiratory hold (cmH2O) — REQUIRED
    ppeak: float    # current peak pressure (cmH2O)


@dataclass
class Mechanics:
    """Constants derived once from the baseline; reused for every candidate."""
    c_stat_base: float    # baseline static compliance (mL/cmH2O) = how stretchy the lung is
    resistive_gap: float  # peak − plateau = pressure lost to airway resistance
    r_aw: float           # airway resistance (cmH2O per L/s)
    v_deadspace: float    # "wasted" volume that doesn't reach gas exchange (mL)
    base_valv: float      # baseline alveolar ventilation (mL/min)
    base_mp: float        # baseline Mechanical Power (J/min)


@dataclass
class Prediction:
    mp: float          # Mechanical Power (J/min) — the thing we minimize
    pplat: float       # predicted plateau pressure
    driving_p: float   # driving pressure = Pplat − PEEP (lung stretch per breath)
    ppeak: float       # predicted peak pressure
    vt: float          # resulting tidal volume (mL)
    ph: float          # predicted blood pH
    paco2: float       # predicted CO2 (mmHg)
    tau: float         # time constant (s) — how fast the lung empties
    te: float          # expiratory time available (s)


# ---------------------------------------------------------------------------
# Dead space — how much of each breath is "wasted" (doesn't exchange gas).
# We try three sources, best first (see docs/_Literature_Validation.md T9 and
# docs/_Research_Agenda.md Q3):
#   1) a MANUAL measured value, if the clinician has one;
#   2) the Harris–Benedict physiological estimate (needs age/sex/height);
#   3) the old anatomic 2.2 mL/kg rule, as a fallback.
# ---------------------------------------------------------------------------

def estimate_vco2_ml_min(age, sex, weight_kg, height_cm, rq=0.8):
    """Estimate CO2 production (mL/min) from the Harris–Benedict resting-energy
    equation. Plain words: predict how much CO2 the body makes from age, sex,
    height and weight. Returns None if any input is missing."""
    if age is None or sex is None or weight_kg is None or height_cm is None:
        return None
    if str(sex).upper().startswith("M"):
        ree = 66.47 + 13.75 * weight_kg + 5.003 * height_cm - 6.755 * age   # kcal/day
    else:
        ree = 655.1 + 9.563 * weight_kg + 1.850 * height_cm - 4.676 * age
    # Weir equation (energy ↔ gas): REE = 1.44 × VCO2 × (3.94/rq + 1.11)
    return ree / (1.44 * (3.94 / rq + 1.11))    # mL/min


def dead_space_ml(pt: PatientCase, vt_ml: float, rr: float, paco2: float) -> float:
    """Physiological dead space (mL): manual → Harris–Benedict → anatomic fallback."""
    # 1) manual / measured override
    if pt.measured_deadspace_ml is not None:
        return pt.measured_deadspace_ml
    if pt.measured_vd_vt is not None:
        return pt.measured_vd_vt * vt_ml

    # 2) Harris–Benedict physiological estimate — OPT-IN only.
    #    Our demo validation showed HB worsened CO2 prediction (14.4 → 33.6 mmHg),
    #    so it is OFF unless pt.use_hb is set. See docs/_Research_Log.md (2026-06-20).
    if pt.use_hb:
        weight = pt.weight_kg if pt.weight_kg is not None else pt.pbw
        vco2 = estimate_vco2_ml_min(pt.age, pt.sex, weight, pt.height_cm)
        ve_l_min = (vt_ml / 1000.0) * rr        # minute ventilation, L/min
        if vco2 is not None and paco2 and paco2 > 0 and ve_l_min > 0:
            # Dead-space fraction: VD/VT = 1 − (VCO2 × 0.863) / (PaCO2 × minute ventilation)
            vd_vt = 1.0 - (vco2 * 0.863) / (paco2 * ve_l_min)
            vd_vt = min(max(vd_vt, 0.1), 0.85)  # clamp to a plausible range
            return vd_vt * vt_ml

    # 3) default / fallback: the anatomic rule
    return 2.2 * pt.pbw


# ---------------------------------------------------------------------------
# Step 1: work out the patient's baseline mechanics (done once per patient).
# ---------------------------------------------------------------------------

def baseline_mechanics(pt: PatientCase, base: Baseline) -> Mechanics:
    # §2 Driving pressure = how much pressure it took to deliver the breath.
    driving_p_base = base.pplat - base.peep

    # §2 Static compliance = breath size ÷ driving pressure (mL per cmH2O).
    # If driving pressure is somehow ≤0 (bad data), fall back to a typical value.
    c_stat_base = base.vt / driving_p_base if driving_p_base > 0 else 50.0

    # §4 The gap between peak and plateau pressure is caused by airway resistance.
    resistive_gap = base.ppeak - base.pplat

    # §4 Resistance = pressure-gap ÷ flow. Flow is assumed ~1 L/s here.
    r_aw = resistive_gap / ((base.vt / 1000.0) / 1.0)

    # §6 Dead space: physiological estimate (manual → Harris–Benedict → anatomic fallback).
    v_deadspace = dead_space_ml(pt, base.vt, base.rr, pt.base_paco2)

    # §6 Alveolar ventilation = the part of breathing that actually clears CO2.
    base_valv = base.rr * (base.vt - v_deadspace)

    # §1 Baseline Mechanical Power (the number we're trying to beat).
    base_mp = 0.098 * base.rr * (base.vt / 1000.0) * (base.ppeak - 0.5 * driving_p_base)

    return Mechanics(c_stat_base, resistive_gap, r_aw, v_deadspace, base_valv, base_mp)


# ---------------------------------------------------------------------------
# Step 2: how compliance changes when we change PEEP (§3 recruitment).
# ---------------------------------------------------------------------------

def dynamic_compliance(c_base: float, ri_index: float, peep: float, base_peep: float) -> float:
    """
    If we RAISE PEEP in a recruitable lung (R/I > 0.5), collapsed lung opens up
    and the lung gets more compliant (stretchier). If it's non-recruitable, the
    opposite. NOTE: the 0.1 multiplier is an unproven assumption (see _Clinical_Logic §3).
    """
    delta_peep = peep - base_peep
    if delta_peep > 0:
        recruitment_factor = (ri_index - 0.5) * 0.1   # [ASSUMPTION] — Phase 1 will test this
        return c_base * (1 + recruitment_factor * delta_peep)
    return c_base


# ---------------------------------------------------------------------------
# Step 3: predict everything for ONE candidate setting.
# ---------------------------------------------------------------------------

def predict(value: float, rr: float, peep: float, base_peep: float,
            pt: PatientCase, mech: Mechanics, mode: str) -> Prediction:
    """
    Predict the outcome of one ventilator setting.

    mode == 'VC'  → `value` is the tidal volume (mL) you set; we predict the pressure.
    mode == 'PC'  → `value` is the inspiratory pressure (cmH2O) you set; we predict the volume.
    `base_peep` is the patient's current PEEP, needed for the recruitment effect.
    """
    # §3 compliance at this PEEP (recruitment effect)
    c_new = dynamic_compliance(mech.c_stat_base, pt.ri_index, peep, base_peep)

    # §5 VC vs PC branching
    if mode == "VC":
        test_vt = value                          # we chose the breath size
        test_pinsp = peep + (test_vt / c_new)    # → predict the plateau pressure
    else:  # PC
        test_pinsp = value                       # we chose the pressure
        test_vt = (test_pinsp - peep) * c_new    # → predict the breath size

    vt_l = test_vt / 1000.0
    pred_pplat = test_pinsp
    pred_driving_p = pred_pplat - peep
    pred_ppeak = pred_pplat + mech.resistive_gap

    # §1 Mechanical Power. In VC we use peak pressure; in PC we use plateau.
    pressure_term = pred_ppeak if mode == "VC" else pred_pplat
    pred_mp = 0.098 * rr * vt_l * (pressure_term - 0.5 * pred_driving_p)

    # §6 CO2 and pH
    valv_new = rr * (test_vt - mech.v_deadspace)
    pred_paco2 = (mech.base_valv * pt.base_paco2) / valv_new
    pred_ph = 6.1 + math.log10(pt.hco3 / (0.03 * pred_paco2))

    # §4 auto-PEEP / breath-stacking helpers
    tau = mech.r_aw * (c_new / 1000.0)
    te = (60.0 / rr) - 1.0

    return Prediction(
        mp=pred_mp, pplat=pred_pplat, driving_p=pred_driving_p, ppeak=pred_ppeak,
        vt=test_vt, ph=pred_ph, paco2=pred_paco2, tau=tau, te=te,
    )
