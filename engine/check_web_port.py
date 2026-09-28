"""
check_web_port.py — does the web app give the SAME numbers as the Python engine?

Plain-language: app/ventoptimizer.html carries a JavaScript copy of the engine. Copies drift.
This script pulls the logic block out of the HTML, runs it in Node on a few made-up cases,
runs the Python engine on the same cases, and compares every number. If anything differs,
it says exactly which field, so the web app can never quietly disagree with the engine.

Usage:  python engine/check_web_port.py        (needs Node.js installed; prints PASS / FAIL)
The cases are invented (no patient data).
"""

import json
import os
import re
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from physiology import PatientCase, Baseline
from optimizer import optimize

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "..", "app", "ventoptimizer.html")
TOL = 1e-6

# Made-up test cases (no patient data). Each = (patient, baseline, mode).
CASES = [
    ({"pbw": 70, "base_paco2": 70, "hco3": 24, "permissive": True},
     {"vt": 430, "rr": 20, "peep": 5, "pplat": 25, "ppeak": 30, "fio2": 0.6, "spo2": 93, "rr_spont": 0, "map_mmHg": 75}, "VC"),
    ({"pbw": 70, "base_paco2": 45, "hco3": 24, "permissive": False},
     {"vt": 420, "rr": 18, "peep": 8, "pplat": 20, "ppeak": 26, "fio2": 0.5, "spo2": 94, "rr_spont": 0, "map_mmHg": 78}, "VC"),
    ({"pbw": 60, "base_paco2": 50, "hco3": 22, "permissive": True, "measured_vd_vt": 0.55},
     {"vt": 380, "rr": 22, "peep": 10, "pplat": 24, "ppeak": 31, "fio2": 40, "spo2": 97, "rr_spont": 0, "map_mmHg": 62,
      "vasopressor_running": True, "chest_tube": True}, "PC"),
    ({"pbw": 80, "base_paco2": 40, "hco3": 26, "permissive": False},
     {"vt": 500, "rr": 16, "peep": 6, "pplat": 18, "ppeak": 24, "fio2": 0.3, "spo2": 96, "rr_spont": 4, "map_mmHg": 80, "icp": 18}, "VC"),
]


def run_js(cases):
    """Extract the engine script from the HTML and run it in Node on the cases."""
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r'<script id="vo-engine">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("could not find the vo-engine script block in the HTML")
    harness = m.group(1) + """
const cases = JSON.parse(process.argv[2]);
const out = cases.map(([pt, base, mode]) => VO.optimize(pt, base, mode));
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        path = f.name
    try:
        res = subprocess.run(["node", path, json.dumps(cases)], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(path)
    if res.returncode != 0:
        raise SystemExit("node failed:\n" + res.stderr)
    return json.loads(res.stdout)


def run_py(cases):
    out = []
    for pt, base, mode in cases:
        r = optimize(PatientCase(**pt), Baseline(**base), mode)
        c = r.peep_ceiling
        out.append({
            "setting": r.setting,
            "prediction": None if r.prediction is None else {k: getattr(r.prediction, k) for k in
                          ["mp", "mp_dyn", "mp_tidal", "pplat", "driving_p", "ppeak", "vt", "ph", "paco2", "tau", "te", "compliance"]},
            "baseline_power": r.baseline_power,
            "ceiling": {"peep_now": c.peep_now, "compliance_now": c.compliance_now, "peep_max_safe": c.peep_max_safe,
                        "binding_constraint": c.binding_constraint, "projected_pplat_at_max": c.projected_pplat_at_max,
                        "projected_dp_at_max": c.projected_dp_at_max, "envelope_low": c.envelope_low, "envelope_high": c.envelope_high,
                        "oxygenation": c.oxygenation, "vetoes": c.vetoes, "cautions": c.cautions, "notes": c.notes},
        })
    return out


def same(a, b):
    # JSON has no NaN: a Python NaN arrives from Node as null. Treat NaN and None as the same "no value".
    a_missing = a is None or (isinstance(a, float) and a != a)
    b_missing = b is None or (isinstance(b, float) and b != b)
    if a_missing or b_missing:
        return a_missing and b_missing
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(a)))
    return a == b


def compare(py, js):
    problems = []
    for i, (p, j) in enumerate(zip(py, js)):
        # setting + prediction numbers
        for key in ["setting", "baseline_power", "prediction"]:
            pv, jv = p[key], j[key]
            if pv is None or jv is None:
                if pv is not jv:
                    problems.append(f"case {i}: {key} present in one engine only")
                continue
            for k in pv:
                if k == "mode":
                    continue
                if not same(pv[k], jv.get(k)):
                    problems.append(f"case {i}: {key}.{k}: python {pv[k]} vs web {jv.get(k)}")
        # the ceiling, including every reason string
        for k, pv in p["ceiling"].items():
            jv = j["ceiling"].get(k)
            if isinstance(pv, list):
                if [str(x) for x in pv] != [str(x) for x in jv]:
                    problems.append(f"case {i}: ceiling.{k}: python {pv} vs web {jv}")
            elif isinstance(pv, str):
                if pv.replace(".0 ", " ") != str(jv).replace(".0 ", " ") and pv != jv:
                    problems.append(f"case {i}: ceiling.{k}: python '{pv}' vs web '{jv}'")
            elif not same(pv, jv):
                problems.append(f"case {i}: ceiling.{k}: python {pv} vs web {jv}")
    return problems


def main():
    cases = CASES
    py = run_py(cases)
    js = run_js(cases)
    problems = compare(py, js)
    print(f"Web-port check: {len(cases)} cases, {len(problems)} differences")
    for p in problems:
        print("  DIFF:", p)
    print("RESULT:", "PASS — the web app mirrors the engine" if not problems else "FAIL — fix the web app before any demo")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
