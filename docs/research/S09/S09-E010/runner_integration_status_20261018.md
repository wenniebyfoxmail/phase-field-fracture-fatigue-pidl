# S09-E010 runner integration status

## Current state

`RUNNER_INTEGRATION_READY_PASS`

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

Focused round-2 review independently exercised 13 scalar-validator cases and
returned `RUNNER_INTEGRATION_READY_PASS`, bound to exact commit
`51835e1626e536b2079adb4e1b878da7256a46c0`. The original `0 -> 500`
counterexample is rejected, the intended boundary cases remain valid, and no
new blocker was found in the narrow diff.

The no-training receipt records the exact packet identity, config identity,
schedule hash, isolated initial-state hashes, per-arm first-cycle direction
hashes and all 48 runner-versus-core hashes.

## Boundary and next gate

The no-training runner/config/evidence layer is now independently reviewed.
The next permitted scope is producer-loop/config-resolution/evaluator-writer
implementation, continued no-training verification and preparation of a later
exact run card. This is not Run Ready or a scientific result; it does not
authorise training, an optimizer step, holdout access or producer launch, and
it does not alter the frozen E009 result.

