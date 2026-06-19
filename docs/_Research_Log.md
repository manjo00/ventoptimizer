# Research Log — the lab notebook

Append-only, detailed record of every experiment and decision, so the model's
development is reproducible and the eventual write-up is ready. **Aggregate results
only — NEVER patient data** (see CLAUDE.md governance). Newest at the bottom.

### Entry template
```
## YYYY-MM-DD — <title>
**Question:** what are we testing?
**Method:** what we did (files, dataset, sample size — aggregate only).
**Result:** the aggregate numbers Ahmed pasted back.
**Decision:** what we concluded / changed next.
**Commit:** <hash or "Phase X — task">
```

---

## 2026-06-20 — Track A: literature pass on the model's assumptions
**Question:** Which of the model's clinical numbers are real/cited, and which are guesses that could make it inaccurate?
**Method:** Reviewed each formula in `_Clinical_Logic.md` against the literature (targeted web searches + the manuscript). Resolved every `[ASSUMPTION]`/`[TO-RESEARCH]` tag in `_Evidence_Base.md`.
**Result (findings):**
- ✅ **Mechanical Power equation** — cited & validated (Gattinoni 2016; Chiumello 2020).
- ✅ **Safety limits** (Pplat ≤ 30, VT 4–8 mL/kg) — ARDSNet (Brower 2000).
- ✅ **Recruitment threshold R/I > 0.5** — now cited (Chen 2020). ⚠️ but the `×0.1` PEEP→compliance multiplier is **invented** (no source) → replace in Track C.
- ⚠️ **Linear compliance = confirmed the model's biggest weakness.** The ARDS P–V curve is nonlinear (lower + upper inflection points; Hickling 1998). One fixed compliance can mis-predict plateau pressure. → **top Track-C fix** (per-patient P–V curve).
- ⚠️ **Dead space 2.2 mL/kg = weakly validated.** Origin Radford 1955, but measured dead space barely correlates with body weight (r² ≈ 0.0002; Respir Care 2021). → Track-C candidate (improve or measure).
- ✅ **pH floors 7.30 / 7.20** — pragmatic ARDSNet-aligned conventions; ~7.20 widely accepted (if arbitrary).
- ✅ **3τ ≈ 95% emptying** — standard math (1 − e⁻³ = 0.95).
**Decision:** Two priorities for Track C once we have data — (1) replace linear compliance with each patient's own P–V curve; (2) improve/measure dead space. Keep MP as the objective; evaluate driving pressure (Amato 2015) as a co-limit *with data*. Every formula now traces to a citation in `_Evidence_Base.md`.
**Commit:** Phase 1 — Track A literature pass
