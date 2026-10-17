# Attempt S09-E009-A003-runner-integration

- Status: `accepted`
- Created: 2026-10-17T21:53:43+01:00
- Closed: 2026-10-17T22:51:07+01:00
- Type: `implementation`
- Human decision required: False

## Motivation
Bind the reviewed four-arm numerical core to the verified E008 runtime, fixed budget/schedule, isolated optimiser states and future evidence contract without executing training.

## Trigger
Exact core commit 8b6a2e49 received CORE_CODE_READY_PASS.

## Current Claim Before Attempt
The four-arm core is reviewed, but runner/config/evidence integration has not yet passed exact-commit review.

## GPT Pro Advice
- Required: True
- Advice path: `runner_integration_review_round4_20261017.md`
- Advice sha256: `e5ddbef33614280074a8475fc7f9f38fc25d99fa11997cbe224a0f9151907722`

Round 4 returned RUNNER_INTEGRATION_READY_PASS after reproducing 76 selected tests and 10 snapshot checks; the single-byte trusted-reference binding is closed.

## Adopted Decision
Accept exact commit efeffbfae4395f95228c56e3f530e323f1ab8f6a as the reviewed no-training runner integration.

## Rejected Or Modified Advice
None. The PASS boundary is retained: producer loop, resolver and complete evaluator/evidence writer require separate implementation and review.

## Decision Rationale
The reviewed runner direction, arm isolation, frozen configuration, terminal evidence contract and trusted-reference byte identity all pass; Pro reproduced 76 selected tests plus 10 narrow checks with zero optimizer updates.

## Success Criteria
- Four byte-identical object-independent arms with empty AdamW state
- exact frozen schedule and evidence manifest
- runner direction equals reviewed core
- no optimiser step or producer path
- exact-commit ChatGPT Pro pass

## Failure Criteria
- Shared state or optimiser mismatch
- direction drift or double clipping
- budget/evaluation drift
- hidden optimiser step
- under-specified termination evidence

## Code Changes
- add: `source/s09_e009_runner_integration.py` - Bind verified runtime, four isolated arms, direction preflight and receipt
- add: `scripts/check_s09_e009_runner_integration.py` - Expose a CPU-only no-training receipt CLI
- add: `tests/test_s09_e009_runner_integration.py` - Verify schedule isolation core equality fail-closed config and no optimizer step
- add: `docs/research/S09/S09-E009/runner_integration_config_20261017.json` - Freeze integration budget arms unresolved source fields and evidence manifest
- modify: `source/s09_e009_runner_integration.py` - Bind production to reviewed base/protocol hashes; add narrow size-only synthetic adapter and conditional terminal receipt validation
- modify: `docs/research/S09/S09-E009/runner_integration_config_20261017.json` - Freeze complete config fields and terminal-state-dependent evidence requirements
- modify: `tests/test_s09_e009_runner_integration.py` - Add config drift counterexamples, terminal branches, buffer isolation and all 64 arm-cycle comparisons
- modify: `source/s09_e009_runner_integration.py` - Verify the synthetic trusted reference hash and link terminal validity, step, stop, evaluation and checkpoint identity
- modify: `tests/test_s09_e009_runner_integration.py` - Cover the Round-2 trusted-reference and five terminal-receipt counterexamples
- modify: `source/s09_e009_runner_integration.py` - Hash and parse the trusted reference from one immutable byte snapshot
- modify: `tests/test_s09_e009_runner_integration.py` - Cover path replacement after trusted-reference snapshot capture

## Input Assets
- `docs/research/S09/S09-E009/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E009/core_code_review.md` (approved core review; exists)

## Output Assets
- `docs/research/S09/S09-E009/runner_integration_config_20261017.json` (no-training integration config; exists)
- `docs/research/S09/S09-E009/runner_integration_review_request_20261017.md` (exact-commit review request; exists)

## Tests
- pass: selected no-training integration suite - 59 passed in 1.36s; AdamW.step sentinel was not called; all four runner directions matched the reviewed core exactly.
- pass: Round-1 repaired no-training integration suite - 69 passed in 2.15s; 64 arm-cycle direction comparisons, base-trust and frozen-field counterexamples, three terminal-state branches, and zero AdamW.step calls.
- pass: Round-2 residual repaired no-training suite - 75 passed in 2.41s; trusted-reference mutation and five terminal-receipt contradictions now fail closed or preserve a legitimate late checkpoint.
- pass: Round-3 byte-snapshot repair no-training suite - 76 passed in 1.91s; trusted reference is read once, hashed and parsed from the same bytes; no optimizer step or producer route.

## Result Interpretation
The no-training runner/config/evidence integration is code-ready. This is an engineering gate only; no producer or training execution occurred.

## Claim After Attempt
Exact commit efeffbfae4395f95228c56e3f530e323f1ab8f6a has RUNNER_INTEGRATION_READY_PASS for no-training integration.

## Next Action
Implement the producer loop, environment resolver and complete evaluator/evidence writer without executing optimizer steps, then submit that exact layer for independent review.
