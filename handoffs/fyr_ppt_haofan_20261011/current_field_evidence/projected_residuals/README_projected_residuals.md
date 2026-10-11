# FEM-grid projected residual panels

Created: 2026-07-01

## Figure purpose

Claim: the hard-recovery PIDL run is close to the FEM SENS recovery case in
event scale, but the field mechanism still differs. These panels compare fields
on one FEM cell grid instead of using separate FEM/PIDL centroid scatter plots.

## Data sources

- FEM reference: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4`
- FEM state0 companion: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4__state0_recovery_from_driver_folder`
- PIDL diagnostics: `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/hard_d1_u0_recovery_5step_0630_formal/raw/run/element_diagnostics_probe_driver`
- PIDL triangle mesh: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile/meshed_geom_fem_soft_hist0.msh`

## Projection method

PIDL element values are projected to the FEM quadrilateral grid using true
polygon-overlap area averaging between the PIDL triangular mesh and FEM quad
cells. The PIDL mesh is verified against the run diagnostic centroid/area export
before projection.

Projection coverage:

- FEM cells: `86408`
- projected FEM cells: `86408`
- overlap pairs: `453236`
- overlap area ratio median: `1.000000`
- overlap area ratio 1st/99th percentiles: `1.000000` / `1.000000`


## Outputs

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_damage_selected_states.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_damage_selected_states.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_history_selected_states.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_history_selected_states.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_fatigue_selected_states.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_fatigue_selected_states.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_driver_selected_states.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/projected_residual_driver_selected_states.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/tail_dense_projected_fields_vs_fem_c89.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/tail_dense_projected_fields_vs_fem_c89.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/tail_dense_projected_residuals_vs_fem_c89.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/figures/tail_dense_projected_residuals_vs_fem_c89.pdf`

## Tables

- `tables/projection_quality.csv`: projection coverage and overlap-quality checks.
- `tables/projected_residual_summary.csv`: FEM, projected-PIDL and residual scalar reductions.
- `tables/tail_dense_projected_residual_summary.csv`: tail-window residual reductions.

## Caption note

Use the phrase "FEM-grid projection by polygon-overlap area averaging" in captions. The PIDL mesh source and centroid/area verification are recorded in `tables/projection_quality.csv`.
