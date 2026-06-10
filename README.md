# Phase-Field Fracture Fatigue PIDL

This repository contains the shared code, diagnostics, and research workflow
docs for the phase-field fracture fatigue PIDL project.  It is the GitHub-synced
child repository inside the larger local workspace:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/
```

The parent folder is local scratch space.  Treat this repository as the source
of truth for code and shared documentation.

## Repository Map

| Path | Purpose |
|---|---|
| `source/` | Core PIDL implementation: energy, fatigue history, neural networks, model construction, optimisation, field supervision, scaling, and plotting helpers. |
| `SENS_tensile/` | SENT benchmark runners, diagnostics, post-processing scripts, and validation utilities. |
| `docs/` | Research frontier, protocols, handovers, result summaries, workflow rules, and selected canonical figures/tables. |
| `docs/handovers/` | Cross-machine task inbox/outbox files for Windows-PIDL, Windows-FEM, and CSD3. |
| `docs/research_frontier.md` | One-screen current research state and next discriminator. Read this first for research context. |
| `docs/git_workflow.md` | Mac/Windows/Taobo/CSD3 role split and Git workflow. |
| `docs/artifact_policy.md` | What belongs in Git versus local/remote artifact storage. |
| `docs/artifact_index.md` | Human-maintained index of important local, Taobo, Windows, and packaged artifacts. |

## Machine Roles

Mac-PIDL is the development machine.  Edit code, runners, and shared docs here,
then commit when the change is meant to be shared.

Windows-PIDL, Windows-FEM, Taobo GPU, and CSD3 are producer machines.  They run
training, FEM references, smoke checks that enter training loops, and production
sweeps.

Do not run PIDL training loops on Mac, including one-cycle training smoke tests.
Mac should only run lightweight import, syntax, or unit sanity checks.

## Common Entry Points

Core code:

- `source/model_train.py`
- `source/fit.py`
- `source/fatigue_history.py`
- `source/compute_energy.py`
- `source/network.py`
- `source/scaling.py`

Frequently used runners and diagnostics:

- `SENS_tensile/run_baseline_umax.py`
- `SENS_tensile/run_fem_mesh_umax.py`
- `SENS_tensile/run_fem_mesh_history_driver_umax.py`
- `SENS_tensile/run_fem_mesh_state_timing_umax.py`
- `SENS_tensile/run_fem_mesh_staged_alpha_umax.py`
- `SENS_tensile/run_m2s_next_stage_feasibility.py`
- `SENS_tensile/compare_fem_pidl_cyclewise_mechanism.py`
- `SENS_tensile/compute_field_level_score_v0.py`

## Lightweight Local Checks

Use checks that do not enter the training loop, for example:

```bash
PYTHON=/Users/wenxiaofang/miniconda3/bin/python3
$PYTHON -m py_compile source/*.py SENS_tensile/*.py
$PYTHON - <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("pidl_scaling", "source/scaling.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print("import sanity ok:", module.PCCScaling.__name__)
PY
```

Run training smoke, baselines, and sweeps only on a producer machine after
following the relevant handover/protocol docs.

## Artifact Rule

Git should contain source, runners, workflow docs, handover docs, concise result
summaries, and small canonical tables/figures needed for review.

Git should not contain raw run folders, checkpoints, TensorBoard logs, large
`.npz`/`.mat`/`.npy` field dumps, copied Taobo project trees, OneDrive packages,
or local result bundles.  Keep those in local or remote artifact storage and
record their paths in `docs/artifact_index.md` or the relevant handover file.

See `docs/artifact_policy.md` for the full rule.

## Collaboration Protocol

Before changing shared code or workflow rules, read:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/git_workflow.md`
- `docs/workflow_rules.md`

For current research direction, read `docs/research_frontier.md` first.  For
cross-machine tasks, use the inbox/outbox files under `docs/handovers/`.
