# Attempt S09-E009-A003-runner-integration

- Status: `tested`
- Created: 2026-10-17T21:53:43+01:00
- Closed: None
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
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Not recorded.

## Rejected Or Modified Advice
Not recorded.

## Decision Rationale
Not recorded.

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

## Input Assets
- `docs/research/S09/S09-E009/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E009/core_code_review.md` (approved core review; exists)

## Output Assets
- `docs/research/S09/S09-E009/runner_integration_config_20261017.json` (no-training integration config; exists)
- `docs/research/S09/S09-E009/runner_integration_review_request_20261017.md` (exact-commit review request; exists)

## Tests
- pass: selected no-training integration suite - 59 passed in 1.36s; AdamW.step sentinel was not called; all four runner directions matched the reviewed core exactly.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
