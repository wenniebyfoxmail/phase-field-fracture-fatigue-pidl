# S09-E011 focused producer rereview v3

Review only the residual R2/R3/R5 findings from the ChatGPT Pro review of
`66156b374d976d12e5632f59e99404c5c7365330`. The numerical objective, pair
set and order, `gamma_R=4096`, `beta=0.25`, two-arm budget, scientific
criteria, A001 history and A002 zero-step result are unchanged.

## Required checks

1. A complete update-500 evaluation that passes the inherited E010 validator
   must also pass after canonical JSONL write, disk read, exact named-map
   membership checks and frozen-order restoration. Unknown or missing atomic,
   grouped, projection or hard-constraint keys must still fail.
2. An evaluation is counted as present only after its JSONL row is written and
   flushed. A diagnostic write failure must preserve the last durable update.
3. A partial-checkpoint cleanup error must be folded into the arm failure
   receipt and must not escape before accumulated step/log/evaluation counts
   are carried to the run-level failure receipt.
4. A wall deadline crossed during objective or direction computation must be
   checked again before `optimizer.step()`, so no avoidable post-deadline
   mutation begins.
5. Completion receipt integer fields must be type-strict. The final field
   artifacts must be replayed from the validated update-500 checkpoints and
   their reconstructed amplitudes must match the validated evaluation records.

## Local no-training evidence

- E011 focused tests: 18 passed.
- E009/E010/E011 regression selection: 135 passed.
- The seven archived E010 update records at 0/16/64/128/256/496/500 pass the
  actual canonical-disk decode and inherited validator path.
- `py_compile` and `git diff --check` pass.
- No producer training or holdout access occurred while preparing this repair.

The first line of the review must be `E011_PRODUCER_READY_PASS` or
`REVISE_AND_REREVIEW`. A PASS binds only the exact reviewed commit and permits
the already approved one-time two-arm run; it is not a scientific result.
