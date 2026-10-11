# State mechanism comparison: FEM SENS vs PIDL hard recovery

Created: 2026-07-01

## Purpose

This package follows the Chapter 4 style of result comparison: state-resolved
field evidence first, then scalar reductions. The primary comparison is between
the FEM SENS recovery/pidlstop case and the PIDL hard-d1 U=0 recovery run.

## State mapping

- FEM source: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4`
- FEM state0 companion: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4__state0_recovery_from_driver_folder`
- PIDL source: `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/hard_d1_u0_recovery_5step_0630_formal/raw/run/element_diagnostics_probe_driver`
- PIDL step 0 is the zero-load hard-alpha recovery state.
- After that: `cN_peak = 1 + 5*(N-1) + 3`; `cN_unloaded = 1 + 5*(N-1) + 4`.
- FEM SENS uses 8 substeps per cycle. The exported `psi_fields/cycle_*.mat`
  files are cycle-level field summaries; the VTK files use suffix `_008`.

## Tables

- `tables/state_mapping_manifest.csv`: label-to-cycle/step mapping.
- `tables/state_metric_summary.csv`: state0, c1, c20, c40, c60, c69 and c89 metrics.
- `tables/tail_dense_state_summary.csv`: FEM c80/c82/c84/c86/c87/c88/c89 and PIDL steps 444-447.

## Figures

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/damage_fatigue_state_montage.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/damage_fatigue_state_montage.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/history_driver_state_montage.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/history_driver_state_montage.pdf`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/state_metric_trajectories.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/figures/state_metric_trajectories.pdf`

## Reading notes

- `damage_fatigue_state_montage` compares FEM damage `d` with PIDL `alpha`, and
  FEM fatigue degradation `f(alpha_bar)` with PIDL `f_fatigue`.
- `history_driver_state_montage` compares FEM fatigue history `alpha_bar` with
  PIDL `hist_fat`, and FEM exported `psi_elem` with PIDL `psi_active`.
- Damage and fatigue field colour scales are fixed to `[0,1]`; values outside
  the interval are visually saturated. This keeps FEM/PIDL panels comparable.
- Driver panels use a shared log colour scale; this makes the late-stage
  under-coupling visible without making the PIDL active-driver panels blank.

## Main interpretation

The initial hard-recovery damage energy is aligned: FEM SENS state0 `Ed` is
about `0.0050587345`, while PIDL step0 `sum(E_d_elem)` is about `0.00505321`.
The event scale also aligns: FEM reaches cycle 89 and PIDL first hits at
`c89_peak/step444`.

The field-level comparison should therefore be read as a mechanism check, not
as a simple life match. The important question is whether damage, fatigue
history, degradation and active driver occupy the same process zone from state0
through the dense tail states.
