"""
check_coverage_other.py — does an eICU or AmsterdamUMCdb folder carry EVERY input the PEEP math needs?

Plain-language: `check_coverage.py` answers this question for MIMIC-IV. This script
answers the SAME question for the two other open ICU databases we may use as a second
dataset (multi-centre validation, or more plateau readings for the PEEP work):

  * eICU Collaborative Research Database (PhysioNet, ~200k stays, 208 US hospitals)
  * AmsterdamUMCdb (Amsterdam UMC, ~23k admissions; free application, not PhysioNet)

The two databases store the same physiology under different names (MIMIC uses numeric
item codes, eICU uses text labels such as "Plateau Pressure", AmsterdamUMCdb uses
Dutch/English item names such as "Plateau druk"). So the script works in two steps:

  1. TRANSLATE — read each database's tables and map every reading we recognise onto
     our common variable names (vt, peep, pplat, ppeak, rr, fio2, ...). Each dataset
     has its own small translation table below (regular expressions on the label text).
     Because label spellings vary between hospitals, the script also prints a LABEL
     AUDIT: which labels it matched, and the most frequent labels it did NOT match,
     so a miss can be added to the translation table and the check re-run.
  2. CHECK — the same questions as for MIMIC: how often is each required variable
     present in ventilated stays; how many PEEP changes have a trustworthy plateau on
     both sides (the usable pairs sub-problem 2 needs); which ventilator modes appear.

It prints AGGREGATE counts only — never a patient row (governance rule). Item labels
and mode strings are metadata, not patient data, so they are safe to paste back.

Usage (run locally by the credentialed person, paste the printed output back):
  python engine/check_coverage_other.py --dataset eicu      --path D:/eicu-2.0 --csv coverage_eicu.csv
  python engine/check_coverage_other.py --dataset amsterdam --path D:/AmsterdamUMCdb --csv coverage_ams.csv
  add --quick to read only the first slices of the big tables (a 5-minute smoke test of
  the translation tables; the counts are then NOT the real coverage).

Honest limits (also in docs/_Required_Variables.md §7):
  * eICU records deaths only up to hospital discharge, so "28-day mortality" there is
    in-hospital death within 28 days of ICU admission — not the manuscript's definition.
  * AmsterdamUMCdb gives height and weight as 10-cm / 10-kg BANDS, so predicted body
    weight carries about +/-5 cm of height uncertainty (flagged in the output).
  * Our translation tables were written from the published data dictionaries, not from
    the data itself (we cannot download either database into a cloud session). The
    label audit is there precisely so the first real run can correct them.
"""

import argparse
import os
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# the plausibility filter is shared with the MIMIC scripts so all datasets use one rule
from validate_mimic import physiologic_filter

