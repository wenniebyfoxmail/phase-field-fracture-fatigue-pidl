# S09-E010 runner integration status

## Current state

`RUNNER_INTEGRATION_CANDIDATE__AWAITING_FOCUSED_REREVIEW`

The reviewed E010 support/amplitude core is now connected to the frozen E008
runtime, three isolated arm states, the 500-update schedule and a fail-closed
evidence contract.  The integration remains CPU-only and no-training.  It has
no optimizer-step or producer-launch function.

## Integrated contract

- Arms are ordered as exact `A25`, `B25`, then `B0`.
- One base model is constructed with seed `20261016`; complete parameters and
  buffers are copied into three disjoint model objects.
- Each arm owns a separate empty AdamW instance with the frozen E009
  hyperparameters.
- Each arm receives exactly 500 scheduled updates and the total cap is 1,500.
- Evaluations are fixed at updates `0, 16, 64, 128, 256, 496, 500`.
- Each complete direction carries exactly one global L2 clip at norm 1.0.
- The support mask and target amplitude are training targets only.  The config
  admits no target-derived inference field.
- The future evidence set requires per-arm logs, final checkpoints and terminal
  receipts, plus shared identity, exact-A25 replay, all-cycle score and decision
  artifacts.

## Verification

The selected E010 and inherited E009 suite now reports `76 passed`.  The actual
frozen 16-cycle, 86,756-node packet produced
`NO_TRAINING_INTEGRATION_PASS`.  All 48 arm-cycle runner directions match their
reviewed core implementations with maximum absolute difference zero.  All
three model hashes remain unchanged, all optimizer states remain empty, and no
optimizer step was called.

Round-1 independent review accepted the arm, budget, isolation, loss-routing,
leakage, replay and no-step boundaries. It found one receipt-validator defect:
zero completed updates could be paired with `stop_update=500`. The validator
now requires the stop to be the completed update or its immediate successor,
and explicit `0 -> 0`, `0 -> 1`, `63 -> 64`, `500 -> 500` and rejected
`0 -> 500` cases are covered. The no-training frozen-packet receipt was
regenerated after this repair with the same 48/48 exact matches.

The no-training receipt records the exact packet identity, config identity,
schedule hash, isolated initial-state hashes, per-arm first-cycle direction
hashes and all 48 runner-versus-core hashes.

## Boundary and next gate

This is an integration candidate, not Run Ready and not a scientific result.
The narrow validator repair must receive focused exact-commit rereview. Only
after that review may producer-loop/config-resolution/evaluator-writer code and
an exact run card be prepared. This stage does not launch training, access a
new holdout or alter the frozen E009 result.

