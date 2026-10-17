# Attempt S09-E009-A002-core-implementation

- Status: `tested`
- Created: 2026-10-17T20:46:47+01:00
- Closed: None
- Type: `implementation`
- Human decision required: False

## Motivation
Implement the design-reviewed four-arm numerical contract without exposing a producer launch path.

## Trigger
S09-E009 protocol v3 received DESIGN_READY_PASS.

## Current Claim Before Attempt
The protocol is design-ready, but no S09-E009 code candidate has yet passed exact-commit review.

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
- Exact implementation of all four directions; deterministic scorecard edge cases; E008 replay preservation; all selected no-training tests pass.

## Failure Criteria
- Protocol mismatch; hidden optimiser step; shared arm state; double clipping; incomplete undefined/NA behavior.

## Code Changes
- add: `source/s09_e009_four_arm.py` - Implement four-arm directions, atomic/grouped losses, arm isolation, diagnostics and scorecard primitives
- add: `tests/test_s09_e009_four_arm.py` - Exercise gradient geometry, clipping, arm isolation and scorecard boundary cases
- modify: `tests/test_s09_stage0a_p1_runner.py` - Verify atomic E009 objectives against the synthetic E008-compatible runtime

## Input Assets
- `docs/research/S09/S09-E009/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E009/design_review.md` (design gate; exists)

## Output Assets
- `docs/research/S09/S09-E009/core_code_review.md` (exact-commit review; missing)

## Tests
- pass: selected synthetic/no-training suite - 43 passed in 1.28s; no optimiser step or training.
- pass: syntax and whitespace checks - Both checks completed with exit code 0.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
