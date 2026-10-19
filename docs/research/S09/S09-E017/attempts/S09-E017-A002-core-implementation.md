# Attempt S09-E017-A002-core-implementation

- Status: `tested`
- Created: 2026-10-19T13:26:23+01:00
- Closed: None
- Type: `core-implementation`
- Human decision required: False

## Motivation
Implement the design-reviewed factorised amplitude-times-shape arithmetic, PCGrad contract and graded classifier without exposing a model, optimiser or training path.

## Trigger
Exact commit 07b66e1df22d6e44d01780003e0b539b0f5886fa received E017_DESIGN_READY_PASS.

## Current Claim Before Attempt
E017 is design-ready, but no independently reviewed numerical core exists.

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/docs/research/S09/S09-E017/design_review_round2_20261019.md`
- Advice sha256: `b83a7341f40af74fbd6adb9f805d53730d682b003882f71fa181b0000b516d44`

E017_DESIGN_READY_PASS bound to commit 07b66e1d after closing all-tie mixed-tradeoff and zero-amplitude decision counterexamples.

## Adopted Decision
Implement and review only the reusable float64 numerical core before any neural-operator integration.

## Rejected Or Modified Advice
No design-review finding was rejected; implementation-specific choices are exposed in the review request.

## Decision Rationale
This is the smallest layer that can verify the factorised decoder, multi-objective arithmetic and graded classifier while keeping execution and scientific claims closed.

## Success Criteria
- The exact pure core matches the reviewed design
- deterministic synthetic and inherited E016 tests pass
- and ChatGPT Pro returns E017_CORE_CODE_READY_PASS.

## Failure Criteria
- Any constraint
- zero-event
- loss
- gradient-order
- beta
- classifier
- diagnostic or scope mismatch remains.

## Code Changes
- add: `source/s09_e017_factorised_pilot.py` - Add factorised decoder, objectives, PCGrad diagnostics and profile classifier
- add: `tests/test_s09_e017_factorised_pilot.py` - Add deterministic constraint, objective, gradient and decision regressions
- add: `docs/research/S09/S09-E017/core_implementation_status_20261019.md` - Record purpose, verification, limitations and open review points
- add: `docs/research/S09/S09-E017/core_review_request_20261019.md` - Freeze exact core-review questions and authority boundary

## Input Assets
- `docs/research/S09/S09-E017/first_principles_pilot_card_draft_20261019.md` (design-approved protocol; exists)
- `docs/research/S09/S09-E017/design_review_round2_20261019.md` (independent design review; exists)

## Output Assets
- `source/s09_e017_factorised_pilot.py` (pure numerical core; exists)
- `tests/test_s09_e017_factorised_pilot.py` (deterministic regressions; exists)
- `docs/research/S09/S09-E017/core_implementation_status_20261019.md` (scope and verification record; exists)

## Tests
- pass: factorised core and inherited E016 regressions - 36 passed in 0.57s; seed sensitivity, decoder bounds, round trip, zero semantics, objectives, PCGrad geometry and classifier edges pass.
- pass: static checks - Syntax, lint and whitespace checks passed.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
