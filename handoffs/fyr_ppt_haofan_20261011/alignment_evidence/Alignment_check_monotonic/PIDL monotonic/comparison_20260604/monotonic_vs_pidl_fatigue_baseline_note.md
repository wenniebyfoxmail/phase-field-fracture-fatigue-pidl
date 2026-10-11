# Monotonic PIDL Cases vs PIDL Fatigue Baseline

Compared on 2026-06-04.

## Sources

- Monotonic cases: `/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check/PIDL monotonic/cases`
- PIDL cyclic fatigue baseline state timing fields: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/pidl_femmesh_state_timing_fields_j0_j1.npz`
- Field summary CSV: `/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check/PIDL monotonic/comparison_20260604/monotonic_cases_vs_pidl_fatigue_baseline_field_summary.csv`
- Energy summary CSV: `/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check/PIDL monotonic/comparison_20260604/monotonic_cases_energy_summary.csv`
- Pairwise alpha differences CSV: `/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check/PIDL monotonic/comparison_20260604/monotonic_pairwise_alpha_differences.csv`

## Main Findings

1. The four monotonic cases are a 2x2 matrix: standard coarse-to-fine pretrain vs all-fine pretrain, crossed with fatigue off/on.
2. In both pretrain settings, monotonic fatigue-on and fatigue-off alpha snapshots are exactly identical over the common saved steps. This is expected: `loading_type='monotonic'` returns unchanged fatigue history, so `alpha_bar=0` and `f=1`.
3. The all-fine and standard-pretrain cases are close at early steps but diverge locally around the instability/load-jump region near step 11. Worst pointwise alpha difference is about 0.989 at step 11, but mean absolute difference is only about 0.012, so it is a localized path difference.
4. Compared with cyclic fatigue baseline, monotonic cases do not reproduce fatigue variables: cyclic baseline j0 has `alpha_bar_max=0.435` and j1 has `alpha_bar_max=0.857`, while monotonic fatigue-on stores `alpha_bar_vs_cycle = [0, 0, 1]` for all saved rows.
5. At U=0.12 monotonic step 7, alpha is hotter than cyclic baseline j0 in the upper tail: monotonic `p99(alpha)≈0.993`, cyclic baseline j0 `p99(alpha)≈0.933`. This is a loading-path effect and should not be read as fatigue accumulation.

## Interpretation

These monotonic cases are useful for checking monotonic phase-field/pretraining behaviour. They are not a PIDL fatigue-baseline replacement because their fatigue history is intentionally disabled by monotonic loading semantics.
