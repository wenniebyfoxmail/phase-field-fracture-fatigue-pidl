# Attempt f1b_exact_pi_solver_invariance_20260729_v2

- Status: `tested`
- Created: 2026-07-29T16:49:08+01:00
- Closed: None
- Type: `framework-validation`
- Human decision required: True

## Motivation
Preserve the dimensionless nonlinear FEM problem and predeclare solver-mesh fresh-solve gates before F1b launch.

## Trigger
Independent review rejected replay-level field identity and unscaled dimensional solver tolerances.

## Current Claim Before Attempt
F1a is scaling-I/O only; F1b remains blocked and untested.

## GPT Pro Advice
- Required: False
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Scale active dimensional residual tolerances and tangent regularization, replace the dimensionally mixed staggered sum, and freeze solver-mesh fresh-solve gates before launch.

## Rejected Or Modified Advice
Rejected floating-point field identity and retaining unscaled absolute residual tolerances; no old run existed to quarantine.

## Decision Rationale
Exact physical Pi groups are insufficient if absolute numerical controls change the normalized nonlinear problem.

## Success Criteria
- Fresh immutable Windows-FEM solve passes numerical-contract checks
- same-cycle c20/c40/c60 fields
- first-hit and confirmed own-event fields
- active support
- and event timing within one cycle.

## Failure Criteria
- Any completed valid solve missing a predeclared field
- support
- numerical-contract
- or event gate fails; unavailable producer remains blocked.

## Code Changes
- modify: `producer_handoffs/f1b_exact_pi_20260729` - Add v2 tolerance audit, scaled Newton controls, dimensionless staggered gate, source hashes, launcher and lock
- modify: `SENS_tensile/analyze_f1b_exact_pi_solver.py` - Add c20-c60 same-cycle and dynamic own-event field-support gates

## Input Assets
- `producer_handoffs/f1b_exact_pi_20260729/INPUT_LOCK.json` (v2 immutable dimensional and numerical input; exists)

## Output Assets
- `docs/f1b_exact_pi_solver_invariance_20260729/decision.md` (blocked or terminal decision; exists)

## Tests
- pass: focused-static-tests - 23 focused tests passed before adding one support-metric identity test; the dedicated F1b file then passed 9 tests.
- pass: full-regression - 176 passed, 1 skipped; one pre-existing Transformer nested-tensor warning.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
