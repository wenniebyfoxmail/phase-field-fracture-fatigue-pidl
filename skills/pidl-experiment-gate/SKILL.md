---
name: pidl-experiment-gate
description: Internal PIDL/FEM physics module for a road-fracture claim already routed through road-fracture-experiment-gate. Load only when FEM/PIDL, Hard-5, teacher, field/state, or synthetic-surrogate semantics materially affect the claim; it is not a second experiment gate.
---

# PIDL/FEM Physics Module

`road-fracture-experiment-gate` owns claim class, experiment contract,
acceptance criterion, record, and conclusion. Its physics-and-surrogates
reference loads this module only when detailed FEM/PIDL, Hard-5, or field/state
semantics are material. This module adds those semantics; it does not open a
second claim route, experiment contract, or review.

When explicitly invoked, preserve those Road-owned fields and add only the
physics-specific information needed for the current claim. Do not load this
module for observation, measurement, inverse, or real-road forecasting work
without a physics/surrogate claim.

Follow the core's **只跑固定基准，通过即交付**. Detailed physics references
describe interpretation and the declared scientific benchmark; they do not
require rerunning every historical validator or adding independent review.

Also use the shared solution-oriented outcome rule. A failed Hard-5, teacher,
surrogate, or mechanism gate remains negative for that bounded claim, but it
must be decomposed into reference qualification, representational ceiling,
optimisation, state alignment, active-driver support, damage/history coupling,
and transfer. Preserve any component that passed, identify the binding mechanism
and use the core's first-principles route design for a physics-grounded repair
or coherent redesign. Match field/state/evolution coverage to that hypothesis;
do not mandate another single-state micro-test when its limitations are known.
Do not stop at
“mechanics misaligned” or “capacity insufficient” when an executable diagnostic
or repair can distinguish the alternatives.

Before setting a performance margin, compare it with FEM/reference uncertainty,
discretisation variation, repeatability and an oracle or replay ceiling. If the
required improvement consumes nearly the whole attainable gap, revise the
claim or design before viewing the holdout rather than manufacturing a sequence
of predictable FAILs.

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
