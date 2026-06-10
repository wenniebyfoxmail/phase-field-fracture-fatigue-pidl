# Brian Review Guide, 10 June 2026

This repository is the GitHub-synced code history for the PIDL fatigue-fracture work. A separate local zip package has been prepared for Brian with selected code, figures, result summaries, and FYR writing:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/BRIAN_CODE_RESULT_PACKAGE_2026-06-10.zip
```

The zip is the cleanest review package. This GitHub branch is useful if Brian wants to inspect the live code history, runner scripts, and shared handover notes.

## Main First-Year Question

The current First Year Report question is:

> Can PIDL reproduce scalar FEM fatigue-life behaviour and achieve field agreement in controlled phase-field fatigue benchmarks?

The conservative current answer is that PIDL can produce plausible scalar/event behaviour in selected controlled cases, but it does not yet reproduce the local FEM fatigue-fracture fields. The main unresolved gap is the local active-driver/history/degradation feedback near the crack tip and retained precrack band.

## Two Stages Of The Work

| Stage | Aim | Typical methods | What it taught us |
|---|---|---|---|
| Stage 1: broad PIDL representation search | Improve NN representation and recover FEM-like fatigue behaviour before the final alignment protocol was fixed. | Williams features, Fourier features, enriched ansatz, exact-BC/Fourier stacks, adaptive sampling, local/tip weighting, weak or oracle supervision, spatial `alpha_T`, fatigue-law variants. | PIDL could move scalar/event behaviour and some local metrics, but stronger representation alone did not reliably produce FEM-like local fields. `N_f` alone is therefore not a safe success criterion. |
| Stage 2: strict FEM/PIDL alignment and diagnosis | Remove avoidable FEM/PIDL mismatch first, then compare scalar history and local fields under a controlled baseline. | Monotonic alignment, soft-hist0 reverseBC FEM, FEM cyclic cadence controls, FEM-mesh PIDL, state-timing comparisons, active-driver/history/degradation audits, precrack fatigue-mask diagnostics. | Initial state and broad event timing can be brought close, but the field-level mechanism still differs. |

## Where To Start In This Repository

For the older Stage 1 method evolution:

```text
docs/advisor_method_evolution_en.md
SENS_tensile/validation_table_all_methods.csv
SENS_tensile/validation_v4_v7_all_methods.csv
```

For the current Stage 2 code path:

```text
SENS_tensile/run_fem_mesh_umax.py
SENS_tensile/run_fem_anchor_bc_umax.py
SENS_tensile/run_fem_mesh_history_driver_umax.py
SENS_tensile/run_fem_mesh_precrack_fatigue_mask_umax.py
SENS_tensile/run_fem_mesh_oracle_field_umax.py
SENS_tensile/run_fem_mesh_local_patch_umax.py
SENS_tensile/run_fem_mesh_fbpinn_umax.py
source/
```

For shared research state and handovers:

```text
docs/research_frontier.md
docs/handovers/windows_fem_outbox.md
docs/handovers/windows_pidl_outbox.md
docs/handovers/csd3_outbox.md
```

## What Is Not In Git

The clean Brian zip, large PIDL archives, large FEM `.mat` handoffs, and generated result folders are intentionally not committed to GitHub. They are local/package artefacts rather than source-control artefacts.