# ---------------------------------------------------------------------------
# THE COMMON REQUIRED-VARIABLE LIST (same tiers as check_coverage.py / _Required_Variables.md §2)
#   key, plain name, group, tier, what it feeds
# ---------------------------------------------------------------------------
VARIABLES = [
    ("vt",         "Tidal volume (observed/exhaled)",   "A mechanics", "REQUIRED",    "Crs, dP, MP"),
    ("vt_set",     "Tidal volume (set)",                "A mechanics", "RECOMMENDED", "fallback for VT"),
    ("peep",       "PEEP (set)",                        "A mechanics", "REQUIRED",    "Crs, dP, MP, the PEEP axis"),
    ("peep_total", "Total / intrinsic PEEP",            "A mechanics", "RECOMMENDED", "auto-PEEP; true dP"),
    ("pplat",      "Plateau pressure",                  "A mechanics", "REQUIRED",    "Crs, dP, ceilings, lung stress"),
    ("ppeak",      "Peak inspiratory pressure",         "A mechanics", "REQUIRED",    "absolute MP (resistive part)"),
    ("rr",         "Respiratory rate (any source)",     "A mechanics", "REQUIRED",    "MP, minute ventilation"),
    ("rr_set",     "Respiratory rate (set)",            "A mechanics", "RECOMMENDED", "controlled-breath rate"),
    ("rr_spont",   "Respiratory rate (spontaneous)",    "A mechanics", "RECOMMENDED", "passivity check"),
    ("mode",       "Ventilator mode (text)",            "A mechanics", "REQUIRED",    "select controlled breaths; VC vs PC formula"),
    ("minute_vol", "Minute volume",                     "A mechanics", "OPTIONAL",    "VE cross-check"),
    ("paw_mean",   "Mean airway pressure",              "A mechanics", "OPTIONAL",    "cross-check"),
    ("ti",         "Inspiratory time",                  "A mechanics", "OPTIONAL",    "Te = 60/RR - Ti"),
    ("ie_ratio",   "I:E ratio",                         "A mechanics", "OPTIONAL",    "expiratory time"),
    ("flow",       "Inspiratory / peak flow",           "A mechanics", "OPTIONAL",    "resistance -> tau"),
    ("vent_crs",   "Ventilator-computed compliance",    "A mechanics", "OPTIONAL",    "cross-check of our Crs"),
    ("vent_res",   "Ventilator-computed resistance",    "A mechanics", "OPTIONAL",    "tau cross-check"),
    ("autopeep",   "Auto-PEEP level",                   "A mechanics", "OPTIONAL",    "air-trapping check"),
    ("psv",        "Pressure-support level",            "A mechanics", "OPTIONAL",    "flags support mode"),
    ("aprv",       "APRV P-high / P-low",               "A mechanics", "OPTIONAL",    "flags APRV (exclude)"),
    ("transpulm",  "Transpulmonary / esophageal pressure", "A mechanics", "OPTIONAL*", "THE missing pleural reference"),
    ("fio2",       "FiO2",                              "B gas",       "REQUIRED",    "P/F, S/F, PEEP-FiO2 table"),
    ("spo2",       "SpO2 (pulse oximetry)",             "B gas",       "REQUIRED",    "oxygenation response (dense)"),
    ("pao2",       "PaO2",                              "B gas",       "RECOMMENDED", "P/F ratio"),
    ("paco2",      "PaCO2",                             "B gas",       "REQUIRED",    "CO2 lever; dead-space signal"),
    ("ph",         "pH",                                "B gas",       "REQUIRED",    "pH floor (7.30 / 7.20)"),
    ("hco3",       "HCO3 / bicarbonate",                "B gas",       "RECOMMENDED", "Henderson-Hasselbalch"),
    ("lactate",    "Lactate",                           "B gas",       "OPTIONAL",    "perfusion safety signal"),
    ("etco2",      "EtCO2",                             "B gas",       "OPTIONAL",    "dead-space fraction"),
    ("map",        "Mean arterial pressure (invasive)", "C hemo",      "RECOMMENDED", "hemodynamic guard for PEEP steps"),
    ("map_nibp",   "Mean BP (non-invasive)",            "C hemo",      "RECOMMENDED", "hemodynamic guard (fallback)"),
    ("hr",         "Heart rate",                        "C hemo",      "OPTIONAL",    "hemodynamic guard"),
    ("cvp",        "Central venous pressure",           "C hemo",      "RECOMMENDED", "PEEP-transmission / pleural proxy"),
    ("vasopress",  "Vasopressor infusions",             "C hemo",      "RECOMMENDED", "instability gate"),
    ("icp",        "Intracranial pressure",             "D gates",     "REQUIRED*",   "raised-ICP gate"),
    ("chest_tube", "Chest tube",                        "D gates",     "RECOMMENDED", "air-leak gate"),
    ("nmb",        "Neuromuscular blocker",             "D gates",     "RECOMMENDED", "guarantees passive mechanics"),
    ("height",     "Height",                            "E patient",   "REQUIRED",    "PBW -> VT/kg limits"),
    ("sex_age",    "Sex + age",                         "E patient",   "REQUIRED",    "PBW formula"),
    ("weight",     "Weight",                            "E patient",   "RECOMMENDED", "BMI (chest wall)"),
    ("vent_proc",  "Ventilation episodes (start/end)",  "F timing",    "REQUIRED",    "time on vent, cohort"),
    ("mortality",  "Mortality (date / flag)",           "G outcome",   "REQUIRED (validation)", "28-day outcome"),
]
TIER = {v[0]: v[3] for v in VARIABLES}
MECH = ["vt", "peep", "pplat", "ppeak", "rr"]

# ---------------------------------------------------------------------------
# TRANSLATION TABLES — ordered: the FIRST pattern that matches a label wins.
# Written from the published data dictionaries; the label audit corrects them.
# ---------------------------------------------------------------------------
EICU_RESP_LABELS = [   # respiratoryCharting.respchartvaluelabel
    ("mode",       r"^(vent(ilator)?\s*)?mode$|ventilator\s*mode|vent\s*mode"),
    ("aprv",       r"p\s*high|p\s*low|aprv"),
    ("psv",        r"pressure\s*support|\bPS\b(?!V)|PSV level"),
    ("vt_set",     r"tidal\s*volume\s*\(set\)|set\s*tidal|\bVt\s*set|TV\s*\(set\)|tidal volume set"),
    ("vt",         r"tidal\s*volume|exhaled\s*(tv|vt)|\bTV\b|\bVt\b|VTe"),
    ("peep_total", r"total\s*peep|intrinsic\s*peep"),
    ("autopeep",   r"auto[\s-]*peep"),
    ("peep",       r"\bpeep\b"),
    ("pplat",      r"plateau"),
    ("ppeak",      r"peak\s*insp|peak\s*pressure|\bPIP\b|peak airway"),
    ("paw_mean",   r"mean\s*airway"),
    ("rr_set",     r"vent\s*rate|set\s*rate|rate\s*\(set\)|rr\s*\(set\)|resp(iratory)?\s*rate\s*\(set\)"),
    ("rr_spont",   r"spont|rr\s*\(patient\)|patient\s*rate"),
    ("rr",         r"total\s*rr|\brr\b|resp(iratory)?\s*rate|resp\s*rate\s*total"),
    ("fio2",       r"fio2|oxygen\s*%|o2\s*%"),
    ("minute_vol", r"minute\s*vol|exhaled\s*mv|\bMV\b|\bVE\b"),
    ("ti",         r"insp(iratory)?\s*time|\bTi\b|i-time"),
    ("ie_ratio",   r"i\s*:\s*e|ie\s*ratio"),
    ("flow",       r"peak\s*flow|insp(iratory)?\s*flow"),
    ("vent_crs",   r"compliance"),
    ("vent_res",   r"resistance"),
    ("transpulm",  r"esoph|transpulm"),
    ("etco2",      r"etco2|end\s*tidal"),
    ("spo2",       r"spo2|sao2|o2\s*sat"),
]
EICU_LAB_LABELS = [    # lab.labname
    ("pao2",    r"^pao2$"),
    ("paco2",   r"^paco2$"),
    ("ph",      r"^ph$"),
    ("hco3",    r"^hco3$|^bicarbonate$|^total co2$"),
    ("lactate", r"^lactate$"),
    ("fio2",    r"^fio2$"),
    ("peep",    r"^peep$"),
    ("vt",      r"^tv$"),
    ("rr_set",  r"^vent rate$"),
]
EICU_VITAL_COLS = {"sao2": "spo2", "systemicmean": "map", "cvp": "cvp", "icp": "icp",
                   "etco2": "etco2", "heartrate": "hr", "respiration": "rr"}
