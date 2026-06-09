# FEM Request 23 Patch Note: Explicit Five-Substep State Export

**Date:** 2026-06-09  
**Direction:** Mac-PIDL -> Windows-FEM  
**Purpose:** export FEM state fields at every converged cyclic substep, using the
same explicit global-step convention as the current PIDL diagnostic exports.

## Background

The current aligned FEM export contains selected states:

```text
state0_initial_unloaded_prehistory
c1_step1, c1_step2, c1_step3, c1_peak, c1_unloaded
c2/c3/c20/c40/c60/c69 peak and unloaded
```

This is enough for peak/unload comparisons, but it still leaves ambiguity when
checking the full five-substep PIDL sequence. PIDL now records explicit global
diagnostic steps. FEM should provide the same explicit step-indexed state
package so Mac can compare each saved PIDL step without using load-scaled
approximations for intermediate states.

## Required Run / Export

Please run or export the FEM case with complete five-substep records.

Primary target:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask
```

If the precrack-fatigue-driver-mask variant from Request 22 has not started yet,
please combine this export requirement with that run. If the run has already
started, either rerun it with complete state saving or add complete state capture
if the solver can still save all converged substeps safely.

Optional but useful:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
```

If existing standard FEM checkpoints/history are enough to re-export all
substeps without rerunning, please also provide a standard baseline explicit
substep package. Do not delay the masked package for this optional baseline.

## Explicit State Mapping

Use this exact index convention:

```text
fem_global_step = 5*(cycle - 1) + (substep - 1)

cycle c, substep 1, load 0.25 -> fem_global_step 5*(c-1)+0 -> c<c>_step1
cycle c, substep 2, load 0.50 -> fem_global_step 5*(c-1)+1 -> c<c>_step2
cycle c, substep 3, load 0.75 -> fem_global_step 5*(c-1)+2 -> c<c>_step3
cycle c, substep 4, load 1.00 -> fem_global_step 5*(c-1)+3 -> c<c>_peak
cycle c, substep 5, load 0.00 -> fem_global_step 5*(c-1)+4 -> c<c>_unloaded
```

Examples:

```text
c1_step1    -> fem_global_step 0
c1_step2    -> fem_global_step 1
c1_step3    -> fem_global_step 2
c1_peak     -> fem_global_step 3
c1_unloaded -> fem_global_step 4
c69_peak    -> fem_global_step 343
c69_unloaded-> fem_global_step 344
```

This should match PIDL's global diagnostic step numbering for the same physical
cycle/substep schedule.

## What To Save

Save state immediately after each converged substep history refresh. For the
precrack-fatigue-driver-mask variant, save after applying the
PIDL-equivalent fatigue-driver/history mask, and label the package as masked
fatigue-history state. Raw mechanics fields should still be exported and
clearly labeled.

Please include:

```text
state0_initial_unloaded_prehistory
c1_step1 ... c1_unloaded
c2_step1 ... c2_unloaded
...
c69_step1 ... c69_unloaded
```

That is:

```text
1 initial state + 69 cycles * 5 substeps = 346 state records
```

If the final cycle differs because the run stops early or late, record the exact
last converged cycle/substep in the README and state index.

## Required State Index

Include a CSV with at least:

```text
row_index
state_label
physical_cycle
substep
load_factor
fem_global_step
pidl_global_step_expected
is_peak
is_unloaded
mask_applied
time_or_increment_index
source_notes
```

For this five-substep schedule, `pidl_global_step_expected` should equal
`fem_global_step` for loaded cycle states.

## Required MAT Fields

Use the same field names as the previous aligned export where possible:

```text
d_elem
alpha_bar_elem
f_fatigue_elem
g_stiffness_elem
psi_plus_elem
g_psi_plus_elem
f_g_psi_plus_elem
epsilon_elem
principal_stress_raw_elem
principal_stress_degraded_effective_elem
sigma_raw_elem
sigma_degraded_effective_elem
element_centroids
element_area
```

For the precrack-fatigue-driver-mask variant, include or document:

```text
raw_psi_plus_elem is raw mechanics
alpha_bar_elem / f_fatigue_elem are post-mask fatigue-history state
mask_support_elem or precrack_fatigue_driver_mask_elem
```

## Suggested Output Folders

Primary masked package:

```text
~/Downloads/_pidl_handoff_v2/latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609/
```

Optional standard baseline package:

```text
~/Downloads/_pidl_handoff_v2/latest_align_soft_hist0_explicit_steps_20260609/
```

Required files:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv
mesh_geometry.mat
precrack_fatigue_driver_mask_region_audit.csv
README_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.md
INPUT_*.m
solve_fatigue_fracture.m
export script(s)
run log
```

For optional standard baseline, use the same names without
`precrackFatigueDriverMask`.

## Acceptance Criteria

Mac can accept the package if:

1. Every converged substep has a state record, not only selected peak/unload
   states.
2. The state index uses the exact `fem_global_step = 5*(cycle-1)+(substep-1)`
   mapping.
3. `c1_peak` is step 3 and `c1_unloaded` is step 4.
4. `c69_peak` is step 343 and `c69_unloaded` is step 344.
5. The README states whether each exported fatigue-history field is raw or
   post-mask.
6. Mesh, material, BCs, loading, and precrack damage profile remain unchanged
   relative to the strict soft-hist0 reference, except for the Request 22
   precrack-history mask if this is the masked variant.
