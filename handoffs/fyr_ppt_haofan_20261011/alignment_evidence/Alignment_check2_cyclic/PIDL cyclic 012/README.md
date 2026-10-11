# PIDL cyclic Umax=0.12 loading-step package

This folder collects PIDL cyclic loading-step diagnostics for Umax=0.12.

Structure:

- `cases/`: one folder per loading-step case, each with `setting.md`, `raw_data/`, `analysis/`, `figures/`, `docs/`, and `logs/` where available.
- `analysis/`: scalar summaries, energy comparisons, and manifest CSVs.
- `figures/`: energy and alignment figures.
- `docs/`: interpretation notes and historical setting notes.

For the Taobo state-timing runs, `raw_data/` includes the optimisation evidence too:
`TBruns/` TensorBoard event folders and `intermediate_models/` training snapshots.

Cases included:

- `one_peak_femmesh_softHist0_N100`: strict FEM-mesh one-peak baseline.
- `explicit_cycle_0_0p5_1_0p5_0_Nphys40_Nstep200`: older explicit-cycle diagnostic with `[0, 0.5, 1, 0.5, 0]`.
- `stateTiming_onepeak_untilFrac_Nphys100_Nstep100`: latest instrumented
  one-peak until-fracture run, with stateTiming snapshots and gradient-balance
  evidence.
- `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`: latest instrumented
  FEM-like substep until-fracture run with `[0.25, 0.5, 0.75, 1, 0]`.

Main reading: PIDL substep diagnostics exist, but they did not by themselves
close the FEM/PIDL field-energy mismatch. The clean energy comparison still
shows PIDL damage-energy growth at about 25% of FEM by c69. The latest
until-fracture one-peak and FEM-like substep PIDL runs fracture in a similar
physical-cycle window, around c82.