EICU_VASOPRESSORS = r"norepinephrine|levophed|epinephrine|adrenalin|vasopressin|phenylephrine|neo-?synephrine|dopamine|dobutamine"
EICU_NMB = r"cisatracurium|nimbex|vecuronium|rocuronium|atracurium|pancuronium"

AMS_NUMERIC_ITEMS = [   # numericitems.item (Dutch and English spellings)
    ("aprv",       r"p\s*high|p\s*low|aprv"),
    ("psv",        r"pressure\s*support|drukondersteuning|\bASB\b|\bPS\s*\(set\)|ondersteuning"),
    ("vt_set",     r"(tidal|teug).*(set|ingesteld)|(set|ingesteld).*(tidal|teug)"),
    ("vt",         r"tidal|teugvolume|\bVt\b|\bVTe\b"),
    ("peep_total", r"(totaal|total|intrinsi).*peep|peep.*(totaal|total|intrinsi)"),
    ("autopeep",   r"auto.?peep"),
    ("peep",       r"\bpeep\b"),
    ("pplat",      r"plateau"),
    ("ppeak",      r"piek|peak|\bPIP\b"),
    ("paw_mean",   r"gemiddelde\s*(luchtweg)?druk|mean\s*airway|\bPmean\b"),
    ("rr_set",     r"(ademfreq|frequentie|resp.*rate|\bRR\b).*(set|ingesteld)|(set|ingesteld).*(ademfreq|frequentie|rate)"),
    ("rr_spont",   r"spont"),
    ("rr",         r"ademfreq|ademhalingsfreq|adem\s*frequentie|resp(iratory)?\s*rate|\bRR\b|frequentie\s*\(gemeten\)"),
    ("fio2",       r"fio2|o2\s*concentratie|o2\s*%|zuurstof\s*%"),
    ("minute_vol", r"minuut\s*volume|minute\s*vol|\bMV\b|\bVE\b"),
    ("ti",         r"insp.*tijd|insp(iratory)?\s*time|\bTi\b"),
    ("ie_ratio",   r"i\s*:\s*e|ie\s*ratio|i/e"),
    ("flow",       r"\bflow\b"),
    ("vent_crs",   r"compliance"),
    ("vent_res",   r"resistance|weerstand"),
    ("transpulm",  r"oesof|esof|transpulm|\bPes\b"),
    ("etco2",      r"etco2|end\s*tidal|eindexpiratoir"),
    ("spo2",       r"saturatie|\bspo2\b|o2\s*sat"),
    ("pao2",       r"\bpo2\b|pao2"),
    ("paco2",      r"\bpco2\b|paco2"),
    ("ph",         r"^ph\b|\bph\s*\(|\bph$"),
    ("hco3",       r"hco3|bicarbonaat|bicarbonate"),
    ("lactate",    r"lactaat|lactate"),
    ("map_nibp",   r"niet\s*invasie.*(gemiddeld|mean)|nibp.*(mean|gemiddeld)|non.?invasive.*mean"),
    ("map",        r"abp\s*gemiddeld|arterial.*mean|\bMAP\b|gemiddelde\s*bloeddruk|art.*gemiddeld"),
    ("cvp",        r"\bcvd\b|\bcvp\b|centraal\s*veneu"),
    ("icp",        r"\bicp\b|intracran"),
    ("hr",         r"hartfreq|heart\s*rate|\bHR\b"),
    ("height",     r"lengte|height"),
    ("weight",     r"gewicht|weight"),
]
AMS_LIST_ITEMS = [      # listitems.item (text-valued settings)
    ("mode", r"ventilatie\s*mode|beademings?\s*mode|vent.*mode|\bmode\b"),
]
AMS_VASOPRESSORS = r"noradrenaline|norepinefrine|norepinephrine|adrenaline|epinefrine|epinephrine|vasopressine|vasopressin|dopamine|dobutamine|fenylefrine|phenylephrine"
AMS_NMB = r"rocuronium|esmeron|cisatracurium|nimbex|atracurium|vecuronium|pancuronium"
AMS_VENT_PROCESS = r"beadem|ventil|intubatie|tube"
AMS_CHEST_TUBE = r"thoraxdrain|thorax\s*drain|chest\s*tube|pleuradrain"

