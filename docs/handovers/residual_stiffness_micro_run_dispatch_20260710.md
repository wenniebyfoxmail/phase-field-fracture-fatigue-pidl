# Residual-Stiffness Micro-Run Dispatch Handover

Created: 2026-07-10T22:47:21+0100 BST
Updated: 2026-07-10T23:05:00+0100 BST
Status: pre-launch / code synced to GitHub branch

## Summary

The next producer-side action is a tiny residual-stiffness/degradation-floor micro-run, not a full production run.

Current scientific claim remains unchanged:

```text
The archived-output event-scale PIDL/FEM comparison is timing-aligned but mechanism-negative. At c89, the active-driver mismatch is degradation-collapse dominated with secondary raw-amplitude under-support.
```

This dispatch tests only whether `residual_stiffness=1e-3` reaches the actual formal hard-recovery runner/export path and lifts active/raw in the c89 event-core masks.

## Launch Gate

Mac-PIDL must not launch training. Producer launch is allowed only after pulling the synced branch/commit below and confirming the runner/export fields exist.

Producer-visible code must include:

```text
SENS_tensile/run_fem_mesh_probe_driver_umax.py supports --res-stiffness
source/model_train.py exports psi_raw_from_g_alpha_elem, psi_raw_from_g_solver_elem, g_solver_override_active
```

Producer-visible sync point:

```text
branch: codex/m2s-framework-validation
commit: 2caf269
commit subject: Add residual-stiffness micro-run gate
```

File hashes to match:

```text
SENS_tensile/run_fem_mesh_probe_driver_umax.py
ec341b2d9e175a5f1deb51a24ae64decdf785b1f4f3bb34be373347001275367

source/model_train.py
9e186c39af9d394d1a12be44ac08a4dbed1b3948c15757ff4cd40ddce14a4f78
```

## Producer Command

Run only after code sync is confirmed:

```bash
CUDA_VISIBLE_DEVICES=<GPU> PIDL_ARCHIVE_DIR=<ARCHIVE_ROOT> \
python3 -u SENS_tensile/run_fem_mesh_probe_driver_umax.py 0.12 \
  --n-cycles-physical 120 \
  --seed 1 \
  --tag hard_d1_u0_recovery_resfloor_micro \
  --history-driver-reduction-mode fem_gp_tri3_g_mean \
  --fem-irr-penalty \
  --hard-alpha-recovery-step \
  --hard-alpha-target 1.0 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --diag-physical-cycles 1,2,3,20,40,60,69,89 \
  --diag-full-physical-cycles 89 \
  --res-stiffness 1e-3
```

The explicit diagnostic flags are required because the runner default diagnostic list does not include cycle 89.

## Required Return Assets

```text
model_settings.txt
stdout/stderr log
run provenance note with command, GPU, branch/commit or snapshot hash, archive root
element_diagnostics_probe_driver/element_fields_cycle_0344.npz
element_diagnostics_probe_driver/element_fields_cycle_0345.npz
element_diagnostics_probe_driver/element_fields_cycle_0444.npz
element_diagnostics_probe_driver/element_fields_cycle_0445.npz
element_diagnostics_probe_driver/element_fields_cycle_0446.npz, if present
element_diagnostics_probe_driver/element_fields_cycle_0447.npz, if present
event/fracture summary, if emitted
```

If the run stops before c89, return the final five diagnostic exports and the event summary. Do not reinterpret c69 as the final event comparison.

## Acceptance Criteria

Accept as a clean micro-run result only if:

```text
model_settings.txt records residual_stiffness = 0.001
formal runner run_fem_mesh_probe_driver_umax.py was used
c89/step444 or clearly documented event-window exports are available
g_alpha_elem and active/raw match eta-floor behavior
active/raw lifts to O(1e-3) in primary masks
active/FEM reaches at least 1e-5 and preferably 3e-5 to 7e-5
raw/FEM remains above 0.01
alpha saturation/overshoot is still reported
```

Quarantine if:

```text
old run_fem_mesh_res_stiff_umax.py was used
eta provenance is missing
active/raw remains O(1e-7)
diagnostic exports lack the new raw-from-g fields
c69 is treated as the final comparison
the result is written as a full FEM/PIDL mechanism fix
```

## After Return

Build a result package under:

```text
local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/residual_stiffness_micro_run_result_<date>/
```

Minimal post-run output:

```text
decision.md
tables/c89_residual_floor_codepath_summary.csv
tables/c89_raw_semantics_consistency.csv
figures/c89_residual_floor_driver_lift_panel.pdf
```
