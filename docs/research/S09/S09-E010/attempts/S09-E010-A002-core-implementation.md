# Attempt S09-E010-A002-core-implementation

- Status: `accepted`
- Created: 2026-10-18T13:18:44+01:00
- Closed: 2026-10-18T13:49:53+01:00
- Type: `core-implementation`
- Human decision required: False

## Motivation
Implement the design-reviewed support/amplitude losses, three-arm gradient rule and cumulative classifier without exposing a training path.

## Trigger
S09-E010 protocol v2 DESIGN_READY_PASS.

## Current Claim Before Attempt
The protocol is design-ready, but no code candidate or no-step frozen-packet evidence exists.

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/docs/research/S09/S09-E010/design_review.md`
- Advice sha256: `6bac9b8b1bae9fb6394f11c176e42a21ff2fdc3ea8c89ae68a683344660792ab`

DESIGN_READY_PASS fixed the per-cycle support/amplitude formulas, zero-gradient logging, same-state B25/B0 decomposition, integer AUC boundary and cumulative classification.

## Adopted Decision
Implement only the reusable numerical core and read-only no-step preflight before any runner or producer path.

## Rejected Or Modified Advice
No design-review recommendation was rejected.

## Decision Rationale
This is the smallest reviewable layer and keeps Code Ready, Run Ready and scientific evidence separate.

## Success Criteria
- Frozen formulas and hierarchy are implemented; deterministic synthetic and frozen-packet no-step checks pass; exact commit is ready for independent review.

## Failure Criteria
- Loss pooling
- leakage
- gradient geometry
- replay
- cumulative classifier
- finite handling
- clip count or no-step boundary differs from protocol.

## Code Changes
- add: `source/s09_e010_support_amplitude.py` - Implement per-cycle losses, projected B directions, exact A25 control and cumulative classifier
- add: `tests/test_s09_e010_support_amplitude.py` - Add deterministic loss, gradient, replay, validity and classifier boundary checks
- add: `scripts/s09_e010_no_step_preflight.py` - Add read-only frozen-packet implementation preflight with no optimizer path
- add: `docs/research/S09/S09-E010/no_step_preflight_20261018.json` - Record 16-cycle frozen-packet no-step evidence and exact identities
- add: `docs/research/S09/S09-E010/implementation_status_20261018.md` - Separate core candidate evidence from Code Ready and execution
- modify: `source/s09_e010_support_amplitude.py` - Canonicalise validated AUC from integer pair counts before inherited classification
- modify: `tests/test_s09_e010_support_amplitude.py` - Add canonical AUC boundary regression and standalone nonzero L_A gradient assertion
- modify: `scripts/s09_e010_no_step_preflight.py` - Add independent frozen-cycle NumPy L_S and L_A reference checks
- modify: `docs/research/S09/S09-E010/no_step_preflight_20261018.json` - Refresh no-step receipt with independent reference differences

## Input Assets
- `docs/research/S09/S09-E010/experiment.md` (frozen protocol; exists)
- `docs/research/S09/S09-E010/design_review.md` (independent design review; exists)

## Output Assets
- `source/s09_e010_support_amplitude.py` (core numerical contract; exists)
- `tests/test_s09_e010_support_amplitude.py` (deterministic tests; exists)
- `docs/research/S09/S09-E010/no_step_preflight_20261018.json` (frozen packet receipt; exists)

## Tests
- pass: selected core and inherited regressions - 61 passed; direct loss formulas, zero-gradient handling, exact A25 direction, same-state physics decomposition, single clip, validity ordering and cumulative classifier all pass.
- pass: frozen 16-cycle no-step preflight - NO_STEP_PREFLIGHT_PASS; A25 exact direction max difference 0; B25-B0 physics residual 1.3704315460216776e-16; model hash unchanged; optimizer steps 0.
- pass: static checks - New module, preflight and tests pass Ruff; syntax and whitespace checks pass.
- pass: focused blocker regression and inherited suite - 62 passed; canonical pair-count AUC boundary and standalone nonzero L_A gradient regression pass.
- pass: revised frozen 16-cycle no-step preflight - NO_STEP_PREFLIGHT_PASS; independent max abs differences L_S=2.842170943040401e-14 and L_A=3.469446951953614e-17 under 1e-12; model hash unchanged; optimizer steps 0.

## Result Interpretation
Exact commit 45d8ec5f158d6fbdc608437f02da4fa43501157f received CORE_CODE_READY_PASS after closing canonical-AUC and frozen-loss-reference blockers; this is Code Ready core evidence only.

## Claim After Attempt
The S09-E010 support/amplitude numerical core is independently code-reviewed and ready for runner/config/evidence integration without training.

## Next Action
Implement runner/config/evidence integration from exact commit 45d8ec5f158d6fbdc608437f02da4fa43501157f, keep it no-step, and submit a separate exact-commit review before any execution.