# Mode classification: the same decision as MIMIC's CONTROLLED_MODES (SIMV counts as controlled;
# support, CPAP, APRV, spontaneous, NIV and standby do not). Exclusions are tested first.
MODE_NOT_CONTROLLED = re.compile(r"cpap|\bps\b|psv|support|aprv|spont|bipap|bi-?vent|niv|sbt|stand.?by|\basv\b|\bmmv\b|nava|\basb\b|\bcsv\b|trial", re.I)
MODE_CONTROLLED = re.compile(r"a/?c\b|\bac\b|cmv|prvc|\bvc\b|\bpc\b|pcv|vcv|simv|assist|control|volume|pressure\s*control|\bimv\b", re.I)


def is_controlled(mode_text):
    s = str(mode_text)
    if MODE_NOT_CONTROLLED.search(s):
        return False
    return bool(MODE_CONTROLLED.search(s))


def label_mapper(table):
    """Return a function label -> variable key (or None), caching each distinct label.
    Only the label TEXT is cached — never a value."""
    compiled = [(key, re.compile(pat, re.I)) for key, pat in table]
    cache = {}

    def f(label):
        if label in cache:
            return cache[label]
        s = "" if label is None or (isinstance(label, float) and np.isnan(label)) else str(label).strip()
        key = None
        for k, rx in compiled:
            if rx.search(s):
                key = k
                break
        cache[label] = key
        return key
    return f


def to_num(series):
    """'21%' -> 21, '0.4' -> 0.4, text -> NaN."""
    return pd.to_numeric(series.astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False).str.strip(),
                         errors="coerce")


def find_file(folder, *candidates):
    """The databases ship as .csv or .csv.gz with varying capitalisation; find whichever exists."""
    listing = {f.lower(): f for f in os.listdir(folder)}
    for c in candidates:
        for ext in ("", ".gz"):
            name = (c + ext).lower()
            if name in listing:
                return os.path.join(folder, listing[name])
    raise FileNotFoundError(f"none of {candidates} found in {folder}")


def read_chunks(path, usecols, chunksize, max_chunks, label):
    n = 0
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False):
        n += 1
        yield chunk
        if n % 10 == 0:
            print(f"    ...{label}: {n * chunksize / 1e6:.0f}M rows read", flush=True)
        if max_chunks and n >= max_chunks:
            print(f"    ...{label}: stopped after {n} slices (--quick)")
            break


