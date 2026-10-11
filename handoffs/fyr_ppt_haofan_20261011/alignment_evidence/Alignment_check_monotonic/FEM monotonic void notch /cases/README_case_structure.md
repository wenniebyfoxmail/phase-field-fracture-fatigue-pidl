# FEM Monotonic Case Structure

Each available FEM case is organized to match the PIDL monotonic case folders.

- `_source/resources/`: original FEM handoff files (`*.vtk`, `*.dat`, `*.out`, `*.log`, checkpoint, and `psi_fields/`).
- `_source/processed/`: parsed CSV tables generated from the FEM text resources.
- `figures/`: rendered field and load-displacement figures for the available FEM snapshots.
- `cases/figures/`: combined Umax0.2 comparison figures across the available fatigue-on/off cases.

Current local availability: only `umax020_fatigue_off` and `umax020_fatigue_on` are present in this `cases/` folder.
The handoff README documents Umax0.12 cases too, but those folders are not currently present locally.

Field-figure caveat: the available FEM resources contain final `fields_000001_024.vtk` and `peak_load_c1.vtk`, not one VTK file per load step.
- `umax020_fatigue_off`: 7 PNG figures generated.
- `umax020_fatigue_on`: 7 PNG figures generated.
