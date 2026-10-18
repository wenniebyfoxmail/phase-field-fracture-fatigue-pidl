# S09-E010 runner/config/evidence integration review request

Please review the attached exact-commit S09-E010 no-training integration.

First verify the package identity, manifest hashes, byte counts, duplicate
members and unlisted members.  Then determine whether the integration is ready
to serve as the reviewed boundary for later producer-loop implementation.

Review these invariants rather than the already accepted core formulas:

1. the exact `A25`, `B25`, `B0` arm order, 500 updates per arm, 1,500 total
   update cap and seven fixed evaluation points;
2. one seeded base model followed by complete parameter/buffer copies, disjoint
   arm model objects and three independent empty AdamW states;
3. exactly one complete-direction global clip and no extra optimization path;
4. all 48 actual frozen-packet arm-cycle runner directions match the reviewed
   core direction exactly, including exact E009 `A25` replay;
5. support masks and target amplitudes are training-only quantities and cannot
   enter inference, case selection, checkpoint selection or evaluation
   filtering;
6. configuration, termination receipts, shared identity and exact-replay
   prerequisites fail closed;
7. this package constructs optimizers but never calls `step`, exposes no
   producer launch, and makes no scientific claim.

Local evidence:

- selected E010 plus inherited E009 suite: `72 passed`;
- actual frozen packet: `NO_TRAINING_INTEGRATION_PASS`;
- 48/48 runner/core direction comparisons have maximum absolute difference
  zero;
- three initial state hashes are identical while model/buffer objects and
  optimizers are disjoint;
- model hashes are unchanged, optimizer states are empty, optimizer steps are
  zero;
- Ruff, py_compile and whitespace checks pass.

Return `RUNNER_INTEGRATION_READY_PASS` if the exact commit safely supports only
later producer-loop/config-resolution/evaluator-writer implementation and
continued no-training verification.  State the exact commit and what you
independently checked.  A pass does not authorise training, holdout access or a
producer launch.

Otherwise return `REVISE_AND_REREVIEW` with the blocking file/function, a
minimal reproduction, and expected versus observed behaviour.  Keep optional
improvements separate from blockers.
