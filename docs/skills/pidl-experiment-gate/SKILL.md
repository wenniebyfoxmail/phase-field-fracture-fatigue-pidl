---
name: pidl-experiment-gate
description: Apply the project experiment gate specifically to PIDL, FEM, teacher qualification, field-mechanism comparison, residual correction, GNO/PINO, and synthetic surrogate work. Use this compatibility entry for physics-specific state semantics or Hard-5 validation; use road-fracture-experiment-gate directly for observation, measurement, inverse, or real-road forecasting work without a physics/surrogate claim.
---

# PIDL/FEM Experiment Gate

This is the physics-route compatibility entry, not the project-wide research
gate.

First read the shared core:

- [`../road-fracture-experiment-gate/SKILL.md`](../road-fracture-experiment-gate/SKILL.md)
- [`../road-fracture-experiment-gate/references/physics_surrogate.md`](../road-fracture-experiment-gate/references/physics_surrogate.md)

Use the shared claim classes, Occam acceptance rule, readiness states, outcome
map, and output template. Add only the physics-specific fields needed for the
current claim.

## Physics-Specific Boundaries

- Tooling success is not numerical, behavioural, teacher, or mechanism validity.
- Numerical convergence is not physical validation.
- Similar event timing is not active-driver/process-zone closure.
- A residual corrector or neural operator imitates its declared producer; it
  does not become physical truth.
- FEM is a synthetic reference only for qualified outputs and regimes and is
  never automatic real-road ground truth.
- Added seeds, nodes, windows, or checkpoints from one physical trajectory do
  not create an independent physical axis.

## Hard-5 And Field Comparison

For Hard-5 or FEM-centred state/field comparison, read
[`references/hard5_field_validation.md`](references/hard5_field_validation.md).
It owns the detailed state/event alignment, process-zone metrics, figure roles,
and legacy-validator boundary. Do not load it for unrelated surrogate,
observation, inverse, or road-forecast tasks.

## Legacy Helpers

`scripts/pidl_attempt_ledger.py` remains available for existing decision-critical
PIDL/FEM sub-attempt ledgers. `experiment.md` remains authoritative. Do not start
a new generic road-fracture ledger under a PIDL-named path.

`scripts/pidl_result_package_check.py` is scoped to its historical July
hard-recovery package. Its PASS is not a current benchmark or scientific gate.
