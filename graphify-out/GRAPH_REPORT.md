# Graph Report - ventoptimizer  (2026-10-30)

## Corpus Check
- 8 files · ~20,261 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 169 nodes · 394 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9cbf2ea6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- state_predictor.py
- validate_mimic.py
- pandas
- safe_peep.py
- check_coverage.py
- optimizer.py
- check_web_port.py
- predict
- physiology.py
- optimize
- estimate_vco2_ml_min

## God Nodes (most connected - your core abstractions)
1. `main()` - 15 edges
2. `optimize()` - 14 edges
3. `predict()` - 13 edges
4. `main()` - 13 edges
5. `highest_safe_peep()` - 12 edges
6. `read_filtered()` - 11 edges
7. `load_snapshots()` - 11 edges
8. `usable_peep_pairs()` - 11 edges
9. `main()` - 10 edges
10. `q1_state_model()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `OptimizerResult` --uses--> `SafePeepResult`  [INFERRED]
  engine/optimizer.py → engine/safe_peep.py
- `ceiling_for()` --uses--> `Baseline`  [INFERRED]
  engine/optimizer.py → engine/physiology.py
- `_peep_guidance()` --uses--> `SafePeepResult`  [INFERRED]
  engine/optimizer.py → engine/safe_peep.py
- `main()` --calls--> `read_filtered()`  [EXTRACTED]
  engine/check_coverage.py → engine/validate_mimic.py
- `OptimizerResult` --uses--> `Prediction`  [INFERRED]
  engine/optimizer.py → engine/physiology.py

## Import Cycles
- None detected.

## Communities (11 total, 1 thin omitted)

### Community 0 - "state_predictor.py"
Cohesion: 0.13
Nodes (17): attach_state(), choose_lambda(), fit_beta(), grouped_folds(), main(), noise_floor(), q1_state_model(), q3_test_step() (+9 more)

### Community 1 - "validate_mimic.py"
Cohesion: 0.12
Nodes (11): exp1_compliance_stability(), exp1b_compliance_stability_fresh(), exp2_plateau_prediction(), exp2b_fresh_plateau_prediction(), exp3_peep_aware_compliance(), exp4_co2_prediction(), exp5_mp_reduction_available(), load_demographics() (+3 more)

### Community 2 - "pandas"
Cohesion: 0.15
Nodes (10): exp6a_noise_floor(), exp6b_consistency(), exp6c_prediction(), fit_beta(), frac_desc(), main(), own_curve_slope(), fresh_plateaus() (+2 more)

### Community 3 - "safe_peep.py"
Cohesion: 0.19
Nodes (11): ceiling_for(), explain(), fio2_fraction(), highest_safe_peep(), main(), mechanical_ceiling(), projected_compliance(), SafePeepResult (+3 more)

### Community 4 - "check_coverage.py"
Cohesion: 0.18
Nodes (7): build_snapshots(), has_reading_within(), main(), peep_change_events(), per_stay_stats(), times_by_stay(), physiologic_filter()

### Community 5 - "optimizer.py"
Cohesion: 0.18
Nodes (5): _baseline_violations(), _explain(), Limits, OptimizerResult, Prediction

### Community 6 - "check_web_port.py"
Cohesion: 0.27
Nodes (4): compare(), main(), run_js(), same()

### Community 7 - "predict"
Cohesion: 0.20
Nodes (5): _peep_guidance(), compliance_change_range(), compliance_response(), Mechanics, predict()

### Community 8 - "physiology.py"
Cohesion: 0.27
Nodes (4): mechanical_power(), mp_dynamic(), mp_gattinoni(), mp_tidal()

### Community 9 - "optimize"
Cohesion: 0.43
Nodes (6): run_py(), optimize(), Baseline, baseline_mechanics(), dead_space_ml(), PatientCase

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `read_filtered()` connect `validate_mimic.py` to `state_predictor.py`, `pandas`, `safe_peep.py`, `check_coverage.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `optimize()` (e.g. with `Baseline` and `PatientCase`) actually correct?**
  _`optimize()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `state_predictor.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Why does `usable_peep_pairs()` connect `pandas` to `state_predictor.py`, `validate_mimic.py`, `safe_peep.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Should `validate_mimic.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12318840579710146 - nodes in this community are weakly interconnected._
- **Why does `fresh_plateaus()` connect `pandas` to `state_predictor.py`, `validate_mimic.py`, `safe_peep.py`, `check_coverage.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Should `pandas` be split into smaller, more focused modules?**
  _Cohesion score 0.1471861471861472 - nodes in this community are weakly interconnected._