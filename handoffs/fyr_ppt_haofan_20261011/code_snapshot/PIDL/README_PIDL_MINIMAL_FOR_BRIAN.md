# PIDL Minimal Snapshot for Brian

This folder contains the PIDL source and the top-level scripts needed to understand the current First Year Report evidence. It excludes the large PIDL archive folders and raw training outputs.

## Folder Layout

```text
source/                 reusable PIDL modules
SENS_tensile_minimal/   runnable/top-level SENT scripts and small mesh files
```

The scripts in `SENS_tensile_minimal/` expect `source/` to be one directory above them, matching the original project layout.

## Main PIDL Baseline / Controls

The current PIDL side of the baseline is the FEM-mesh soft-hist0 family.

Start with:

```text
SENS_tensile_minimal/config.py
SENS_tensile_minimal/main.py
SENS_tensile_minimal/run_fem_mesh_umax.py
```

`run_fem_mesh_umax.py` is the clean FEM-mesh PIDL runner. It keeps the baseline objective and architecture, but uses a triangularised FEM reference mesh.

Important mesh files included:

```text
meshed_geom1.msh                  legacy coarse pretrain mesh
meshed_geom2.msh                  legacy PIDL fine mesh
meshed_geom_fem_baseline.msh      FEM-derived baseline mesh
meshed_geom_fem_soft_hist0.msh    soft-hist0 FEM-derived mesh used by current alignment work
```

## Current Diagnostic Runners

These are the most relevant PIDL scripts for the current Chapter 5 story.

| Script | Purpose |
|---|---|
| `run_fem_mesh_umax.py` | Main FEM-mesh PIDL forward baseline/control. |
| `run_fem_anchor_bc_umax.py` | Boundary-condition alignment diagnostic. |
| `run_explicit_cycle_umax.py` | Older explicit substep smoke diagnostic on the default PIDL mesh. |
| `run_fem_mesh_precrack_fatigue_mask_umax.py` | Retained-material precrack fatigue/history mask diagnostic. |
| `run_fem_mesh_probe_driver_umax.py` | Probe-averaged `g(alpha)` driver reduction diagnostic. |
| `run_fem_mesh_history_driver_umax.py` | Raw/lagged/current active history-driver comparison. |
| `run_fem_mesh_oracle_field_umax.py` | Oracle field-injection diagnostic for testing which field closes the gap. |
| `run_fem_mesh_staged_alpha_umax.py` | Head-staging / alpha training-sequence diagnostic. |
| `run_fem_mesh_inverse_alphaT_umax.py` | Scalar fatigue-parameter inverse calibration diagnostic. |
| `run_fem_mesh_fbpinn_umax.py` | Domain-decomposition/local representation diagnostic. |
| `run_fem_mesh_local_patch_umax.py` | Local patch representation diagnostic. |
| `run_fem_mesh_adaptive_lambda_hist_umax.py` | Adaptive/history-weight diagnostic. |
| `run_fem_mesh_monotonic_fatigue_off.py` and `run_fem_mesh_monotonic_fatigue_on.py` | Monotonic FEM/PIDL alignment checks. |
| `run_m2s_next_stage_feasibility.py` | Measurement-to-state/RUL feasibility tests. |

## Analysis / Export Scripts

These scripts connect raw PIDL/FEM runs to the evidence tables and figures:

```text
export_pidl_element_diagnostics.py
export_pidl_mapped_state_fields.py
compare_fem_pidl_cyclewise_mechanism.py
compare_femmesh_pidl_incremental_energy.py
compare_pidl_state_timing_mappings.py
compare_pidl_to_fem_nstep2_timing.py
compute_field_level_score_v0.py
audit_active_driver_definitions.py
analyze_soft_hist0_state_timing.py
posthoc_mesh_probe_alignment.py
plot_fem_pidl_residual_fields.py
```

The corresponding result evidence is in:

```text
../../1 ALIGNMENT CHECK/Alignment_check2_cyclic/
../../1 ALIGNMENT CHECK/Alignment_check_monotonic/
```

## Minimal Run Examples

These commands are examples for Brian's agent to inspect. Run them from the package root. Full training should be run on a GPU machine, not on a laptop.

Baseline FEM-mesh PIDL:

```bash
cd "0 CODE/PIDL/SENS_tensile_minimal"
python run_fem_mesh_umax.py 0.12 --mesh-file meshed_geom_fem_soft_hist0.msh --n-cycles 100 --seed 1
```

Older explicit substep smoke diagnostic:

```bash
cd "0 CODE/PIDL/SENS_tensile_minimal"
python run_explicit_cycle_umax.py 0.12 --n-cycles 5 --seed 1 --substeps 0,0.5,1,0.5,0
```

Current FEM-mesh precrack fatigue/history mask diagnostic:

```bash
cd "0 CODE/PIDL/SENS_tensile_minimal"
python run_fem_mesh_precrack_fatigue_mask_umax.py 0.12 --n-cycles-physical 120 --mesh-file meshed_geom_fem_soft_hist0.msh --seed 1
```

## Current Interpretation

The PIDL code can produce scalar/event behaviour in the same broad range as the FEM reference, but the local fields are not yet FEM-like. The key unresolved mismatch is not just raw `psi+`; it is the spatial feedback among damage, active driver `g(alpha) psi+`, fatigue history, fatigue degradation and local stiffness response.
