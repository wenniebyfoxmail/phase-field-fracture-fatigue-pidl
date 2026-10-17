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
- Advice path: `core_code_review_round2_20261017.md`
- Advice sha256: ``

Round 2 returned REVISE_AND_REREVIEW: F3 closed; F1 still needed replay raw-norm/diagnostic checks and F2 still needed native-float ratio outputs.

## Adopted Decision
Adopt both residual Round-2 fixes and submit one more narrow exact-commit rereview.

## Rejected Or Modified Advice
No Round-2 finding is rejected; F3 remains closed.

## Decision Rationale
Both are deterministic interface boundaries; neither changes the approved mathematics, budget, controls or thresholds.

## Success Criteria
- Exact implementation of all four directions; deterministic scorecard edge cases; E008 replay preservation; all selected no-training tests pass.

## Failure Criteria
- Protocol mismatch; hidden optimiser step; shared arm state; double clipping; incomplete undefined/NA behavior.

## Code Changes
- add: `source/s09_e009_four_arm.py` - Implement four-arm directions, atomic/grouped losses, arm isolation, diagnostics and scorecard primitives
- add: `tests/test_s09_e009_four_arm.py` - Exercise gradient geometry, clipping, arm isolation and scorecard boundary cases
- modify: `tests/test_s09_stage0a_p1_runner.py` - Verify atomic E009 objectives against the synthetic E008-compatible runtime
- add: `53b9bf9ab12c6fa3bc333b9287483735414ec3ba` - Freeze the exact core implementation candidate submitted for independent review
- modify: `source/s09_e009_four_arm.py` - Fail closed on nonfinite derived quantities, emit strict JSON scalars, and separate exact-zero from near-zero projection labels
- modify: `tests/test_s09_e009_four_arm.py` - Add Round-1 overflow, NumPy JSON, and projection-label counterexamples
- modify: `source/s09_e009_four_arm.py` - Fail closed before the inherited replay merger when its ordinary norm would overflow, and validate finite replay diagnostics
- modify: `source/s09_e009_four_arm.py` - Normalise accepted ratio inputs and defined outputs to native Python floats for strict JSON

## Input Assets
- `docs/research/S09/S09-E009/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E009/design_review.md` (design gate; exists)

## Output Assets
- `docs/research/S09/S09-E009/core_code_review.md` (exact-commit review; missing)

## Tests
- pass: selected synthetic/no-training suite - 43 passed in 1.28s; no optimiser step or training.
- pass: syntax and whitespace checks - Both checks completed with exit code 0.
- pass: Round-1 repaired synthetic/no-training suite - 48 passed in 1.18s; reviewer counterexamples are covered; no optimiser step or training.
- pass: Round-2 replay-boundary repair suite - 49 passed in 1.28s; the exact two-parameter replay norm-overflow counterexample now fails closed before the frozen merger.
- pass: Round-2 residual repair suite - 51 passed in 1.15s; replay single-object norm overflow and NumPy float32/float64 strict JSON ratios are covered.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