# ---------------------------------------------------------------------------
# LOADERS — each returns the same bundle:
#   num   : DataFrame[stay_id, t, var, value]   t = minutes from ICU/unit admission
#   modes : DataFrame[stay_id, t, mode]
#   stays : DataFrame[stay_id, height_ok, sex_age_ok, weight_ok, dead_hosp, dead_28, vent_episode, chest_tube,
#                     vasopress, nmb]  (one row per stay; booleans/ints only)
#   audit : dict label -> (var key or None, row count)   for the label audit
#   notes : list of plain-language caveats to print
# ---------------------------------------------------------------------------
def load_eicu(base, chunksize, max_chunks):
    notes = []
    audit = Counter()
    mapped = Counter()
    rmap = label_mapper(EICU_RESP_LABELS)

    print("  reading patient.csv ...")
    pt = pd.read_csv(find_file(base, "patient.csv"),
                     usecols=["patientunitstayid", "gender", "age", "admissionheight", "admissionweight",
                              "hospitaldischargeoffset", "hospitaldischargestatus", "unitdischargestatus"])
    pt = pt.rename(columns={"patientunitstayid": "stay_id"})

    print("  reading respiratoryCharting.csv (the ventilator flowsheet) ...")
    parts, mode_parts = [], []
    for ch in read_chunks(find_file(base, "respiratoryCharting.csv"),
                          ["patientunitstayid", "respchartoffset", "respchartvaluelabel", "respchartvalue"],
                          chunksize, max_chunks, "respiratoryCharting"):
        labels = ch["respchartvaluelabel"]
        audit.update(labels.value_counts().to_dict())
        ch["var"] = labels.map(rmap)
        ch = ch[ch["var"].notna()]
        mapped.update(ch["respchartvaluelabel"].value_counts().to_dict())
        ch = ch.rename(columns={"patientunitstayid": "stay_id", "respchartoffset": "t"})
        m = ch[ch["var"] == "mode"]
        if len(m):
            mode_parts.append(m[["stay_id", "t", "respchartvalue"]].rename(columns={"respchartvalue": "mode"}))
        ch = ch[ch["var"] != "mode"].copy()
        ch["value"] = to_num(ch["respchartvalue"])
        parts.append(ch[["stay_id", "t", "var", "value"]])
    num = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["stay_id", "t", "var", "value"])
    modes = pd.concat(mode_parts, ignore_index=True) if mode_parts else pd.DataFrame(columns=["stay_id", "t", "mode"])
    vent_ids = set(num.loc[num["var"].isin(["vt", "peep", "pplat", "ppeak"]), "stay_id"])

    print("  reading lab.csv (blood gases) ...")
    lmap = label_mapper(EICU_LAB_LABELS)
    lparts = []
    for ch in read_chunks(find_file(base, "lab.csv"), ["patientunitstayid", "labresultoffset", "labname", "labresult"],
                          chunksize, max_chunks, "lab"):
        ch["var"] = ch["labname"].map(lmap)
        ch = ch[ch["var"].notna() & ch["patientunitstayid"].isin(vent_ids)]
        lparts.append(ch.rename(columns={"patientunitstayid": "stay_id", "labresultoffset": "t", "labresult": "value"})
                        [["stay_id", "t", "var", "value"]])
    if lparts:
        num = pd.concat([num] + lparts, ignore_index=True)

    print("  reading vitalPeriodic.csv (SpO2, MAP, CVP, ICP every 5 min — the biggest table) ...")
    vparts = []
    cols = ["patientunitstayid", "observationoffset"] + list(EICU_VITAL_COLS)
    for ch in read_chunks(find_file(base, "vitalPeriodic.csv"), cols, chunksize, max_chunks, "vitalPeriodic"):
        ch = ch[ch["patientunitstayid"].isin(vent_ids)]
        if not len(ch):
            continue
        long = ch.melt(id_vars=["patientunitstayid", "observationoffset"], value_vars=list(EICU_VITAL_COLS),
                       var_name="col", value_name="value").dropna(subset=["value"])
        long["var"] = long["col"].map(EICU_VITAL_COLS)
        vparts.append(long.rename(columns={"patientunitstayid": "stay_id", "observationoffset": "t"})
                          [["stay_id", "t", "var", "value"]])
    if vparts:
        num = pd.concat([num] + vparts, ignore_index=True)
    try:
        print("  reading vitalAperiodic.csv (cuff blood pressure) ...")
        aparts = []
        for ch in read_chunks(find_file(base, "vitalAperiodic.csv"), ["patientunitstayid", "observationoffset", "noninvasivemean"],
                              chunksize, max_chunks, "vitalAperiodic"):
            ch = ch[ch["patientunitstayid"].isin(vent_ids)].dropna(subset=["noninvasivemean"])
            ch["var"] = "map_nibp"
            aparts.append(ch.rename(columns={"patientunitstayid": "stay_id", "observationoffset": "t", "noninvasivemean": "value"})
                            [["stay_id", "t", "var", "value"]])
        if aparts:
            num = pd.concat([num] + aparts, ignore_index=True)
    except FileNotFoundError:
        notes.append("vitalAperiodic.csv not found — cuff blood pressure skipped")

    print("  reading infusionDrug.csv, treatment.csv, respiratoryCare.csv ...")
    inf = pd.read_csv(find_file(base, "infusionDrug.csv"), usecols=["patientunitstayid", "drugname"])
    vaso_ids = set(inf.loc[inf["drugname"].astype(str).str.contains(EICU_VASOPRESSORS, case=False, regex=True), "patientunitstayid"])
    nmb_ids = set(inf.loc[inf["drugname"].astype(str).str.contains(EICU_NMB, case=False, regex=True), "patientunitstayid"])
    tr = pd.read_csv(find_file(base, "treatment.csv"), usecols=["patientunitstayid", "treatmentstring"])
    ct_ids = set(tr.loc[tr["treatmentstring"].astype(str).str.contains("chest tube|thoracostomy", case=False, regex=True), "patientunitstayid"])
    mv_ids = set(tr.loc[tr["treatmentstring"].astype(str).str.contains("mechanical ventilation", case=False, regex=True), "patientunitstayid"])
    try:
        rc = pd.read_csv(find_file(base, "respiratoryCare.csv"), usecols=["patientunitstayid", "ventstartoffset", "ventendoffset"])
        epi_ids = set(rc.loc[rc["ventstartoffset"].notna() | rc["ventendoffset"].notna(), "patientunitstayid"])
    except (FileNotFoundError, ValueError):
        epi_ids = set()
        notes.append("respiratoryCare.csv missing or without ventstart/ventend columns — ventilation episodes taken from treatment strings")
    epi_ids = epi_ids | mv_ids

    stays = pt[pt["stay_id"].isin(vent_ids)].copy()
    age = pd.to_numeric(stays["age"].astype(str).str.replace(">", "", regex=False).str.strip(), errors="coerce")
    stays["height_ok"] = stays["admissionheight"].between(100, 250)
    stays["weight_ok"] = stays["admissionweight"].between(20, 400)
    stays["sex_age_ok"] = stays["gender"].isin(["Male", "Female"]) & age.notna()
    stays["dead_hosp"] = (stays["hospitaldischargestatus"] == "Expired") | (stays["unitdischargestatus"] == "Expired")
    stays["dead_28"] = stays["dead_hosp"] & (stays["hospitaldischargeoffset"] <= 28 * 1440)
    stays["vent_episode"] = stays["stay_id"].isin(epi_ids)
    stays["chest_tube"] = stays["stay_id"].isin(ct_ids)
    stays["vasopress"] = stays["stay_id"].isin(vaso_ids)
    stays["nmb"] = stays["stay_id"].isin(nmb_ids)
    stays["mortality_ok"] = stays["hospitaldischargestatus"].notna()
    notes.append("eICU knows deaths only up to HOSPITAL DISCHARGE: 'dead_28' = in-hospital death within 28 days of unit admission "
                 "(the manuscript's 28-day mortality also counts deaths after discharge).")
    notes.append("eICU has no numeric ventilator-mode codes: the mode text comes from the 'Mode' flowsheet label and is classified by keywords — check the MODES table.")
    audit_out = {lab: (rmap(lab), n) for lab, n in audit.items()}
    return num, modes, stays, audit_out, notes, len(pt)


