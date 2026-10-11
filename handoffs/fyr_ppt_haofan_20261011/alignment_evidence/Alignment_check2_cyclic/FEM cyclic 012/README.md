# FEM cyclic Umax=0.12 loading-step package

This folder collects the FEM cyclic loading-step controls for the strict
soft-hist0 reverseBC Umax=0.12 alignment check.

Structure:

- `cases/`: one folder per loading-step case, each with `setting.md`, `raw_data/`, `analysis/`, `figures/`, and `docs/`.
- `analysis/`: regenerated CSV summaries and mechanism reductions.
- `figures/`: cadence, energy, and ratio figures.
- `docs/`: interpretation notes and Windows-FEM handover record.

Cases included:

- `standard`: retained load factors `[0.25, 0.5, 0.75, 1, 0]`, penetration `N_f=69`.
- `peak_only`: retained load factor `[1]`, no penetration by c120.
- `n_step_2`: retained load factors `[1, 0]`, penetration `N_f=70`.
- `n_step_3`: retained load factors `[0.5, 1, 0]`, penetration `N_f=70`.
- `n_step_10`: retained load factors `[0.2, 0.4, 0.6, 0.8, 1, 0]`, penetration `N_f=69`.
- `state_timing`: cycle-1 timing export used to label mixed FEM states.

Main reading: peak-only is the outlier. FEM cases that retain the unload/end-of-cycle state fracture at c69-c70 and have nearly identical event-level damage-energy paths.
