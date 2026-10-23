# Physics, FEM/PIDL, And Surrogate Adapter

Read this reference for FEM/PIDL numerical or mechanism studies, teacher
qualification, residual correction, neural operators, GNO/PINO, and synthetic
transition surrogates.

## Declare The Reference Role

Choose one role and do not silently promote it:

- numerical candidate;
- mechanism hypothesis or diagnostic;
- qualified synthetic producer;
- teacher for a declared state/output subset;
- surrogate target;
- prior or feature generator for a reality-facing model.

Numerical convergence does not establish physical behaviour. Matching event
timing does not establish field mechanism. A residual corrector or surrogate
imitates its declared producer, not reality. FEM becomes a usable teacher only
for outputs and regimes that passed the relevant numerical, behavioural,
provenance, and state-capability gates.

## State And Trajectory Identity

When field comparison matters, identify physical family, geometry/mesh,
material and loading schedule, initialization, cycle/time, substep/phase,
pre/post update timing, support/reduction, channel, solver/code identity, and
comparison class. Unknown identity remains unknown.

Keep same-state, common pre-event, own-first-event, and own-terminal comparisons
separate. Do not select predictive inputs using future event information.

## Smallest Primary Criterion

- numerical qualification: the declared accepted-state residual/bounds or
  discretisation criterion;
- mechanism claim: one mechanism-local observable or field criterion on an
  independent physical axis;
- teacher qualification: capability for the exact supervised outputs and
  regime, not general solver success;
- surrogate/operator: held-out complete-trajectory error or rollout stability
  against the qualified producer;
- residual correction: incremental held-out process-zone/transition value over
  the uncorrected model and a direct data-only comparator.

Whole-domain error, training fit, extra seeds, nodes, windows, or checkpoints
from one physical trajectory do not establish independent transfer.

## Routing

For Hard-5 or detailed FEM/PIDL field validation, also use
`pidl-experiment-gate`; its dedicated reference owns legacy event/state and
metric guidance. Producer selection and remote safety remain in project
`AGENTS.md`, not in this scientific adapter.
