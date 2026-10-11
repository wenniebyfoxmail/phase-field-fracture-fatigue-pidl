# FEM Soft-Hist0 Monotonic 24-Step Handoff

This folder stores the latest FEM retained-material monotonic handoff received from Windows-FEM on 2026-06-07.

## Raw Data

- Raw handoff: `raw_handoff/_pidl_handoff_soft_hist0_monotonic_24vtk_20260607/`
- `fatigue_off/`: 24 VTK files, `fields_000001_001.vtk` through `fields_000001_024.vtk`
- `fatigue_on/`: 24 VTK files, `fields_000001_001.vtk` through `fields_000001_024.vtk`
- Each case includes its `load_displ_*.out` table for mapping VTK step index to displacement and force.

The old shared-code cache path now points here by symlink:
`upload code/fem_result/onedrive_packages/_pidl_handoff_soft_hist0_monotonic_24vtk_20260607`.

## FEM Setting

- Geometry/mesh setting: retained material with soft diffuse precrack / hist0 initialization.
- Not the older void/slit-notch control: no void slit and no duplicated crack-face nodes.
- Boundary condition: reverseBC.
- Constraints: `fix_X` on top and bottom, `fix_Y` on bottom, `disp_Y` on top.
- Model: `AT1 + AMOR + PENALTY`.
- Material parameters: `E = 1`, `nu = 0.3`, `Gc = 0.01`, `ell = 0.01`, `res_stiff = 1e-6`.
- Fatigue-on case: `alpha_T = 0.5`.
- Fatigue-off case: `alpha_T = 1e10`.
- Displacement steps: `0.025`, `0.050`, `0.075`, `0.100`, then `0.105:0.005:0.200`.

## Figures

Damage-field figures were rendered with a shared damage scale across both cases:

- `cases/umax020_fatigue_off/figures/damage_steps_20260607/`
- `cases/umax020_fatigue_on/figures/damage_steps_20260607/`

Figure names follow `parent_case_folder_cycleXX.png`, for example:
`umax020_fatigue_off_cycle13.png`.

The combined manifest is:
`cases/soft_hist0_monotonic_24vtk_damage_manifest_20260607.csv`.

## Key Load-Drop Observation

Both cases show the load collapse between step 12 and step 13:

- Step 12: `U = 0.140`, force about `0.0928`.
- Step 13: `U = 0.145`, force about `4.6e-4`.

The damage field correspondingly changes from a half-width crack band to a through-width crack band.
