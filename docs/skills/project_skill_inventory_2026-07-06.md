# Project Skill Inventory

**Date**: 2026-07-06
**Purpose**: legacy inventory of project-local skills/workflows. Current machine
authorisation comes from `AGENTS.md`; CSD3 is not a default producer.

## Shared Project Skills

| Skill / workflow | Location | Trigger | Output |
|---|---|---|---|
| Road-Fracture Experiment Gate | `docs/skills/road-fracture-experiment-gate/SKILL.md` | Any claim-changing observation/data, measurement/inverse, transition/prediction, decision, or physics/surrogate Experiment. | Claim-class and evidence-domain routing, minimum validity prerequisites, one primary criterion, stop rule, and bounded claim impact. |
| PIDL/FEM Experiment Gate | `docs/skills/pidl-experiment-gate/SKILL.md`; `docs/skills/pidl-experiment-gate/scripts/pidl_attempt_ledger.py` | Physics-specific PIDL/FEM, teacher, field-mechanism, residual, GNO/PINO, or Hard-5 work. | Compatibility route into the shared gate plus physics-specific state semantics and optional legacy sub-attempt ledger. |
| Paper Ledger To Paper | `docs/skills/paper-ledger-to-paper/SKILL.md` | Turning evolving mechanism results into a tagged research ledger before paper prose. | Tagged record with `[CORE]`, `[EVID]`, `[CAVEAT]`, `[PENDING]`, `[MOVE]`, `[SPEC]`. |

## Code-Execution Workflows To Treat As Skills

| Workflow | Canonical docs | Code entrypoints | Alignment rule |
|---|---|---|---|
| Taobo GPU submission | `docs/taobo_gpu_submission_protocol.md`; `docs/git_workflow.md` | PIDL runners under `SENS_tensile/run_*.py` | Mac prepares/commits; Taobo runs with attributable root, `CUDA_VISIBLE_DEVICES`, archive root, log, PID/GPU. |
| FEM/PIDL state alignment | `docs/pidl_fem_alignment_protocol_2026-05-29.md`; `docs/pidl_fem_diagnostic_analysis_protocol_2026-06-21.md` | `SENS_tensile/pidl_fem_alignment_protocol.py`; `export_pidl_mapped_state_fields.py`; `compare_*` scripts | Compare by state label and field semantics, not by raw loop index. |
| Active-driver process-zone metric | `docs/active_driver_process_zone_metric_2026-06-28.md` | `SENS_tensile/compute_process_zone_metrics.py`; `diagnose_nstep2_active_driver_colocation.py`; `plot_process_zone_comparison.py` | A scalar event improvement is not field closure unless this gate improves. |
| Posthoc field comparison | `docs/field_level_comparison_metric_plan.md`; `docs/field_level_metric_results_2026-05-28.md` | `posthoc_pidl_vs_fem_trajectory.py`; `posthoc_element_tip_criterion.py`; `posthoc_lbfgs_polish_audit.py`; `summarize_lbfgs_polish_audit.py` | Use existing archives before launching new training. |
| M2S framework validation | `docs/m2s_framework_validation_2026-05-31.md`; `docs/m2s_next_stage_feasibility_2026-05-31.md` | `run_m2s_synthetic_validation.py`; `run_m2s_next_stage_feasibility.py` | Keep forecast validation separate from forward PIDL field mismatch claims. |
| Producer execution and handovers | `AGENTS.md`; `docs/git_workflow.md`; producer-specific protocols and historical handovers | Direct SSH to an authorised producer or a named handover | Use fresh Run IDs and receipts; direct SSH does not waive the Experiment gate; never fall back to CSD3 silently. |

## Runner Families

| Family | Representative scripts | Current stance |
|---|---|---|
| Strict FEM-mesh cyclic PIDL | `run_fem_mesh_umax.py`, `run_fem_mesh_probe_driver_umax.py`, `run_fem_mesh_res_stiff_umax.py` | Use only behind the PIDL Experiment Gate and process-zone criteria. |
| State/restart diagnostics | `run_fem_state_restart_umax.py`, `run_fem_mesh_c1_altmin_probe.py`, `run_fem_mesh_frozen_alpha_elastic_probe.py` | Prefer before long production runs when the question is state sufficiency or early feedback. |
| History/driver diagnostics | `run_fem_mesh_history_driver_umax.py`, `run_fem_mesh_precrack_fatigue_mask_umax.py` | Raw/lagged are already negative brackets; only bounded/mixed variants deserve gated tests. |
| Representation/localization | `run_fem_mesh_local_patch_umax.py`, `run_fem_mesh_fbpinn_umax.py`, `run_tip_local_net_S1_umax.py`, discontinuity/SDF runners | Closed as negative unless the proposed run targets the active-driver/process-zone gate. |
| Monotonic controls | `run_fem_mesh_monotonic_fatigue_off.py`, `run_fem_mesh_monotonic_fatigue_on.py` | Supporting semantics checks; compare by load value. |
| Figures/posthoc | `plot_*.py`, `analyze_*.py`, `posthoc_*.py` | Mac-safe when they do not enter training; prefer these for cheaper diagnostics. |

## Skill Maintenance Rules

1. Keep project skills in `docs/skills/` so they sync across machines.
2. When a skill invokes code, list the exact script family and producer machine.
3. Do not add a new execution skill without a no-training-on-Mac statement if it can run PIDL training.
4. New or next-touched work uses `Storyline -> Experiment -> Run -> Evidence`;
   update legacy registries only when needed for compatibility.
5. Obtain an independent pre-result review for claim-changing architecture,
   diagnostic, threshold, or criterion changes. Bind it to the exact protocol
   and implementation; record adoption/tests in `experiment.md` or the optional
   v2 attempt ledger.