def load_amsterdam(base, chunksize, max_chunks):
    notes = []
    audit = Counter()
    nmap = label_mapper(AMS_NUMERIC_ITEMS)
    lmapper = label_mapper(AMS_LIST_ITEMS)

    print("  reading admissions.csv ...")
    adm = pd.read_csv(find_file(base, "admissions.csv"))
    adm = adm.rename(columns={"admissionid": "stay_id"})
    t0 = adm.set_index("stay_id")["admittedat"]          # milliseconds

    def minutes(df, col="measuredat"):
        return (df[col] - df["stay_id"].map(t0)) / 60000.0

    print("  reading numericitems.csv (≈1 billion rows on the full database — expect HOURS; use --quick for a smoke test) ...")
    parts = []
    for ch in read_chunks(find_file(base, "numericitems.csv"), ["admissionid", "item", "value", "measuredat"],
                          chunksize, max_chunks, "numericitems"):
        audit.update(ch["item"].value_counts().to_dict())
        ch["var"] = ch["item"].map(nmap)
        ch = ch[ch["var"].notna()].rename(columns={"admissionid": "stay_id"})
        if not len(ch):
            continue
        ch["t"] = minutes(ch)
        parts.append(ch[["stay_id", "t", "var", "value"]])
    num = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["stay_id", "t", "var", "value"])
    vent_ids = set(num.loc[num["var"].isin(["vt", "peep", "pplat", "ppeak"]), "stay_id"])

    print("  reading listitems.csv (ventilator mode) ...")
    mparts = []
    for ch in read_chunks(find_file(base, "listitems.csv"), ["admissionid", "item", "value", "measuredat"],
                          chunksize, max_chunks, "listitems"):
        ch["var"] = ch["item"].map(lmapper)
        ch = ch[(ch["var"] == "mode")].rename(columns={"admissionid": "stay_id", "value": "mode"})
        if not len(ch):
            continue
        ch["t"] = minutes(ch)
        mparts.append(ch[["stay_id", "t", "mode"]])
    modes = pd.concat(mparts, ignore_index=True) if mparts else pd.DataFrame(columns=["stay_id", "t", "mode"])

    print("  reading drugitems.csv and processitems.csv ...")
    dr = pd.read_csv(find_file(base, "drugitems.csv"), usecols=["admissionid", "item"])
    vaso_ids = set(dr.loc[dr["item"].astype(str).str.contains(AMS_VASOPRESSORS, case=False, regex=True), "admissionid"])
    nmb_ids = set(dr.loc[dr["item"].astype(str).str.contains(AMS_NMB, case=False, regex=True), "admissionid"])
    pr = pd.read_csv(find_file(base, "processitems.csv"), usecols=["admissionid", "item"])
    epi_ids = set(pr.loc[pr["item"].astype(str).str.contains(AMS_VENT_PROCESS, case=False, regex=True), "admissionid"])
    ct_ids = set(pr.loc[pr["item"].astype(str).str.contains(AMS_CHEST_TUBE, case=False, regex=True), "admissionid"])

    stays = adm[adm["stay_id"].isin(vent_ids)].copy()
    stays["height_ok"] = stays["heightgroup"].notna() if "heightgroup" in stays.columns else False
    stays["weight_ok"] = stays["weightgroup"].notna() if "weightgroup" in stays.columns else False
    stays["sex_age_ok"] = stays["gender"].notna() & stays["agegroup"].notna()
    dod = pd.to_numeric(stays["dateofdeath"], errors="coerce")
    stays["dead_hosp"] = dod.notna() & (dod <= pd.to_numeric(stays["dischargedat"], errors="coerce"))
    stays["dead_28"] = dod.notna() & ((dod - stays["admittedat"]) <= 28 * 86400000)
    stays["vent_episode"] = stays["stay_id"].isin(epi_ids)
    stays["chest_tube"] = stays["stay_id"].isin(ct_ids)
    stays["vasopress"] = stays["stay_id"].isin(vaso_ids)
    stays["nmb"] = stays["stay_id"].isin(nmb_ids)
    stays["mortality_ok"] = True
    notes.append("AmsterdamUMCdb gives height/weight/age as BANDS (e.g. height 170-179 cm): predicted body weight carries ≈ ±5 cm "
                 "of height uncertainty → VT/kg limits are approximate; flag this in any result.")
    notes.append("Date of death is recorded (including after discharge) → a true 28-day mortality IS computable.")
    audit_out = {lab: (nmap(lab), n) for lab, n in audit.items()}
    return num, modes, stays, audit_out, notes, len(adm)


