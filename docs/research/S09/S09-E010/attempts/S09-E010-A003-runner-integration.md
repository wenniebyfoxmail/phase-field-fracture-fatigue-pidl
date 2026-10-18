# Attempt S09-E010-A003-runner-integration

- Status: `tested`
- Created: 2026-10-18T14:07:34+01:00
- Closed: None
- Type: `runner-integration`
- Human decision required: False

## Motivation
Connect the reviewed E010 numerical core to the frozen runtime, schedule, isolated arm states and fail-closed evidence contract without entering the optimizer loop.

## Trigger
S09-E010-A002 received CORE_CODE_READY_PASS at exact commit 45d8ec5f158d6fbdc608437f02da4fa43501157f.

## Current Claim Before Attempt
The numerical core is Code Ready, but no reviewed E010 runner/config/evidence integration exists.

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
- All 48 frozen arm-cycle directions match the reviewed core exactly; the three arms share initial state but have independent model/optimizer objects; schedule
- evidence and invalidity contracts fail closed; no step occurs.

## Failure Criteria
- Any core-direction mismatch
- state sharing
- schedule/budget drift
- target-derived inference path
- incomplete receipt branch
- mutation or optimizer step.

## Code Changes
- add: `source/s09_e010_runner_integration.py` - Add three-arm config validation, isolated state construction, exact reviewed-core direction checks, schedule and receipt validators
- add: `tests/test_s09_e010_runner_integration.py` - Add no-step, 48 arm-cycle equivalence, leakage, budget, isolation and receipt regressions
- add: `scripts/check_s09_e010_runner_integration.py` - Add explicit CPU-only no-training integration receipt entry point
- add: `docs/research/S09/S09-E010/runner_integration_config_20261018.json` - Freeze three arms, 1500-update cap, evidence set and producer placeholders
- add: `docs/research/S09/S09-E010/runner_integration_no_training_20261018.json` - Record actual frozen-packet 48-direction no-step integration evidence

## Input Assets
- `docs/research/S09/S09-E010/experiment.md` (frozen protocol; exists)
- `source/s09_e010_support_amplitude.py` (reviewed numerical core; exists)

## Output Assets
- `source/s09_e010_runner_integration.py` (no-training integration contract; exists)
- `docs/research/S09/S09-E010/runner_integration_config_20261018.json` (frozen integration config; exists)
- `docs/research/S09/S09-E010/runner_integration_no_training_20261018.json` (frozen packet no-training receipt; exists)

## Tests
- pass: selected E010 integration and inherited regressions - 52 passed; no-step interception, three-arm isolation, exact direction equivalence, leakage/budget fail-closed branches and inherited E009 integration remain valid.
- pass: actual frozen-packet no-training integration - NO_TRAINING_INTEGRATION_PASS; all 48 arm-cycle runner directions match reviewed core bitwise, model hashes are unchanged, optimizer states remain empty and step count is zero.
- pass: static checks - New integration module, test and entry script pass lint, syntax and whitespace checks.
- pass: complete selected E010 and E009 regression suite - 72 passed; complete reviewed core plus both integration layers remain consistent.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
