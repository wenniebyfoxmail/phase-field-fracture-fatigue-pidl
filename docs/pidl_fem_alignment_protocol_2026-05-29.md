# PIDL/FEM Alignment Protocol

Date: 2026-05-29

## What "History Timing" Means

History timing is the moment in the nonlinear cycle loop when the solver updates
memory variables:

```text
damage irreversibility memory: hist_alpha
fatigue history:              alpha_bar
fatigue degradation:          f(alpha_bar)
previous tensile driver:      psi_plus_prev / peak-to-date psi_plus
```

The same label, such as "cycle 1", can describe different states:

```text
before loading
after damage solve but before fatigue history refresh
after peak-load history refresh
after unloading/end-of-cycle history refresh
```

FEM Request 20 showed that the old FEM c1 handoff was a mixed state:

```text
d / alpha_bar / f: cycle1_unloaded_post_history_refresh
psi_plus:          cycle1 psi_plus_peak_to_date
```

The PIDL state-timing audit then showed this FEM c1 mixed state maps best to
PIDL saved `j=0`, not PIDL saved `j=1`.

## Current Protocol

Use this convention for the soft-hist0 reverseBC alignment track:

```text
FEM reference:        soft-hist0 retained-material reverseBC FEM
PIDL reference:       FEM-mesh PIDL, not old geom2 PIDL
cycle mapping:        FEM cycle c -> PIDL saved index j = c - 1
first-cycle mapping:  FEM c1 mixed timing -> PIDL saved j=0
energy reporting:     keep absolute E_d and Delta E_d separate
field reporting:      include alpha_bar p99/p999, near-tip integrals, active psi_plus, and damage width/position
```

The shared constants are recorded in:

```text
SENS_tensile/pidl_fem_alignment_protocol.py
```

## Priority Order Now

1. Lock scripts to the current comparison protocol.
   - Add explicit `pidl_cycle_offset=-1` where cyclewise FEM/PIDL fields are
     compared.
   - Use FEM-mesh PIDL as the default for this alignment track.

2. Regenerate cyclewise common-probe evidence with the corrected mapping.
   - Compare FEM c1/c20/c40/c69 to PIDL j0/j19/j39/j68.
   - Re-check when `alpha_bar`, active `psi_plus`, and `Delta E_d` start
     separating.

3. Add true PIDL state-timing instrumentation.
   - Existing PIDL checkpoints are saved after history refresh.
   - Future PIDL runs should export prehistory, post damage solve/pre-refresh,
     post-refresh, and reset/unload-equivalent states.

4. Wait for FEM Request 21.
   - The `n_step=2/3/10` FEM controls will tell us how much of the late-cycle
     gap is explained by substep/history-refresh cadence.

5. Run only one matched PIDL substep diagnostic.
   - Use FEM's retained load factors/history-refresh points from Request 21.
   - Do this before another broad architecture or patch sweep.

## Why This Matters

Without this protocol, we can accidentally create a false mechanism gap by
comparing:

```text
FEM c1 post-refresh state vs PIDL j1 post-refresh state
old geom2 PIDL vs FEM-derived mesh FEM
absolute E_d including initial precrack vs incremental E_d after c1
current psi_plus vs peak-to-date psi_plus
```

Those are bookkeeping differences, not necessarily physics differences.  After
the protocol is locked, any remaining gap is more likely to be a real solver or
representation issue.

## Protocol-Shifted Evidence

The corrected cyclewise common-probe run now compares:

```text
FEM c1/c20/c40/c69 -> PIDL j0/j19/j39/j68
```

Outputs:

```text
_analysis_fem_mechanism_20260528/femmesh_pidl_vs_soft_hist0_fem_probe_j0map_c1_c20_c40_c69.csv
_analysis_fem_mechanism_20260528/femmesh_j0map_common_probe_residual_summary.csv
_analysis_fem_mechanism_20260528/figures/femmesh_j0map_common_probe_residual_damage_alpha.png
_analysis_fem_mechanism_20260528/figures/femmesh_j0map_common_probe_residual_alpha_bar.png
_analysis_fem_mechanism_20260528/figures/femmesh_j0map_common_probe_residual_fatigue_f.png
_analysis_fem_mechanism_20260528/figures/femmesh_j0map_common_probe_residual_psi_plus_active.png
```

Selected ratios after applying the `j=c-1` mapping:

| FEM cycle -> PIDL index | damage tip_2l0 | alpha_bar tip_2l0 | alpha_bar p99 | active psi tip_2l0 |
|---|---:|---:|---:|---:|
| c1 -> j0 | 1.008 | 0.985 | 0.421 | 1.013 |
| c20 -> j19 | 0.996 | 0.946 | 0.928 | 1.150 |
| c40 -> j39 | 1.002 | 0.792 | 0.430 | 0.245 |
| c69 -> j68 | 1.012 | 0.466 | 0.191 | 0.029 |

Reading: the first-cycle mapping is now clean, and the damage tip mean remains
close even late.  The mechanism gap opens later through local history and the
active near-tip driver: by c40 the near-tip active driver is already only about
0.25x FEM, and by c69 it is about 0.03x FEM.
