# Case File Guide

Each folder under `cases/` keeps the original handoff contents.

Typical files:

- `monitorcycle.dat`: cycle/step monitor data.
- `extra_scalars.dat`: additional scalar diagnostics.
- `load_displ_*.out`: load-displacement response.
- `fields_*.vtk`: full exported field trajectory for the case.
- `peak_load_c1.vtk`: peak-load field snapshot.
- `checkpoint.mat`: GRIPHFiTH/MATLAB checkpoint.
- `crack_regularized.dat`: crack/damage profile data.
- `cputime.dat`: runtime information.
- `CONV_*.log`: per-step convergence logs.
- `psi_fields/cycle_0001.mat`: first-cycle psi-field export.

Case file counts copied into this package:

| Case | Files |
|---|---:|
| `umax012_fatigue_off` | 17 |
| `umax012_fatigue_on` | 17 |
| `umax020_fatigue_off` | 33 |
| `umax020_fatigue_on` | 33 |

Top-level support files:

- `docs/README_pidl_aligned_monotonic_four_cases.md`
- `docs/monotonic_four_case_summary.csv`
- `scripts/INPUT_SENT_PIDL_12_fine_reverseBC_monotonic.m`
- `scripts/main_SENT_PIDL_12_fine_reverseBC_monotonic*.m`
