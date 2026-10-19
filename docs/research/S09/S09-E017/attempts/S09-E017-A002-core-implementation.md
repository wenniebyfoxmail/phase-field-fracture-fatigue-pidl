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
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/docs/research/S09/S09-E017/core_review_round1_20261019.md`
- Advice sha256: `46a273cd1d07582ed348a127e6908276cee56e4166d95e0a296651348e6b0f03`

E017_CORE_CODE_REVISE bound to 0fa5ca33: repair tie arithmetic, A2/S6/R2/P4 evidence validation, strict-zero factorisation postconditions and derived nonfinite checks; design remains closed.

## Adopted Decision
Adopt all four minimal implementation repairs and add the supplied counterexamples as regressions.

## Rejected Or Modified Advice
No blocking advice rejected. The reviewer NumPy counterexample using the minimum subnormal and weights [2,1] becomes a strict-zero underflow in native Torch; the native regression therefore uses the minimum subnormal for lost-positive detection and twice that value for non-normalised positive-amplitude shape detection.

## Decision Rationale
Each finding demonstrates an implementation path that could change a graded verdict or return invalid arithmetic while leaving the approved scientific design unchanged.

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
- modify: `source/s09_e017_factorised_pilot.py` - Close B1-B4 with exact comparator, schema/count checks, E016 factorisation postconditions and finite derived-arithmetic guards
- modify: `tests/test_s09_e017_factorised_pilot.py` - Add complete tie profile, malformed evidence, subnormal factorisation and overflow regressions
- add: `docs/research/S09/S09-E017/core_review_round1_20261019.md` - Persist exact-commit review evidence and accepted repair scope

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
- pass: revised factorised core and inherited E016 regressions - 49 passed in 0.58s; all four review counterexample families now fail closed or classify under the frozen rule.
- pass: revised static checks - Syntax, Ruff and whitespace checks passed after B1-B4 repairs.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
