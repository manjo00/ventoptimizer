"""
safe_peep.py — SUB-PROBLEM 1: the highest SAFE PEEP from the current, recorded state.

Plain-language: before we can ask "which PEEP gives the least power?" we need the CEILING —
the highest PEEP this patient could be given right now without over-stretching the lung or
tripping a safety gate. This module computes that ceiling from numbers already in the chart.
It makes NO prediction of how the lung will respond (that is sub-problem 2). Instead it asks:
"if compliance stays as it is — or falls by a cautious worst-case margin — what is the highest
PEEP at which every limit still holds?"

How it works (plain steps):
  1. Read the patient's current breath: tidal volume, plateau pressure, PEEP → compliance now.
  2. Project the plateau at every candidate PEEP, assuming compliance may FALL by a margin that
     grows with the size of the step (the cautious assumption; see MARGIN_PER_CMH2O).
  3. Keep only PEEPs where plateau <= 30, driving pressure <= 15, and estimated transpulmonary
     driving pressure <= 11.7. The highest one is the mechanical ceiling.
  4. Cap it with the conventional PEEP/FiO2 envelope (ARDSNet tables) and an absolute maximum.
  5. Apply GATES: some situations forbid any PEEP increase (raised ICP, low blood pressure,
     plateau or driving pressure already over the limit, invalid mechanics); others only raise
     a caution (chest tube, vasopressor running, auto-PEEP, spontaneous breathing).
  6. Report the ceiling, which limit is binding, the oxygenation status, and every reason.

EVERY number here traces to docs/_Evidence_Base.md (tags in brackets). This is decision
support for a clinician to review — never an instruction. Aggregate-only output when run on a
dataset (`--mimic`), never a patient row.

Usage:
  python engine/safe_peep.py                       # one worked example
  python engine/safe_peep.py --mimic <MIMIC folder> # validation on recorded data (aggregates)
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------------------
# CITED CONSTANTS — tags refer to docs/_Evidence_Base.md
# ---------------------------------------------------------------------------------------
PPLAT_MAX = 30.0          # plateau pressure ceiling, cmH2O                           [E3] ARDSNet 2000
DP_MAX = 15.0             # airway driving-pressure ceiling, cmH2O                    [N9] Chiumello 2016; [E4] Amato 2015
DPL_MAX = 11.7            # transpulmonary driving-pressure ceiling, cmH2O            [N9] Chiumello 2016
EL_ERS_RATIO = 0.70       # lung / respiratory-system elastance ratio (population)    [ASSUMPTION — population average; _Research_Agenda]
SPO2_TARGET = (88.0, 95.0)   # % — oxygenation goal                                   [E3] ARDSNet
PAO2_TARGET = (55.0, 80.0)   # mmHg                                                    [E3] ARDSNet
ICP_MAX = 22.0            # mmHg — treat above this; PEEP increase forbidden above it   [N10] Brain Trauma Foundation 4th ed.
MAP_MIN = 65.0            # mmHg — initial MAP target in shock                          [N11] Surviving Sepsis Campaign 2021
PEEP_ABS_MAX = 24.0       # cmH2O — highest PEEP in the ARDSNet tables                 [E3][N7]
MARGIN_PER_CMH2O = 0.05   # cautious worst case: compliance may FALL 5% per cmH2O of PEEP increase
                          #   [ASSUMPTION — from our demo (1b): lower-quartile response ≈ −7% for a 3-cmH2O step,
                          #    worst cases ≈ −30%; to be replaced by the full-MIMIC H5 result]
MARGIN_CAP = 0.50         # never assume more than a 50% fall                           [ASSUMPTION]

# ARDSNet PEEP/FiO2 tables — the CONVENTIONAL envelope for a given FiO2 (not a target)
# lower-PEEP/higher-FiO2 table [E3] and higher-PEEP/lower-FiO2 table [N7] (ALVEOLI 2004)
FIO2_COLUMNS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
TABLE_LOWER = {0.3: [5], 0.4: [5, 8], 0.5: [8, 10], 0.6: [10], 0.7: [10, 12, 14], 0.8: [14], 0.9: [14, 16, 18], 1.0: [18, 20, 22, 24]}
TABLE_HIGHER = {0.3: [5, 8, 10, 12, 14], 0.4: [14, 16], 0.5: [16, 18, 20], 0.6: [20], 0.7: [20], 0.8: [20, 22], 0.9: [22], 1.0: [22, 24]}


@dataclass
class State:
    """Everything the ceiling needs, all from the chart. None = not available."""
    vt_ml: float
    pplat: float
    peep: float
    fio2: Optional[float] = None            # fraction (0.4) or percent (40) — both accepted
    spo2: Optional[float] = None
    pao2: Optional[float] = None
    ppeak: Optional[float] = None
    peep_total: Optional[float] = None      # measured total PEEP (set + auto-PEEP)
    rr_spont: Optional[float] = None        # spontaneous breaths per minute
    controlled_mode: bool = True
    map_mmHg: Optional[float] = None
    vasopressor_running: bool = False
    icp: Optional[float] = None
    chest_tube: bool = False
    dpl_measured: Optional[float] = None    # measured transpulmonary driving pressure (esophageal balloon), if any


@dataclass
class SafePeepResult:
    peep_now: float
    compliance_now: float
    peep_max_safe: Optional[float]          # None when mechanics are invalid
    binding_constraint: str
    projected_pplat_at_max: Optional[float]
    projected_dp_at_max: Optional[float]
    envelope_low: Optional[float]
    envelope_high: Optional[float]
    oxygenation: str
    vetoes: List[str] = field(default_factory=list)      # reasons that FORBID any PEEP increase
    cautions: List[str] = field(default_factory=list)    # reasons to be careful (no veto)
    notes: List[str] = field(default_factory=list)


def fio2_fraction(fio2):
    if fio2 is None or fio2 != fio2:          # None or NaN (a NaN never equals itself)
        return None
    return fio2 / 100.0 if fio2 > 1.0 else fio2


def table_envelope(fio2):
    """Conventional PEEP range for this FiO2: [lowest value in the lower table, highest in the higher table]."""
    f = fio2_fraction(fio2)
    if f is None:
        return None, None
    col = min(FIO2_COLUMNS, key=lambda c: abs(c - f))
    return float(min(TABLE_LOWER[col])), float(max(TABLE_HIGHER[col]))


def projected_compliance(c_now, dpeep):
    """Cautious compliance if PEEP rises by dpeep (no change assumed when PEEP falls)."""
    if dpeep <= 0:
        return c_now
    drop = min(MARGIN_PER_CMH2O * dpeep, MARGIN_CAP)
    return c_now * (1.0 - drop)


def mechanical_ceiling(vt_ml, c_now, peep_now, dpl_measured=None, step=1.0):
    """Highest PEEP (>= current) at which the projected plateau, driving pressure and
    transpulmonary driving pressure all stay under their ceilings. Returns (peep, binding, pplat, dp)."""
    best = None
    peep = peep_now
    binding = "none"
    while peep <= PEEP_ABS_MAX + 1e-9:
        c = projected_compliance(c_now, peep - peep_now)
        dp = vt_ml / c
        pplat = peep + dp
        dpl = dpl_measured * (dp / (vt_ml / c_now)) if dpl_measured is not None else dp * EL_ERS_RATIO
        if pplat > PPLAT_MAX:
            binding = f"plateau ceiling: would exceed {PPLAT_MAX:g} cmH2O [E3]"
            break
        if dp > DP_MAX:
            binding = f"driving-pressure ceiling: would exceed {DP_MAX:g} cmH2O [N9][E4]"
            break
        if dpl > DPL_MAX:
            binding = f"transpulmonary ceiling: would exceed {DPL_MAX:g} cmH2O [N9]"
            break
        best = (peep, pplat, dp)
        peep += step
    if best is not None and best[0] >= PEEP_ABS_MAX:
        binding = f"absolute maximum: {PEEP_ABS_MAX:g} cmH2O, the highest value in the ARDSNet tables [N7]"
    return best, binding


def highest_safe_peep(s: State) -> SafePeepResult:
    """The ceiling for one patient-moment, with every reason."""
    vetoes, cautions, notes = [], [], []

    # ---- validity of the mechanics ---------------------------------------------------
    peep_ref = s.peep_total if s.peep_total is not None else s.peep
    valid = True
    # Every reason is written as "category: detail" so summaries can group by category.
    if not s.controlled_mode:
        valid = False
        vetoes.append("support/spontaneous mode: plateau and compliance are not valid")
    if s.rr_spont is not None and s.rr_spont > 0:
        valid = False
        vetoes.append(f"spontaneous breaths present: {s.rr_spont:g}/min — plateau unreliable")
    if s.pplat is None or s.vt_ml is None or s.pplat <= peep_ref:
        valid = False
        vetoes.append("plateau not above PEEP: mechanics cannot be computed")
    if s.peep_total is not None and s.peep_total - s.peep >= 1:
        cautions.append(f"auto-PEEP measured: {s.peep_total - s.peep:g} cmH2O — check expiratory time (3τ rule) [E5]")

    c_now = s.vt_ml / (s.pplat - peep_ref) if valid else float("nan")
    dp_now = s.pplat - peep_ref if valid else float("nan")

    # ---- gates that FORBID any increase -----------------------------------------------
    if valid and s.pplat > PPLAT_MAX:
        vetoes.append(f"plateau already over the ceiling: {s.pplat:g} > {PPLAT_MAX:g} cmH2O [E3] — reduce first")
    if valid and dp_now > DP_MAX:
        vetoes.append(f"driving pressure already over the ceiling: {dp_now:g} > {DP_MAX:g} cmH2O [N9] — reduce tidal volume first")
    if s.icp is not None and s.icp > ICP_MAX:
        vetoes.append(f"intracranial pressure raised: {s.icp:g} > {ICP_MAX:g} mmHg [N10] — no PEEP increase")
    elif s.icp is not None:
        cautions.append("intracranial pressure monitored: raise PEEP only with neuro review [N10]")
    if s.map_mmHg is not None and s.map_mmHg < MAP_MIN:
        vetoes.append(f"mean arterial pressure below floor: {s.map_mmHg:g} < {MAP_MIN:g} mmHg [N11] — unstable; no PEEP increase")
    elif s.vasopressor_running:
        cautions.append("vasopressor running: PEEP lowers venous return; watch blood pressure [N11]")
    if s.chest_tube:
        cautions.append("chest tube present: rule out air leak before raising PEEP [ASSUMPTION: clinical convention]")

    # ---- the ceiling --------------------------------------------------------------------
    peep_max, binding, pplat_at, dp_at = None, "mechanics invalid: no ceiling", None, None
    env_low, env_high = table_envelope(s.fio2)
    if valid:
        best, binding = mechanical_ceiling(s.vt_ml, c_now, peep_ref, s.dpl_measured)
        if best is not None:
            peep_max, pplat_at, dp_at = best
        else:                                    # the CURRENT state already breaks a ceiling
            peep_max, pplat_at, dp_at = peep_ref, s.pplat, dp_now
            binding = "current state already at or over a ceiling: no increase"
        if env_high is not None and peep_max > env_high:
            peep_max = env_high
            binding = f"PEEP/FiO2 envelope top: {env_high:g} cmH2O at FiO2 {fio2_fraction(s.fio2):.2f} [E3][N7]"
            pplat_at = env_high + s.vt_ml / projected_compliance(c_now, env_high - peep_ref)
            dp_at = pplat_at - env_high
        if vetoes:
            peep_max = min(peep_max, peep_ref)
            binding = "vetoed: no increase allowed (see reasons)"

    # ---- oxygenation status (information for the clinician, not a decision) ---------------
    ox = "unknown"
    if s.spo2 is not None:
        if s.spo2 < SPO2_TARGET[0]:
            ox = f"below target (SpO2 {s.spo2:g} < {SPO2_TARGET[0]:g}%) [E3]"
        elif s.spo2 > SPO2_TARGET[1]:
            ox = f"above target (SpO2 {s.spo2:g} > {SPO2_TARGET[1]:g}%) — room to lower FiO2/PEEP [E3]"
        else:
            ox = f"within target (SpO2 {s.spo2:g}%) [E3]"
    elif s.pao2 is not None:
        ox = ("below target" if s.pao2 < PAO2_TARGET[0] else "above target" if s.pao2 > PAO2_TARGET[1] else "within target") + f" (PaO2 {s.pao2:g}) [E3]"
    if env_low is not None and valid:
        if peep_ref < env_low:
            notes.append(f"current PEEP {peep_ref:g} is below the conventional envelope [{env_low:g}–{env_high:g}] for this FiO2")
        elif peep_ref > env_high:
            notes.append(f"current PEEP {peep_ref:g} is above the conventional envelope [{env_low:g}–{env_high:g}] for this FiO2")

    return SafePeepResult(peep_now=peep_ref, compliance_now=c_now, peep_max_safe=peep_max, binding_constraint=binding,
                          projected_pplat_at_max=pplat_at, projected_dp_at_max=dp_at, envelope_low=env_low, envelope_high=env_high,
                          oxygenation=ox, vetoes=vetoes, cautions=cautions, notes=notes)


def explain(r: SafePeepResult) -> str:
    lines = [f"PEEP now {r.peep_now:g} cmH2O; compliance now {r.compliance_now:.1f} mL/cmH2O"]
    if r.peep_max_safe is None:
        lines.append("Highest safe PEEP: cannot be computed — the mechanics are not valid (see VETO)")
    else:
        lines.append(f"Highest safe PEEP: {r.peep_max_safe:g} cmH2O  (binding: {r.binding_constraint})")
        if r.projected_pplat_at_max is not None:
            lines.append(f"  at that PEEP, cautious projection: plateau {r.projected_pplat_at_max:.1f}, driving pressure {r.projected_dp_at_max:.1f} cmH2O")
    if r.envelope_low is not None:
        lines.append(f"Conventional PEEP/FiO2 envelope: {r.envelope_low:g}–{r.envelope_high:g} cmH2O")
    lines.append(f"Oxygenation: {r.oxygenation}")
    for v in r.vetoes:
        lines.append(f"  VETO: {v}")
    for c in r.cautions:
        lines.append(f"  caution: {c}")
    for n in r.notes:
        lines.append(f"  note: {n}")
    lines.append("This is a ceiling for a clinician to review — not an instruction to go there.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------
# Validation on recorded data (aggregate only)
# ---------------------------------------------------------------------------------------
def validate_on_mimic(mimic):
    import numpy as np
    import pandas as pd
    from validate_mimic import load_snapshots, fresh_plateaus, usable_peep_pairs, read_filtered

    snaps = load_snapshots(mimic)
    fresh = fresh_plateaus(snaps)
    rows = fresh[fresh["controlled"]].copy().sort_values("charttime")

    # state signals: last value before the plateau time, within a window
    ce = read_filtered(os.path.join(mimic, "icu", "chartevents.csv.gz"),
                       ["stay_id", "charttime", "itemid", "valuenum"], [220277, 223835, 220052, 220181, 220765, 224700])
    ce["charttime"] = pd.to_datetime(ce["charttime"])
    for ids, name, hours in [([220277], "spo2", 4), ([223835], "fio2", 24), ([220052, 220181], "map", 2),
                             ([220765], "icp", 2), ([224700], "peep_total", 4)]:
        sig = (ce[ce["itemid"].isin(ids)][["stay_id", "charttime", "valuenum"]]
                 .rename(columns={"valuenum": name, "charttime": "t_sig"}).sort_values("t_sig"))
        rows = pd.merge_asof(rows.sort_values("charttime"), sig, left_on="charttime", right_on="t_sig", by="stay_id",
                             direction="backward", tolerance=pd.Timedelta(hours=hours)).drop(columns=["t_sig"])
    ie = read_filtered(os.path.join(mimic, "icu", "inputevents.csv.gz"), ["stay_id", "itemid", "starttime", "endtime"],
                       [221906, 221749, 222315, 221289, 221662, 221653])
    ie["starttime"], ie["endtime"] = pd.to_datetime(ie["starttime"]), pd.to_datetime(ie["endtime"])
    oe = read_filtered(os.path.join(mimic, "icu", "outputevents.csv.gz"), ["stay_id", "itemid"], [226588, 226589])
    chest_stays = set(oe["stay_id"])

    def vaso_running(sid, t):
        g = ie[ie["stay_id"] == sid]
        return bool(((g["starttime"] <= t) & (g["endtime"] >= t)).any())

    results = []
    for _, r in rows.iterrows():
        s = State(vt_ml=r["vt"], pplat=r["pplat"], peep=r["peep"], fio2=r.get("fio2"), spo2=r.get("spo2"),
                  peep_total=None if pd.isna(r.get("peep_total")) else r.get("peep_total"),
                  rr_spont=None if pd.isna(r.get("rr_spont")) else r.get("rr_spont"), controlled_mode=True,
                  map_mmHg=None if pd.isna(r.get("map")) else r.get("map"), vasopressor_running=vaso_running(r["stay_id"], r["charttime"]),
                  icp=None if pd.isna(r.get("icp")) else r.get("icp"), chest_tube=r["stay_id"] in chest_stays)
        results.append(highest_safe_peep(s))

    n = len(results)
    computed = [x for x in results if x.peep_max_safe is not None]
    vetoed = [x for x in results if x.vetoes]
    free = [x for x in computed if not x.vetoes]              # an increase is allowed: the ceiling is a real number
    head = np.array([x.peep_max_safe - x.peep_now for x in free])
    print("=== SAFE-PEEP validation on recorded data (aggregate only) ===\n")
    print(f"Real controlled plateau moments assessed: {n} in {rows['stay_id'].nunique()} stays")
    print(f"  vetoed (no increase allowed): {len(vetoed)} ({100.0 * len(vetoed) / max(n, 1):.0f}%)   |   "
          f"increase allowed, ceiling computed: {len(free)} ({100.0 * len(free) / max(n, 1):.0f}%)")
    if len(head):
        print(f"  headroom where an increase is allowed (ceiling − current PEEP): median {np.median(head):.0f} cmH2O, "
              f"IQR {np.percentile(head, 25):.0f} to {np.percentile(head, 75):.0f}; no headroom at all: {(head <= 0).mean() * 100:.0f}%")
    category = lambda text: text.split(":")[0]
    binding = pd.Series([category(x.binding_constraint) for x in free]).value_counts()
    print("  binding constraint at the ceiling (where an increase is allowed):")
    for k, v in binding.items():
        print(f"     {k}: {v} ({100.0 * v / max(len(free), 1):.0f}%)")
    vet = pd.Series([category(v) for x in results for v in x.vetoes]).value_counts()
    cau = pd.Series([category(c) for x in results for c in x.cautions]).value_counts()
    print("  veto reasons (moments):")
    for k, v in vet.items():
        print(f"     {k}: {v}")
    print("  cautions (moments):")
    for k, v in cau.items():
        print(f"     {k}: {v}")
    ox = pd.Series([x.oxygenation.split(' (')[0] for x in results]).value_counts()
    print("  oxygenation status:")
    for k, v in ox.items():
        print(f"     {k}: {v} ({100.0 * v / max(n, 1):.0f}%)")
    env = [("below envelope" if any("below the conventional" in t for t in x.notes) else
            "above envelope" if any("above the conventional" in t for t in x.notes) else "within envelope")
           for x in computed if x.envelope_low is not None]
    if env:
        e = pd.Series(env).value_counts()
        print("  charted PEEP vs the conventional PEEP/FiO2 envelope:")
        for k, v in e.items():
            print(f"     {k}: {v} ({100.0 * v / len(env):.0f}%)")

    # did PEEP-up steps that went ABOVE our ceiling end badly more often? (usable pairs; cells < 10 suppressed)
    pairs, _ = usable_peep_pairs(snaps, fresh)
    up = pairs[pairs["dpeep"] > 0]
    over, under = [], []
    for _, r in up.iterrows():
        res = highest_safe_peep(State(vt_ml=r["vt_before"], pplat=r["pplat_before"], peep=r["peep_before"]))
        if res.peep_max_safe is None:
            continue
        (over if r["peep_after"] > res.peep_max_safe else under).append(r["frac_change"] < -0.10)
    print(f"\n  PEEP-up steps vs the ceiling computed BEFORE the step (usable pairs): went above {len(over)}, stayed at/below {len(under)}")
    for lab, v in [("above the ceiling", over), ("at/below the ceiling", under)]:
        if len(v) < 10:
            print(f"     {lab}: n={len(v)} < 10 — suppressed")
        else:
            print(f"     {lab}: compliance FELL >10% in {100.0 * np.mean(v):.0f}% (n={len(v)})")
    print("\nNothing above identifies a patient.")


def main():
    ap = argparse.ArgumentParser(description="Highest safe PEEP from the current recorded state (sub-problem 1).")
    ap.add_argument("--mimic", default=None, help="optional: MIMIC-IV folder for the aggregate validation")
    args = ap.parse_args()
    if args.mimic:
        validate_on_mimic(args.mimic)
        return
    # a worked example (invented, typical numbers — not a patient)
    s = State(vt_ml=420, pplat=24, peep=8, fio2=0.6, spo2=91, ppeak=30, rr_spont=0, map_mmHg=72,
              vasopressor_running=True, icp=None, chest_tube=False)
    print(explain(highest_safe_peep(s)))


if __name__ == "__main__":
    main()
