# GRIPHFiTH Minimal FEM Snapshot for Brian

Source branch:

```text
GRIPHFiTH origin/codex/reversebc-diffuse-precrack-audit
```

This folder contains the FEM/GRIPHFiTH code closest to the current First Year Report baseline. It is not the full GRIPHFiTH repository. Large solver outputs, `.mat` handoffs and unrelated benchmarks are excluded.

## Main FEM Baseline

The current strict FEM baseline is:

```text
Scripts/fatigue_fracture/main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
```

This is the `Umax=0.12` SENT cyclic fatigue reference with:

- retained-material soft diffuse precrack,
- zero initial fatigue history (`alpha_bar = 0`),
- reverseBC boundary condition,
- `AT1 + AMOR + PENALTY`,
- `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`,
- `alpha_T=0.5`,
- standard cyclic retained states through GRIPHFiTH `n_step=8`.

In the current evidence package this FEM reference fractures at about `c69`.

## FEM Cadence Controls

These test whether the FEM result is sensitive to retained loading substeps:

```text
main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_nstep2.m
main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_nstep3.m
main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_nstep10.m
main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_peakonly.m
```

Interpretation:

- unload-retaining FEM variants fracture around `c69-c70`;
- `peakonly` is the outlier and does not represent the cyclic unload-retaining baseline.

## Geometry / Notch Controls

These are included to show what changed before the current soft-hist0 baseline:

```text
main_SENT_PIDL_12_reverseBC.m
main_SENT_PIDL_12_fine_reverseBC.m
main_SENT_PIDL_12_diffuse_precrack_reverseBC.m
```

Use them as diagnostics, not as the current strict baseline.

## Monotonic FEM Reference

The closest monotonic FEM code is:

```text
main_SENT_PIDL_12_fine_reverseBC_monotonic.m
INPUT_SENT_PIDL_12_fine_reverseBC_monotonic.m
```

This supports the monotonic alignment evidence in:

```text
../../1 ALIGNMENT CHECK/Alignment_check_monotonic/
```

## Export / Handoff Scripts

The result package does not include large raw FEM outputs. These scripts show how the handoff/evidence tables were produced:

```text
export_reverseBC_cyclewise_mechanism.m
export_reverseBC_diffuse_precrack_soft_hist0.m
export_reverseBC_soft_hist0_nstep2.m
export_reverseBC_soft_hist0_nstep3.m
export_reverseBC_soft_hist0_nstep10.m
export_reverseBC_soft_hist0_state_timing.m
export_soft_hist0_pidl_like_c1_mixed_row.m
```

The source note for these FEM runs is:

```text
Scripts/fatigue_fracture/FEM_PIDL_REVERSEBC_EXPERIMENTS_2026-05-28.md
```

## Core GRIPHFiTH Code Included

```text
Sources/
Scripts/fatigue_fracture/init_fatigue_fracture.m
Scripts/fatigue_fracture/solve_fatigue_fracture.m
Scripts/fatigue_fracture/accelerate_fatigue_fracture.m
Scripts/fatigue_fracture/jump_cycles.m
Dependencies/SENT_mesh/SENT_mesh.inp
Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp
```

The soft-hist0 baseline itself uses `specimen.internal.plate(...)` to generate the retained-material mesh. The `.inp` files are included because the older reverseBC and fine-mesh diagnostic controls reference them.

## Running Caveat

This is a MATLAB/GRIPHFiTH source snapshot. Running it may require the same MATLAB/MEX/SuiteSparse setup used on the Windows FEM machine. Brian's agent should first read the input/main files and compare them to the evidence tables before attempting a full solve.
