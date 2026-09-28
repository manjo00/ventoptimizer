"""
check_coverage.py — does a MIMIC-IV folder carry EVERY input the PEEP math needs?

Plain-language: CLAUDE.md says a dataset must contain every number our equations
use before we commit to it. This script is that check, in code form. It opens a
MIMIC-IV folder (the open 100-patient demo, or the full credentialed copy), looks
for each variable on our required list, and prints how often it is present:

  * for every variable: how many readings exist, how many ventilated ICU stays
    have at least one reading, and what share of ventilated stays that is;
  * "feasibility" counts — e.g. how many PEEP changes have a plateau pressure
    before AND after (needed to learn a patient's own PEEP response), and how
    many of those also have a blood gas / SpO2 / blood pressure nearby;
  * which ventilator modes the data was recorded in (plateau pressure is only
    meaningful in controlled, passive breathing).

It prints AGGREGATE counts only — never a patient row (governance rule).
The credentialed person runs this SAME script on the full MIMIC-IV locally and
pastes the printed table back. The variable list itself is documented for humans
in docs/_Required_Variables.md; keep the two in sync.

Usage:
  python engine/check_coverage.py --mimic data/mimic-iv-clinical-database-demo-2.2
  python engine/check_coverage.py --mimic D:/mimic-iv-3.1 --csv coverage_full.csv
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

# Make Unicode print safely on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Shared with the validation harness (one definition each, so the two scripts never drift):
# the plausibility filter, the sliced table reader, and the list of controlled ventilator modes.
from validate_mimic import physiologic_filter, read_filtered, CONTROLLED_MODES

# ---------------------------------------------------------------------------
# THE REQUIRED-VARIABLE LIST (code form of docs/_Required_Variables.md)
# Each entry: (key, plain name, group, tier, table, item codes, what it feeds)
#   tier: REQUIRED    = the math cannot run without it
#         RECOMMENDED = makes the math safer / more accurate; has a fallback
#         OPTIONAL    = nice to have, cross-checks, or rare-but-valuable
# ---------------------------------------------------------------------------
VARIABLES = [
    # --- A. Respiratory mechanics (one reading = one ventilator timepoint) ---
    ("vt_obs",     "Tidal volume (observed)",        "A mechanics", "REQUIRED",    "chartevents", [224685], "Crs, dP, MP"),
    ("vt_set",     "Tidal volume (set)",             "A mechanics", "RECOMMENDED", "chartevents", [224684], "fallback for VT"),
    ("peep_set",   "PEEP (set)",                     "A mechanics", "REQUIRED",    "chartevents", [220339], "Crs, dP, MP, the PEEP axis"),
    ("peep_total", "Total PEEP (incl. auto-PEEP)",   "A mechanics", "RECOMMENDED", "chartevents", [224700], "auto-PEEP = total - set; true dP"),
    ("pplat",      "Plateau pressure",               "A mechanics", "REQUIRED",    "chartevents", [224696], "Crs, dP, ceilings, lung stress"),
    ("ppeak",      "Peak inspiratory pressure",      "A mechanics", "REQUIRED",    "chartevents", [224695], "absolute MP (resistive part)"),
    ("rr",         "Respiratory rate (vital sign)",  "A mechanics", "REQUIRED",    "chartevents", [220210], "MP, minute ventilation"),
    ("rr_total",   "Respiratory rate (total, vent)", "A mechanics", "RECOMMENDED", "chartevents", [224690], "MP (vent-measured rate)"),
    ("rr_set",     "Respiratory rate (set)",         "A mechanics", "RECOMMENDED", "chartevents", [224688], "controlled-breath rate"),
    ("rr_spont",   "Respiratory rate (spontaneous)", "A mechanics", "RECOMMENDED", "chartevents", [224689], "passivity check (spont > 0 invalidates Pplat)"),
    ("mode",       "Ventilator mode (text)",         "A mechanics", "REQUIRED",    "chartevents", [223849, 229314], "select controlled breaths; VC vs PC MP formula"),
    ("vent_type",  "Ventilator type",                "A mechanics", "OPTIONAL",    "chartevents", [223848], "which mode vocabulary applies"),
    ("minute_vol", "Minute volume",                  "A mechanics", "OPTIONAL",    "chartevents", [224687], "VE cross-check (VT x RR)"),
    ("paw_mean",   "Mean airway pressure",           "A mechanics", "OPTIONAL",    "chartevents", [224697], "cross-check; oxygenation driver"),
    ("ti",         "Inspiratory time",               "A mechanics", "OPTIONAL",    "chartevents", [224738], "Te = 60/RR - Ti (replaces 1-s assumption)"),
    ("ie_ratio",   "I:E ratio (insp / exp)",         "A mechanics", "OPTIONAL",    "chartevents", [226873, 226871], "expiratory time"),
    ("flow",       "Inspiratory flow rate",          "A mechanics", "OPTIONAL",    "chartevents", [224691], "resistance = (Ppeak - Pplat)/flow -> tau"),
    ("vent_crs",   "Ventilator-computed compliance", "A mechanics", "OPTIONAL",    "chartevents", [229661], "cross-check of our Crs"),
    ("vent_res",   "Ventilator-computed resistance", "A mechanics", "OPTIONAL",    "chartevents", [220283, 229665, 229664], "tau cross-check"),
    ("autopeep",   "Auto-PEEP level",                "A mechanics", "OPTIONAL",    "chartevents", [224699], "air-trapping check"),
    ("psv",        "Pressure-support level",         "A mechanics", "OPTIONAL",    "chartevents", [224701], "flags support mode"),
    ("aprv",       "APRV P-high / P-low",            "A mechanics", "OPTIONAL",    "chartevents", [224705, 224706], "flags APRV (exclude)"),
    ("transpulm",  "Transpulmonary pressure (esophageal-derived)", "A mechanics", "OPTIONAL*", "chartevents", [224746, 224747], "THE missing pleural reference (validation subset)"),
    # --- B. Gas exchange / oxygenation ---
    ("fio2",       "FiO2",                           "B gas",       "REQUIRED",    "chartevents", [223835], "P/F, S/F, PEEP-FiO2 table"),
    ("spo2",       "SpO2 (pulse oximetry)",          "B gas",       "REQUIRED",    "chartevents", [220277], "oxygenation response (dense)"),
    ("pao2",       "PaO2 (chart ABG)",               "B gas",       "RECOMMENDED", "chartevents", [220224], "P/F ratio; recruitability predictor"),
    ("paco2",      "PaCO2 (chart ABG)",              "B gas",       "REQUIRED",    "chartevents", [220235], "CO2 lever; dead-space / overdistension signal"),
    ("ph",         "pH (chart ABG)",                 "B gas",       "REQUIRED",    "chartevents", [223830], "pH floor (7.30 / 7.20)"),
    ("sao2",       "SaO2 (chart ABG)",               "B gas",       "OPTIONAL",    "chartevents", [220227], "oxygenation cross-check"),
    ("tco2",       "TCO2 arterial (HCO3 proxy)",     "B gas",       "RECOMMENDED", "chartevents", [225698], "Henderson-Hasselbalch"),
    ("hco3",       "HCO3 (serum)",                   "B gas",       "RECOMMENDED", "chartevents", [227443], "Henderson-Hasselbalch"),
    ("etco2",      "EtCO2",                          "B gas",       "OPTIONAL",    "chartevents", [228640], "dead-space fraction (sparse)"),
    ("lab_abg",    "Lab ABG panel (pH/pCO2/pO2/TCO2/BE)", "B gas",  "RECOMMENDED", "labevents",   [50820, 50818, 50821, 50804, 50802], "timed gas with explicit specimen"),
    ("lab_vent",   "Lab ABG vent fields (PEEP/VT/rate at gas time)", "B gas", "OPTIONAL", "labevents", [50819, 50826, 50827], "settings at the moment of the gas"),
    ("lab_hco3",   "Bicarbonate (chemistry)",        "B gas",       "RECOMMENDED", "labevents",   [50882], "Henderson-Hasselbalch"),
    ("lab_lact",   "Lactate",                        "B gas",       "OPTIONAL",    "labevents",   [50813], "perfusion safety signal"),
    # --- C. Hemodynamics (is raising PEEP safe for the circulation?) ---
    ("map_art",    "Arterial BP mean (invasive)",    "C hemo",      "RECOMMENDED", "chartevents", [220052], "hemodynamic guard for PEEP steps"),
    ("map_nibp",   "Non-invasive BP mean",           "C hemo",      "RECOMMENDED", "chartevents", [220181], "hemodynamic guard (fallback)"),
    ("hr",         "Heart rate",                     "C hemo",      "OPTIONAL",    "chartevents", [220045], "hemodynamic guard"),
    ("cvp",        "Central venous pressure (spot)", "C hemo",      "RECOMMENDED", "chartevents", [220074], "PEEP-transmission / pleural proxy (coarse)"),
    ("vasopress",  "Vasopressor infusions",          "C hemo",      "RECOMMENDED", "inputevents", [221906, 221749, 222315, 221289, 221662, 221653], "instability gate"),
    # --- D. Gates / contraindications ---
    ("icp",        "Intracranial pressure",          "D gates",     "REQUIRED*",   "chartevents", [220765, 227989], "raised-ICP gate (no permissive hypercapnia; PEEP caution)"),
    ("chest_tube", "Chest tube (output / site / placed)", "D gates", "RECOMMENDED", "mixed",      [226588, 226589, 223993, 224438, 225433], "air-leak / pneumothorax gate"),
    ("nmb",        "Neuromuscular blocker infusion", "D gates",     "RECOMMENDED", "inputevents", [221555, 222062], "guarantees passive mechanics"),
    # --- E. Patient descriptors ---
    ("height",     "Height (cm / inches)",           "E patient",   "REQUIRED",    "chartevents", [226730, 226707], "PBW -> VT/kg limits"),
    ("weight",     "Weight (admission / daily)",     "E patient",   "RECOMMENDED", "chartevents", [226512, 224639], "BMI (chest-wall), drug dosing"),
    # --- F. Timing / cohort ---
    ("vent_proc",  "Invasive ventilation episodes",  "F timing",    "REQUIRED",    "procedureevents", [225792], "vent start/end -> days on vent, VFDs"),
    ("intub",      "Intubation / extubation events", "F timing",    "OPTIONAL",    "procedureevents", [224385, 227194], "episode boundaries"),
]

MECH_IDS = [224685, 220339, 224696, 224695, 220210]          # the pivot columns we need for compliance
MECH_NAMES = {224685: "vt", 220339: "peep", 224696: "pplat", 224695: "ppeak", 220210: "rr"}
MODE_IDS = [223849, 229314]
VENT_MARKER_IDS = [224685, 220339, 224696, 224695]           # "this stay was on a ventilator"


def per_stay_stats(sub, vent_ids):
    """rows, ventilated stays with >=1 reading, % of ventilated stays, median readings per stay."""
    sub = sub[sub["stay_id"].isin(vent_ids)]
    stays = int(sub["stay_id"].nunique())
    per = sub.groupby("stay_id").size()
    return {
        "rows": int(len(sub)),
        "stays": stays,
        "pct_vent_stays": round(100.0 * stays / max(len(vent_ids), 1), 1),
        "median_per_stay": float(per.median()) if stays else 0.0,
    }


def has_reading_within(events, signal_times_by_stay, window_h):
    """For each PEEP-change event: is there >=1 signal reading within `window_h` hours
    BEFORE the change and >=1 within `window_h` hours AFTER it?"""
    w = pd.Timedelta(hours=window_h)
    before_ok = np.zeros(len(events), dtype=bool)
    after_ok = np.zeros(len(events), dtype=bool)
    for i, (sid, tb, ta) in enumerate(zip(events["stay_id"], events["t_before"], events["t_after"])):
        times = signal_times_by_stay.get(sid)
        if times is None:
            continue
        lo = np.searchsorted(times, (tb - w).to_datetime64())
        hi = np.searchsorted(times, tb.to_datetime64(), side="right")
        before_ok[i] = hi > lo
        lo = np.searchsorted(times, ta.to_datetime64())
        hi = np.searchsorted(times, (ta + w).to_datetime64(), side="right")
        after_ok[i] = hi > lo
    return before_ok, after_ok


def times_by_stay(df):
    """{stay_id: sorted numpy array of reading times} — for fast window look-ups."""
    df = df.sort_values(["stay_id", "charttime"])
    return {sid: g["charttime"].to_numpy() for sid, g in df.groupby("stay_id")}


def build_snapshots(num, text):
    """One row per (stay, time) with vt/peep/pplat/ppeak/rr; settings forward-filled
    within a stay (same recipe as validate_mimic.load_snapshots). Also keeps two flags:
      pplat_fresh — True only where a plateau was actually charted at that time
                    (a forward-filled plateau is a STALE copy of an older reading);
      controlled  — True when the ventilator mode in force is a controlled mode
                    (plateau / compliance are only meaningful in passive, controlled breaths)."""
    m = num[num["itemid"].isin(MECH_IDS)].copy()
    m["field"] = m["itemid"].map(MECH_NAMES)
    piv = (m.pivot_table(index=["stay_id", "charttime"], columns="field",
                         values="valuenum", aggfunc="median")
             .reset_index().sort_values(["stay_id", "charttime"]))
    piv["pplat_fresh"] = piv["pplat"].notna() if "pplat" in piv.columns else False
    for c in ["vt", "peep", "pplat", "ppeak", "rr"]:
        if c in piv.columns:
            piv[c] = piv.groupby("stay_id")[c].ffill()
    # When was the plateau we are carrying actually measured? And when did PEEP last change?
    # A carried plateau is only valid for the CURRENT PEEP if it was measured after the last PEEP change.
    piv["pplat_time"] = piv["charttime"].where(piv["pplat_fresh"])
    piv["pplat_time"] = piv.groupby("stay_id")["pplat_time"].ffill()
    prev_peep = piv.groupby("stay_id")["peep"].shift()
    changed = piv["peep"].notna() & prev_peep.notna() & (piv["peep"] != prev_peep)
    piv["peep_since"] = piv["charttime"].where(changed)
    piv["peep_since"] = piv.groupby("stay_id")["peep_since"].ffill()
    # attach the ventilator mode in force at each snapshot (the last mode charted at or before it)
    mode = (text.sort_values(["stay_id", "charttime"])
                .drop_duplicates(["stay_id", "charttime"], keep="last")
                [["stay_id", "charttime", "value"]].rename(columns={"value": "mode"}))
    piv = pd.merge_asof(piv.sort_values("charttime"), mode.sort_values("charttime"),
                        on="charttime", by="stay_id", direction="backward")
    piv = piv.sort_values(["stay_id", "charttime"]).reset_index(drop=True)
    piv["controlled"] = piv["mode"].isin(CONTROLLED_MODES)
    return piv


def peep_change_events(d, look_ahead_h=4):
    """Consecutive plausible snapshots where PEEP moved by >=1 cmH2O (same rule as exp3).
    For each event also records whether the plateau values are TRUSTWORTHY:
      before_valid   — the 'before' plateau was measured while the OLD PEEP was in force
                       (not carried over from an even earlier PEEP);
      after_fresh    — a plateau was charted AT the change row itself (what exp3 silently assumed);
      after_fresh_4h — a plateau was charted within `look_ahead_h` hours after the change while
                       PEEP stayed at the new value (the honest 'after' measurement);
      controlled_both — controlled ventilator mode on both sides."""
    rows = []
    look = pd.Timedelta(hours=look_ahead_h)
    for sid, g in d.groupby("stay_id"):
        g = g.sort_values("charttime").reset_index(drop=True)
        t = g["charttime"].to_numpy()
        peep = g["peep"].to_numpy()
        fresh = g["pplat_fresh"].to_numpy()
        ctrl = g["controlled"].to_numpy()
        pplat_time = g["pplat_time"].to_numpy()
        peep_since = g["peep_since"].to_numpy()
        for i in range(1, len(g)):
            if abs(peep[i] - peep[i - 1]) < 1:
                continue
            before_valid = bool(pd.isna(peep_since[i - 1]) or pplat_time[i - 1] >= peep_since[i - 1])
            after_4h = False
            j = i
            while j < len(g) and peep[j] == peep[i] and t[j] <= t[i] + look:
                if fresh[j]:
                    after_4h = True
                    break
                j += 1
            rows.append((sid, g["charttime"][i - 1], g["charttime"][i], peep[i] - peep[i - 1],
                         before_valid, bool(fresh[i]), after_4h, bool(ctrl[i - 1] and ctrl[i])))
    return pd.DataFrame(rows, columns=["stay_id", "t_before", "t_after", "dpeep",
                                       "before_valid", "after_fresh", "after_fresh_4h", "controlled_both"])


def main():
    ap = argparse.ArgumentParser(description="Coverage check of the PEEP-math required variables on a MIMIC-IV folder.")
    ap.add_argument("--mimic", required=True, help="MIMIC-IV folder containing icu/ and hosp/")
    ap.add_argument("--csv", default=None, help="optional: also save the aggregate table to this CSV")
    args = ap.parse_args()
    base = args.mimic
    icu, hosp = os.path.join(base, "icu"), os.path.join(base, "hosp")

    # ---- 1. load the small tables --------------------------------------------------
    stays = pd.read_csv(os.path.join(icu, "icustays.csv.gz"), parse_dates=["intime", "outtime"])
    patients = pd.read_csv(os.path.join(hosp, "patients.csv.gz"))
    adm = pd.read_csv(os.path.join(hosp, "admissions.csv.gz"), usecols=["hadm_id", "hospital_expire_flag", "deathtime"])

    # ---- 2. load the big tables, filtered to our codes ------------------------------
    chart_ids = sorted({i for v in VARIABLES if v[4] in ("chartevents", "mixed") for i in v[5]})
    ce = read_filtered(os.path.join(icu, "chartevents.csv.gz"),
                       ["stay_id", "charttime", "itemid", "value", "valuenum"], chart_ids)
    ce["charttime"] = pd.to_datetime(ce["charttime"])
    text = ce[ce["itemid"].isin(MODE_IDS)][["stay_id", "charttime", "itemid", "value"]]   # mode strings
    num = ce.drop(columns=["value"])
    del ce

    input_ids = sorted({i for v in VARIABLES if v[4] == "inputevents" for i in v[5]})
    ie = read_filtered(os.path.join(icu, "inputevents.csv.gz"), ["stay_id", "itemid"], input_ids)
    oe = read_filtered(os.path.join(icu, "outputevents.csv.gz"), ["stay_id", "itemid"], [226588, 226589])
    proc_ids = sorted({i for v in VARIABLES if v[4] in ("procedureevents", "mixed") for i in v[5]})
    pe = read_filtered(os.path.join(icu, "procedureevents.csv.gz"),
                       ["stay_id", "itemid", "starttime", "endtime"], proc_ids)
    lab_ids = sorted({i for v in VARIABLES if v[4] == "labevents" for i in v[5]})
    le = read_filtered(os.path.join(hosp, "labevents.csv.gz"), ["hadm_id", "charttime", "itemid"], lab_ids)
    le["charttime"] = pd.to_datetime(le["charttime"])
    # attach a stay_id to each lab by admission + time inside the ICU stay window
    le = le.merge(stays[["hadm_id", "stay_id", "intime", "outtime"]], on="hadm_id", how="inner")
    le = le[(le["charttime"] >= le["intime"]) & (le["charttime"] <= le["outtime"])][["stay_id", "charttime", "itemid"]]

    # ---- 3. the cohort denominator ---------------------------------------------------
    vent_ids = set(num.loc[num["itemid"].isin(VENT_MARKER_IDS), "stay_id"])
    proc_vent_ids = set(pe.loc[pe["itemid"] == 225792, "stay_id"])
    n_vent = len(vent_ids)
    print("=" * 78)
    print("COHORT")
    print(f"  ICU stays in folder ................. {len(stays)}")
    print(f"  ventilated stays (any vent setting) . {n_vent}   <- denominator for '% vent stays'")
    print(f"  stays with an 'Invasive Ventilation' procedure record: {len(proc_vent_ids)} "
          f"(overlap with chart-based: {len(vent_ids & proc_vent_ids)})")

    # ---- 4. per-variable coverage ----------------------------------------------------
    by_table = {"chartevents": num, "inputevents": ie, "labevents": le, "procedureevents": pe,
                "mixed": pd.concat([num[["stay_id", "itemid"]], oe[["stay_id", "itemid"]], pe[["stay_id", "itemid"]]])}
    rows = []
    for key, name, group, tier, table, ids, feeds in VARIABLES:
        src = by_table[table]
        st = per_stay_stats(src[src["itemid"].isin(ids)], vent_ids)
        rows.append({"group": group, "variable": name, "codes": " ".join(map(str, ids)), "tier": tier,
                     "rows": st["rows"], "stays": st["stays"], "pct_vent_stays": st["pct_vent_stays"],
                     "median_per_stay": st["median_per_stay"], "feeds": feeds})
    # demographics + outcomes (from the small tables, keyed by subject / admission)
    vs = stays[stays["stay_id"].isin(vent_ids)].merge(patients, on="subject_id", how="left").merge(adm, on="hadm_id", how="left")
    rows.append({"group": "E patient", "variable": "Sex + age (patients table)", "codes": "gender anchor_age", "tier": "REQUIRED",
                 "rows": int(vs["gender"].notna().sum()), "stays": int(vs["gender"].notna().sum()),
                 "pct_vent_stays": round(100.0 * vs["gender"].notna().mean(), 1), "median_per_stay": 1.0, "feeds": "PBW formula"})
    omr_path = os.path.join(hosp, "omr.csv.gz")
    if os.path.exists(omr_path):
        omr = pd.read_csv(omr_path, usecols=["subject_id", "result_name"])
        omr_h = set(omr.loc[omr["result_name"].str.contains("Height", na=False), "subject_id"])
        chart_h = set(num.loc[num["itemid"].isin([226730, 226707]), "stay_id"])
        any_h = vs["stay_id"].isin(chart_h) | vs["subject_id"].isin(omr_h)
        rows.append({"group": "E patient", "variable": "Height from ANY source (chart or outpatient OMR)", "codes": "226730 226707 +omr", "tier": "REQUIRED",
                     "rows": int(any_h.sum()), "stays": int(any_h.sum()), "pct_vent_stays": round(100.0 * any_h.mean(), 1),
                     "median_per_stay": 1.0, "feeds": "PBW (fallback source)"})
    dead_hosp = vs["hospital_expire_flag"].fillna(0).astype(int)
    dod = pd.to_datetime(vs["dod"], errors="coerce")
    dead_28 = (dod.notna()) & (dod <= vs["intime"] + pd.Timedelta(days=28))
    rows.append({"group": "G outcome", "variable": "Mortality (hospital flag / date of death)", "codes": "hospital_expire_flag dod", "tier": "REQUIRED (validation)",
                 "rows": int(dead_hosp.sum()), "stays": int(len(vs)), "pct_vent_stays": 100.0, "median_per_stay": 1.0,
                 "feeds": f"in-hospital deaths {int(dead_hosp.sum())} ({100.0 * dead_hosp.mean():.1f}%); 28-day deaths {int(dead_28.sum())} ({100.0 * dead_28.mean():.1f}%)"})

    table = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_colwidth", 60)
    print("\n" + "=" * 78)
    print("PER-VARIABLE COVERAGE  (stays = ventilated stays with >=1 reading)")
    print(table[["group", "variable", "codes", "tier", "rows", "stays", "pct_vent_stays", "median_per_stay"]].to_string(index=False))
    print("  outcome detail:", rows[-1]["feeds"])
    if args.csv:
        table.to_csv(args.csv, index=False)
        print(f"\n(saved aggregate table to {args.csv})")

    # ---- 5. feasibility of the actual PEEP math ------------------------------------
    piv = build_snapshots(num, text)
    d = physiologic_filter(piv)                         # plausible snapshots with compliance
    ev = peep_change_events(d)
    gas = num[num["itemid"].isin([220235, 220224, 223830])]
    spo2 = num[num["itemid"] == 220277]
    fio2 = num[num["itemid"] == 223835]
    mapbp = num[num["itemid"].isin([220052, 220181])]
    levels = d.groupby("stay_id")["peep"].nunique()
    levels_fresh = d[d["pplat_fresh"]].groupby("stay_id")["peep"].nunique()
    pct = lambda mask: f"{int(mask.sum())} ({100.0 * mask.mean():.0f}%)" if len(mask) else "0"
    print("\n" + "=" * 78)
    print("FEASIBILITY OF THE PEEP MATH")
    print(f"  snapshots with VT + PEEP + Pplat (compliance computable) ... {len(d)}  in {d['stay_id'].nunique()} stays")
    print(f"     ...with a FRESHLY charted plateau (not forward-filled) .. {int(d['pplat_fresh'].sum())}")
    print(f"     ...in a CONTROLLED ventilator mode ...................... {int(d['controlled'].sum())}")
    print(f"  PEEP-change events with Pplat before AND after ............. {len(ev)}  in {ev['stay_id'].nunique() if len(ev) else 0} stays"
          f"   (up: {int((ev['dpeep'] > 0).sum()) if len(ev) else 0}, down: {int((ev['dpeep'] < 0).sum()) if len(ev) else 0})")
    if len(ev):
        usable = ev["before_valid"] & ev["after_fresh_4h"]
        print(f"     ...'before' plateau measured under the OLD PEEP ......... {pct(ev['before_valid'])}")
        print(f"     ...'after' plateau charted AT the change row ............ {pct(ev['after_fresh'])}   <- what exp2/exp3 silently used")
        print(f"     ...'after' plateau charted within 4h at the NEW PEEP .... {pct(ev['after_fresh_4h'])}")
        print(f"     ...USABLE pairs (before valid AND fresh after <=4h) ...... {pct(usable)}")
        print(f"     ...usable AND controlled mode on both sides ............. {pct(usable & ev['controlled_both'])}")
        print(f"     ...CONTROLLED mode on both sides (all events) ........... {pct(ev['controlled_both'])}")
    print(f"  stays with >=2 distinct PEEP levels (own slope possible) ... {int((levels >= 2).sum())}   (>=3 levels: {int((levels >= 3).sum())})")
    print(f"     ...counting only fresh-plateau snapshots ................ {int((levels_fresh >= 2).sum())}   (>=3 levels: {int((levels_fresh >= 3).sum())})")
    if len(ev):
        for label, sig, w in [("arterial blood gas (chart)", gas, 2), ("SpO2", spo2, 1),
                              ("FiO2 (a setting, charted less often)", fio2, 4), ("mean BP", mapbp, 1)]:
            b, a = has_reading_within(ev, times_by_stay(sig), w)
            print(f"  ...events with {label:<38} within +/-{w}h before AND after: {pct(b & a)}")
    print(f"  stays with esophageal-derived transpulmonary pressure ...... {num.loc[num['itemid'].isin([224746, 224747]), 'stay_id'].nunique()}")
    print(f"  stays with spot CVP ........................................ {num.loc[num['itemid'] == 220074, 'stay_id'].nunique()}")

    # ---- 6. ventilator modes (plateau/compliance only valid in controlled breaths) ---
    print("\n" + "=" * 78)
    print("VENTILATOR MODES (rows of mode text; '*' = counted as CONTROLLED)")
    vc = text["value"].value_counts()
    ctrl = 0
    for mode, n in vc.items():
        flag = "*" if mode in CONTROLLED_MODES else " "
        ctrl += n if flag == "*" else 0
        print(f"  {flag} {mode:<24} {n}")
    if len(text):
        print(f"  controlled share of mode rows: {100.0 * ctrl / len(text):.0f}%")
    unknown = [m for m in vc.index if m not in CONTROLLED_MODES and m not in {
        "CPAP/PSV", "PSV/SBT", "Standby", "MMV/PSV/AutoFlow", "CPAP/PSV+ApnVol", "MMV/PSV", "CPAP", "CPAP/PPS",
        "CPAP/PSV+ApnPres", "SPONT", "VS", "NIV", "NIV-ST", "ASV", "APRV", "PCV+/PSV", "MMV", "MMV/AutoFlow", "SYNCHRON MASTER", "SYNCHRON SLAVE", "Apnea Ventilation"}]
    if unknown:
        print(f"  mode strings not yet classified (tell Claude): {unknown}")

    # ---- 7. verdict -------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("VERDICT — REQUIRED variables below 90% of ventilated stays")
    print("  (gates marked REQUIRED* are only required WHEN PRESENT, so they are not flagged)")
    weak = table[table["tier"].str.startswith("REQUIRED") & ~table["tier"].str.endswith("*")
                 & (table["pct_vent_stays"] < 90)]
    if len(weak):
        for _, r in weak.iterrows():
            print(f"  ! {r['variable']:<50} {r['pct_vent_stays']}%")
    else:
        print("  none — every REQUIRED variable is present in >=90% of ventilated stays")
    print("=" * 78)


if __name__ == "__main__":
    main()
