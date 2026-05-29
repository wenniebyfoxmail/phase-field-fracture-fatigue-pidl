# PIDL FEM-Mesh State-Timing Audit

Date: 2026-05-29

## Purpose

This audit checks the remaining cycle-index ambiguity after the soft-hist0 FEM
state-timing export.  The comparison uses the FEM-derived soft-hist0 PIDL mesh
as the main benchmark because it removes the old PIDL geometry as a first-order
source of mismatch.

The two tested mappings are:

```text
FEM c1 mixed timing -> PIDL saved j=0
FEM c1 mixed timing -> PIDL saved j=1
```

Here "FEM c1 mixed timing" means the object that matches the old FEM c1 export:
damage/history/f from `cycle1_unloaded_post_history_refresh`, and tensile
driver from `psi_plus_peak_to_date`.

## Outputs

```text
SENS_tensile/compare_pidl_state_timing_mappings.py
SENS_tensile/plot_pidl_mesh_comparison.py
_analysis_fem_mechanism_20260528/pidl_femmesh_state_timing_mapping_j0_j1.csv
_analysis_fem_mechanism_20260528/pidl_femmesh_state_timing_fields_j0_j1.npz
_analysis_fem_mechanism_20260528/figures/pidl_femmesh_state_timing_mapping_j0_j1.png
_analysis_fem_mechanism_20260528/figures/pidl_mesh_geom2_vs_fem_soft_hist0.png
_analysis_fem_mechanism_20260528/figures/pidl_mesh_geom2_vs_fem_soft_hist0.csv
```

The `.npz` is a local analysis artifact and is not intended as a lightweight
handoff; the CSV and PNG are the review artifacts.

## Mesh Reminder

| Mesh | Nodes | Triangles | Median element area | Tip elements `r<=4l0` | Precrack-strip elements |
|---|---:|---:|---:|---:|---:|
| old PIDL `meshed_geom2.msh` | 33,749 | 67,276 | `1.73e-6` | 2,919 | 11,599 |
| FEM-derived soft-hist0 mesh | 45,591 | 90,000 | `2.00e-6` | 2,516 | 10,000 |

The old PIDL mesh is an unstructured triangular refinement with a very dense
horizontal crack band.  The FEM-derived soft-hist0 mesh is a structured
triangularization of the FEM Q4 mesh, so it is much cleaner for common-probe
alignment even though it does not automatically fix the physics/history gap.

## Timing Mapping Result

Selected PIDL/FEM ratios:

| Field/metric | PIDL `j=0` / FEM c1 | PIDL `j=1` / FEM c1 | Reading |
|---|---:|---:|---|
| damage `tip_2l0_mean` | 1.008 | 1.015 | Both close. |
| damage p99 | 0.946 | 0.948 | Both slightly lower than FEM. |
| `alpha_bar` domain mean | 0.915 | 1.830 | `j=0` is closer. |
| `alpha_bar` tip_2l0_mean | 0.985 | 1.968 | `j=1` has already accumulated another cycle of local history. |
| `alpha_bar` max | 1.835 | 3.615 | Both have a hotter pointwise max than FEM; `j=0` is less wrong. |
| active `psi_plus` tip_2l0_mean | 1.013 | 1.011 | Both close near the tip. |
| active `psi_plus` p99 | 1.053 | 1.055 | Both close in high-percentile driver. |

Conclusion: for the cycle-1 field comparison, PIDL saved `j=0` is the better
mapping.  PIDL saved `j=1` is already one history increment too late for
`alpha_bar`, even though damage and active driver still look similar.

## Three Gap Separation

### 1. Initialization Gap

Mostly controlled now.

The soft-hist0 benchmark aligns retained material, diffuse precrack, initial
`alpha_bar=0`, and initial `f=1`.  The remaining initialization caveat is that
PIDL's pretraining alpha can be slightly different from the analytic initial
profile, but the c1 timing audit says this is not the main late-cycle gap.

### 2. History-Refresh / Cycle-Timing Gap

Partly controlled, still important.

The `j=0` mapping fixes the first-cycle comparison better than `j=1`, but this
is still a post-hoc saved state.  Current PIDL checkpoints are saved after
history refresh, so we cannot exactly reconstruct pre-history-refresh PIDL
states from existing archives.

This is the next code-instrumentation target if the paper needs strict state
labels:

```text
PIDL preload/prehistory
PIDL post damage solve, pre fatigue-history refresh
PIDL post fatigue-history refresh
PIDL unloaded/reset state, if represented
```

### 3. Representation / Localization Gap

Still open.

After using the FEM-derived mesh and the better c1 mapping, the late-cycle
result remains:

```text
c69 damage location/mean: close
c69 alpha_bar p99 and tip history: PIDL low
c69 active psi_plus near tip: PIDL low
c69 incremental E_d: PIDL about 0.25x FEM
```

So mesh and first-cycle timing do not fully explain the mechanism gap.  The
current evidence points to how PIDL creates, localizes, and remembers local work
over many cycles.

## FEM-Side Setting Tests

Because FEM is cheaper than PIDL GPU sweeps, we should keep using FEM one-factor
reruns before launching broad PIDL variants.  This is reasonable as long as each
FEM run answers one alignment question.

Already useful FEM controls:

```text
tol_irrev=5e-3       -> N_f=68, so tolerance alone is not the gap.
peak-only history    -> no penetration by c120, so substep/history refresh matters.
res_stiff=0          -> N_f=69, so residual stiffness is not the gap.
soft-hist0 state timing -> old c1 timing trap identified.
```

Recommended next FEM-side controls:

1. Export a FEM "PIDL-like c1 row" explicitly, using the same mixed timing we
   compare here, so future scripts cannot silently mix states.
2. If we change PIDL fatigue-update semantics, run the FEM analogue first when
   possible: peak-only, substep count, history refresh point, or irreversibility
   tolerance.
3. Avoid changing many FEM settings at once.  FEM is cheap, but multi-change FEM
   runs can create the same interpretability problem as broad PIDL sweeps.

## Current Decision

Use FEM-mesh PIDL with PIDL saved `j=0` mapped to FEM c1 as the main benchmark
for first-cycle-aligned comparisons.  Keep old `geom2` results as historical
context only, not as the primary alignment evidence.
