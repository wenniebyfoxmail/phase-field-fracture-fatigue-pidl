# Canonical outputs

Use this file to avoid choosing between repeated same-named CSVs and figures.

## FEM loading-step comparison

Primary figure:

- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_protocol_metrics_20260608.png`
- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_protocol_metrics_20260608.pdf`

Most aligned FEM control against standard:

- `FEM cyclic 012/figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.png`
- `FEM cyclic 012/figures/protocol_comparison/fem_nstep10_vs_standard_protocol_metrics_20260608.pdf`

Void-notch diagnostic mirror:

- `FEM cyclic 012/cases/void_notch_reverseBC_nstep8/setting.md`
- `FEM cyclic 012/cases/void_notch_reverseBC_nstep8/raw_data/README_reverseBC_u12_cyclewise_mechanism.md`
- `FEM cyclic 012/cases/void_notch_reverseBC_nstep8/raw_data/reverseBC_u12_cyclewise_mechanism_metrics.csv`
- `FEM cyclic 012/cases/void_notch_reverseBC_nstep8/raw_data/reverseBC_u12_cyclewise_element_fields_c1_c74.mat`

Use this only as a notch-convention diagnostic. It is the closest available
void/slit-notch FEM reference, but it is not the current strict standard because
the mesh/notch convention and loading cadence differ from the soft-hist0
retained-material reference.

Supporting tables:

- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_protocol_metrics_long_20260608.csv`
- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_event_ratios_20260608.csv`
- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_c69_ratios_20260608.csv`
- `FEM cyclic 012/figures/protocol_comparison/fem_loading_step_phase_front_metrics_20260608.csv`

Interpretation note:

- `FEM cyclic 012/comparison_figure_note_20260608.md`

## PIDL loading-step and FEM/PIDL comparison

Primary FEM/PIDL comparison figure:

- `PIDL cyclic 012/figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.png`
- `PIDL cyclic 012/figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.pdf`

Most aligned PIDL-vs-standard-FEM figure set:

- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_standard_fem_metrics_20260608.png`
- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_standard_fem_metrics_20260608.pdf`
- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.png`
- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.pdf`

Supporting tables:

- `PIDL cyclic 012/figures/protocol_comparison/standard_fem_vs_pidl_energy_metrics_20260608.csv`
- `PIDL cyclic 012/figures/protocol_comparison/standard_fem_phase_front_metrics_20260608.csv`
- `PIDL cyclic 012/figures/protocol_comparison/pidl_one_peak_phase_front_metrics_20260608.csv`
- `PIDL cyclic 012/figures/protocol_comparison/pidl_femlike_substep_phase_front_metrics_20260608.csv`
- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_selection_summary_20260608.csv`

Interpretation notes:

- `PIDL cyclic 012/comparison_figure_note_20260608.md`
- `PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem/most_aligned_pidl_standard_fem_note_20260608.md`
- `PIDL cyclic 012/cases/setting_comparison_20260608.md`

Deep-dive comparison package:

- `comparisons/most_comparable_fem_pidl_deep_dive_20260608/README_deep_dive_20260608.md`
- `comparisons/most_comparable_fem_pidl_deep_dive_20260608/figures/`
- `comparisons/most_comparable_fem_pidl_deep_dive_20260608/tables/`

Latest aligned state-field comparison package:

- `comparisons/latest_align_state_field_comparison_20260608/README_latest_align_state_field_comparison_20260608.md`
- `comparisons/latest_align_state_field_comparison_20260608/figures/`
- `comparisons/latest_align_state_field_comparison_20260608/tables/`
- `comparisons/latest_align_state_field_comparison_20260608/scripts/compare_latest_align_fields.py`

## Phase-field figures

FEM:

- `FEM cyclic 012/figures/key_phase_field/fem_phase_field_initial_and_fracture_final_20260607.png`
- `FEM cyclic 012/figures/key_phase_field/fem_phase_field_state_timing_initial_c1_substeps_20260607.png`

## FEM State-Field Exports

Latest aligned field package for mapped-state PIDL comparison:

- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/README_latest_align_soft_hist0_state_fields.md`
- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/latest_align_soft_hist0_state_index.csv`
- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/latest_align_soft_hist0_state_fields.mat`
- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/mesh_geometry.mat`

Use this package for state0, c1 substeps, and peak/unloaded states at c2, c3,
c20, c40, c60, and c69. It separates raw stress from degraded/effective stress
and includes element and Gauss-point strain/stress/psi/damage/history fields.

PIDL:

- `PIDL cyclic 012/figures/key_phase_field/pidl_one_peak_phase_field_initial_post_fracture_20260607.png`
- `PIDL cyclic 012/figures/key_phase_field/pidl_substep_controls_phase_field_initial_final_20260607.png`

## De-duplication note

The repeated files named `aligned_fem_pidl_energy_tiers.csv`,
`energy_over_cycle_fem_pidl_substep_comparison_20260607.*`, and
`soft_hist0_alignment_audit_*` appear in both root and case-local folders.
Use the canonical files listed above for writing. Treat case-local copies as
provenance snapshots unless a case-specific note says otherwise.
