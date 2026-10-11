# FEM Monotonic Alignment Package

Source handoff:

`/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_pidl_aligned_monotonic_four_cases_20260603`

This folder organizes the four monotonic FEM cases prepared for PIDL alignment.
The package keeps the original case folders intact and separates summary
documents, MATLAB scripts, and case outputs.

## Layout

- `docs/`  
  Original handoff README and `monotonic_four_case_summary.csv`.
- `scripts/`  
  MATLAB input/main scripts used to generate the handoff cases.
- `cases/`  
  Four case folders with VTK fields, load-displacement output, convergence
  logs, checkpoints, crack data, and first-cycle psi fields.
- `manifest/`  
  Reserved for future generated file manifests or audit notes.

## Case Summary

| Case | Loading | Steps | Peak/displacement note | Key scalar note |
|---|---:|---:|---|---|
| `umax012_fatigue_on` | Umax 0.12, fatigue on | 8 | peak at U=0.12 | Kt 8.873, f_mean 0.999915 |
| `umax012_fatigue_off` | Umax 0.12, fatigue off | 8 | peak at U=0.12 | Kt 8.816, f_mean 1 |
| `umax020_fatigue_off` | Umax 0.20, fatigue off | 24 | peak force at U=0.165, drop at U=0.17 | Kt 1228.39 |
| `umax020_fatigue_on` | Umax 0.20, fatigue on | 24 | peak force at U=0.16, drop at U=0.165 | Kt 1162.37 |

## Notes

- The Umax 0.12 cases use the older 8-step linear monotonic loading.
- The Umax 0.20 cases use the Manav/Mac explicit monotonic sequence:
  `0.025, 0.050, 0.075, 0.100, 0.105, ..., 0.200`.
- For detailed scalar values, use `docs/monotonic_four_case_summary.csv`.
- For field inspection, use each case's `fields_*.vtk`, `peak_load_c1.vtk`,
  and `psi_fields/cycle_0001.mat`.
