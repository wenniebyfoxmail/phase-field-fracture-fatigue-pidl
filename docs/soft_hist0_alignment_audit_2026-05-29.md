# Soft-Hist0 FEM/PIDL Alignment Audit

Date: 2026-05-29

Status: Historical alignment audit for the soft-hist0 comparison state as of
2026-05-29. Use as provenance for old results, not as the current analysis
protocol.

## Purpose

This note audits the current "strict alignment" status before using FEM/PIDL
differences as evidence about architecture or optimisation.  The reference
setting is the soft-hist0 diffuse precrack reverseBC case:

- retained material in the precrack band,
- soft diffuse precrack damage rather than void slit or hard `d=1`,
- initial fatigue history `alpha_bar=0`,
- initial fatigue degradation `f=1`,
- reverseBC `u_max=0.12`.

## Data Sources

FEM reference and one-factor controls:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_tolir5e3_2026-05-29
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_2026-05-29
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_resstiff0_2026-05-29
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29
```

PIDL/Taobo diagnostic runs:

```text
tol_ir=1e-3:
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/...tolir1e3...

explicit substeps:
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/...explicit_cycle...

FEM-mesh PIDL:
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/...femmesh_softHist0...
```

Local audit outputs:

```text
_analysis_fem_mechanism_20260528/soft_hist0_alignment_audit_summary_20260529.csv
_analysis_fem_mechanism_20260528/figures/soft_hist0_alignment_audit_scalars_20260529.png
```

## What Is Aligned Now

The clean benchmark is now much better aligned than the older comparisons.

| Item | Current status |
|---|---|
| Boundary condition | Aligned to reverseBC `u=0.12`. |
| Precrack material | Aligned to retained-material diffuse precrack, not void. |
| Initial fatigue history | Aligned in intent: `alpha_bar=0`, `f=1`. |
| FEM state timing | FEM Request 20 separates state0, peak pre/post history refresh, and unloaded post-history states. |
| Mesh/probe comparison | FEM-mesh PIDL exists and common-probe comparisons exist. |
| Absolute vs incremental energy | Now separated; absolute `E_d` includes the initial diffuse precrack energy. |

The FEM-mesh PIDL result is the cleanest immediate check.  By c69 the damage
tip mean on common probes is almost aligned (`damage_alpha tip_2l0_mean`
PIDL/FEM = 1.013), but the history and active driver are not:

```text
c69 alpha_bar max PIDL/FEM        = 0.509
c69 alpha_bar p99 PIDL/FEM        = 0.191
c69 alpha_bar tip_2l0 PIDL/FEM    = 0.466
c69 psi_plus_active tip_2l0 ratio = 0.028
c69 Delta E_d PIDL/FEM            = 0.251
```

This means mesh/probe alignment improves the damage-position comparison, but
does not remove the late local history/energy gap.

## What Is Not Strictly Aligned Yet

The biggest remaining trap is state timing.

FEM Request 20 showed that the old FEM c1 row was not an initial state.  Its
damage/history fields correspond to `cycle1_unloaded_post_history_refresh`,
while `psi_plus` is a peak-to-date quantity.  Therefore c1 can only be compared
fairly after naming the state.

PIDL still needs the same state naming.  In `source/model_train.py`, the main
loop is zero-based (`j=0,1,...`), then `hist_alpha` is updated after training,
then fatigue history/degradation are refreshed, and only then are the model and
checkpoint saved.  Therefore a saved `trained_1NN_0.pt` / `checkpoint_step_0.pt`
is a post-refresh state for the first PIDL loop index, not a clean preload or
pre-history state.

Relevant PIDL code locations:

```text
source/model_train.py:600-603   main loop and zero-based j
source/model_train.py:683-686   hist_alpha irreversibility update
source/model_train.py:794-813   hist_fat and f_fatigue update
source/model_train.py:1005-1019 saved model/checkpoint after updates
source/utils.py:73-120          analytic AT1 initial crack profile
```

The current scalar plots use a "cycle-like index" for PIDL.  For standard PIDL
this is saved index `j+1`; for explicit substeps this is substep index divided
by 5.  That is useful for diagnosis, but not yet a strict FEM-cycle state match.

## One-Factor Diagnostics

| Case | Result | Meaning |
|---|---:|---|
| FEM soft-hist0 baseline | `N_f=69` | Current aligned FEM reference. |
| FEM `tol_irrev=5e-3` | `N_f=68` | Matching PIDL tolerance alone does not explain the FEM/PIDL gap. |
| FEM peak-only | no penetration by c120 | Within-cycle/substep history refresh is decisive in FEM. |
| FEM `res_stiff=0` | `N_f=69` | Residual stiffness is not the main driver of the current gap. |
| PIDL `tol_ir=1e-3` | first detected c85, confirmed c95 | Stronger irreversibility tolerance did not move PIDL toward FEM c69. |
| PIDL explicit substeps | no fracture by 40 physical cycles | The current explicit-cycle semantics strongly change history accumulation. |
| PIDL FEM-mesh | first detected c82, confirmed c85 | Mesh/probe alignment helps, but history peak and incremental `E_d` remain low. |

## Current Interpretation

The huge early differences were mostly setting differences: void notch versus
diffuse precrack, hard/pre-fatigued crack band versus soft hist0, and mixed FEM
c1 timing.  After those are repaired, the comparison is much cleaner.

The remaining gap is not mainly "crack-tip position" at one late cycle.  It is
the coupled route by which the solver creates and remembers local work:

```text
local tensile driver psi_plus -> fatigue history alpha_bar -> degradation f
-> elastic relaxation/stress redistribution -> next psi_plus
-> damage growth and incremental E_d
```

FEM and PIDL can look close in damage position while still disagreeing in the
late local history peak and the incremental damage energy.  That is why we
should not claim the mechanism is aligned from c70/c75 position alone.

## What To Do Next

1. Export PIDL state timing for the first loop index: preload/prehistory,
   post-damage-solve pre-history-refresh, post-history-refresh, and any
   unloaded/reset state the current PIDL loop implies.
2. Re-run common-probe comparisons with two mappings: PIDL saved `j=0` to FEM
   c1, and PIDL saved `j=1` to FEM c1.  This quantifies the one-step timing
   ambiguity directly.
3. Use the FEM peak-only and PIDL explicit-substep results to decide whether the
   fatigue-history refresh law is the next thing to align, before changing NN
   architecture.
4. Keep the FEM-mesh PIDL archive as the main scalar/field benchmark.  It tells
   us mesh is not the whole story because the damage location improves but
   `alpha_bar`, active `psi_plus`, and incremental `E_d` still lag.

Only after this timing audit should we interpret patch-strength, branch-restart,
or local-head experiments as evidence about the NN representation.