# ---------------------------------------------------------------------------
# THE CHECK (shared) — mirrors check_coverage.py sections 3–7
# ---------------------------------------------------------------------------
def build_snapshots(num, modes):
    m = num[num["var"].isin(MECH)]
    piv = (m.pivot_table(index=["stay_id", "t"], columns="var", values="value", aggfunc="median")
             .reset_index().sort_values(["stay_id", "t"]))
    for c in MECH:
        if c not in piv.columns:
            piv[c] = np.nan
    piv["pplat_fresh"] = piv["pplat"].notna()
    for c in MECH:
        piv[c] = piv.groupby("stay_id")[c].ffill()
    piv["pplat_time"] = piv["t"].where(piv["pplat_fresh"])
    piv["pplat_time"] = piv.groupby("stay_id")["pplat_time"].ffill()
    prev = piv.groupby("stay_id")["peep"].shift()
    changed = piv["peep"].notna() & prev.notna() & (piv["peep"] != prev)
    piv["peep_since"] = piv["t"].where(changed)
    piv["peep_since"] = piv.groupby("stay_id")["peep_since"].ffill()
    if len(modes):
        md = (modes.dropna(subset=["mode"]).sort_values(["stay_id", "t"])
                   .drop_duplicates(["stay_id", "t"], keep="last"))
        piv = pd.merge_asof(piv.sort_values("t"), md.sort_values("t"), on="t", by="stay_id", direction="backward")
    else:
        piv["mode"] = np.nan
    piv = piv.sort_values(["stay_id", "t"]).reset_index(drop=True)
    piv["controlled"] = piv["mode"].map(lambda s: is_controlled(s) if isinstance(s, str) else False)
    return piv


def peep_change_events(d, look_ahead_min=240):
    rows = []
    for sid, g in d.groupby("stay_id"):
        g = g.sort_values("t").reset_index(drop=True)
        t, peep = g["t"].to_numpy(), g["peep"].to_numpy()
        fresh, ctrl = g["pplat_fresh"].to_numpy(), g["controlled"].to_numpy()
        pplat_time, peep_since = g["pplat_time"].to_numpy(), g["peep_since"].to_numpy()
        for i in range(1, len(g)):
            if abs(peep[i] - peep[i - 1]) < 1:
                continue
            before_valid = bool(np.isnan(peep_since[i - 1]) or pplat_time[i - 1] >= peep_since[i - 1])
            after_4h, j = False, i
            while j < len(g) and peep[j] == peep[i] and t[j] <= t[i] + look_ahead_min:
                if fresh[j]:
                    after_4h = True
                    break
                j += 1
            rows.append((sid, t[i - 1], t[i], peep[i] - peep[i - 1], before_valid, bool(fresh[i]), after_4h,
                         bool(ctrl[i - 1] and ctrl[i])))
    return pd.DataFrame(rows, columns=["stay_id", "t_before", "t_after", "dpeep", "before_valid", "after_fresh",
                                       "after_fresh_4h", "controlled_both"])


def has_reading_within(events, sig, window_min):
    sig = sig.sort_values(["stay_id", "t"])
    times = {sid: g["t"].to_numpy() for sid, g in sig.groupby("stay_id")}
    b = np.zeros(len(events), dtype=bool)
    a = np.zeros(len(events), dtype=bool)
    for i, (sid, tb, ta) in enumerate(zip(events["stay_id"], events["t_before"], events["t_after"])):
        ts = times.get(sid)
        if ts is None:
            continue
        b[i] = np.searchsorted(ts, tb, side="right") > np.searchsorted(ts, tb - window_min)
        a[i] = np.searchsorted(ts, ta + window_min, side="right") > np.searchsorted(ts, ta)
    return b, a


def run_check(dataset, num, modes, stays, audit, notes, n_total, csv_path, quick):
    vent_ids = set(stays["stay_id"])
    n_vent = len(vent_ids)
    num = num[num["stay_id"].isin(vent_ids)]
    pct = lambda mask: f"{int(mask.sum())} ({100.0 * mask.mean():.0f}%)" if len(mask) else "0"

    print("\n" + "=" * 78)
    print(f"COHORT — {dataset}" + ("   [--quick: partial read, counts are NOT real coverage]" if quick else ""))
    print(f"  ICU stays / admissions in folder ..... {n_total}")
    print(f"  ventilated stays (any vent reading) .. {n_vent}   <- denominator for '% vent stays'")
    print(f"  stays with a ventilation episode record: {int(stays['vent_episode'].sum())}")

    # ---- per-variable coverage -------------------------------------------------------
    rows = []
    per_var = num.groupby("var")
    for key, name, group, tier, feeds in VARIABLES:
        if key in ("height", "sex_age", "weight", "vent_proc", "mortality", "vasopress", "nmb", "chest_tube"):
            col = {"height": "height_ok", "sex_age": "sex_age_ok", "weight": "weight_ok", "vent_proc": "vent_episode",
                   "mortality": "mortality_ok", "vasopress": "vasopress", "nmb": "nmb", "chest_tube": "chest_tube"}[key]
            n = int(stays[col].sum())
            rows.append({"group": group, "variable": name, "tier": tier, "rows": n, "stays": n,
                         "pct_vent_stays": round(100.0 * n / max(n_vent, 1), 1), "median_per_stay": 1.0, "feeds": feeds})
            continue
        if key == "mode":
            sub = modes[modes["stay_id"].isin(vent_ids)]
        elif key in per_var.groups:
            sub = per_var.get_group(key)
        else:
            sub = num.iloc[0:0]
        st = sub["stay_id"].nunique()
        per = sub.groupby("stay_id").size()
        rows.append({"group": group, "variable": name, "tier": tier, "rows": int(len(sub)), "stays": int(st),
                     "pct_vent_stays": round(100.0 * st / max(n_vent, 1), 1),
                     "median_per_stay": float(per.median()) if st else 0.0, "feeds": feeds})
    table = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    print("\n" + "=" * 78)
    print("PER-VARIABLE COVERAGE  (stays = ventilated stays with >=1 reading)")
    print(table[["group", "variable", "tier", "rows", "stays", "pct_vent_stays", "median_per_stay"]].to_string(index=False))
    print(f"  outcome detail: in-hospital deaths {int(stays['dead_hosp'].sum())} ({100.0 * stays['dead_hosp'].mean():.1f}%); "
          f"28-day deaths {int(stays['dead_28'].sum())} ({100.0 * stays['dead_28'].mean():.1f}%)")
    if csv_path:
        table.to_csv(csv_path, index=False)
        print(f"  (saved aggregate table to {csv_path})")

    # ---- feasibility of the PEEP math -------------------------------------------------
    piv = build_snapshots(num, modes[modes["stay_id"].isin(vent_ids)])
    d = physiologic_filter(piv)
    ev = peep_change_events(d)
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
        print(f"     ...'after' plateau charted within 4h at the NEW PEEP .... {pct(ev['after_fresh_4h'])}")
        print(f"     ...USABLE pairs (before valid AND fresh after <=4h) ...... {pct(usable)}")
        print(f"     ...usable AND controlled mode on both sides ............. {pct(usable & ev['controlled_both'])}")
        for label, keys, w in [("arterial blood gas", ["paco2", "pao2", "ph"], 120), ("SpO2", ["spo2"], 60),
                               ("FiO2", ["fio2"], 240), ("mean BP (any)", ["map", "map_nibp"], 60)]:
            sig = num[num["var"].isin(keys)]
            b, a = has_reading_within(ev, sig, w)
            print(f"  ...events with {label:<22} within +/-{w // 60}h before AND after: {pct(b & a)}")
    levels = d.groupby("stay_id")["peep"].nunique()
    levels_fresh = d[d["pplat_fresh"]].groupby("stay_id")["peep"].nunique()
    print(f"  stays with >=2 distinct PEEP levels ........................ {int((levels >= 2).sum())}   (fresh-plateau only: {int((levels_fresh >= 2).sum())})")
    print(f"  stays with transpulmonary / esophageal pressure ............ {num.loc[num['var'] == 'transpulm', 'stay_id'].nunique()}")
    print(f"  stays with CVP ............................................. {num.loc[num['var'] == 'cvp', 'stay_id'].nunique()}")

    # ---- ventilator modes ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print("VENTILATOR MODES (rows of mode text; '*' = classified as CONTROLLED by keyword — check this!)")
    vc = modes[modes["stay_id"].isin(vent_ids)]["mode"].value_counts()
    ctrl = 0
    for mode, n in vc.head(40).items():
        flag = "*" if is_controlled(mode) else " "
        ctrl += n if flag == "*" else 0
        print(f"  {flag} {str(mode)[:40]:<40} {n}")
    if len(vc):
        print(f"  controlled share of mode rows: {100.0 * ctrl / vc.sum():.0f}%   (distinct mode strings: {len(vc)})")
    else:
        print("  no mode text found — the translation table missed the mode label (see LABEL AUDIT)")

    # ---- label audit ---------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("LABEL AUDIT — how each dataset label was translated (metadata only, safe to paste)")
    matched = sorted(((k, lab, n) for lab, (k, n) in audit.items() if k), key=lambda x: (x[0], -x[2]))
    print("  matched labels (variable <- label, rows):")
    for k, lab, n in matched[:120]:
        print(f"    {k:<11} <- {str(lab)[:45]:<45} {n}")
    unmatched = sorted(((n, lab) for lab, (k, n) in audit.items() if not k), reverse=True)
    print("  most frequent UNMATCHED labels (tell Claude if any of these is a ventilator / gas / pressure reading):")
    for n, lab in unmatched[:40]:
        print(f"    {str(lab)[:60]:<60} {n}")

    # ---- verdict --------------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("VERDICT — REQUIRED variables below 90% of ventilated stays")
    weak = table[table["tier"].str.startswith("REQUIRED") & ~table["tier"].str.endswith("*") & (table["pct_vent_stays"] < 90)]
    if len(weak):
        for _, r in weak.iterrows():
            print(f"  ! {r['variable']:<50} {r['pct_vent_stays']}%")
    else:
        print("  none — every REQUIRED variable is present in >=90% of ventilated stays")
    for n in notes:
        print(f"  note: {n}")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(description="Coverage check of the PEEP-math required variables on eICU or AmsterdamUMCdb.")
    ap.add_argument("--dataset", required=True, choices=["eicu", "amsterdam"])
    ap.add_argument("--path", required=True, help="folder holding the dataset's CSV files (.csv or .csv.gz)")
    ap.add_argument("--csv", default=None, help="optional: also save the aggregate coverage table to this CSV")
    ap.add_argument("--quick", action="store_true", help="read only the first slices of the big tables (smoke test)")
    ap.add_argument("--chunksize", type=int, default=2_000_000)
    args = ap.parse_args()
    max_chunks = 3 if args.quick else 0
    print("=" * 78)
    print(f"check_coverage_other — {args.dataset} — {args.path}")
    if args.dataset == "eicu":
        num, modes, stays, audit, notes, n_total = load_eicu(args.path, args.chunksize, max_chunks)
    else:
        num, modes, stays, audit, notes, n_total = load_amsterdam(args.path, args.chunksize, max_chunks)
    run_check(args.dataset, num, modes, stays, audit, notes, n_total, args.csv, args.quick)


if __name__ == "__main__":
    main()
