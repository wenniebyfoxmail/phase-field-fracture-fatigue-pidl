# Attempt S09-E010-A001-design

- Status: `accepted`
- Created: 2026-10-18T10:43:09+01:00
- Closed: 2026-10-18T10:58:15+01:00
- Type: `diagnostic-design`
- Human decision required: False

## Motivation
Test the smallest controllable support-and-amplitude multi-objective repair for E009 regime-ranking failure while preserving its component gains.

## Trigger
S09-E009 valid mixed-tradeoff result plus frozen target-support concentration diagnostic.

## Current Claim Before Attempt
E009 shows a finite-budget damage-component signal, but the present PINO anchor does not improve amplitude ranking or median spatial alignment.

## GPT Pro Advice
- Required: True
- Advice path: `design_review.md`
- Advice sha256: ``

Full review found one cumulative-classifier ambiguity; protocol v2 closed it. Focused rereview verified the v2 ZIP and 2/2 manifest hashes and returned DESIGN_READY_PASS, limited to local implementation, deterministic no-step preflight and exact-commit review.

## Adopted Decision
Adopt protocol v2 as the frozen design for local implementation only.

## Rejected Or Modified Advice
No review finding was rejected. The floating-point boundary note was incorporated as an equivalent integer decision rule.

## Decision Rationale
The single Level-6 inheritance ambiguity is now explicit, the pair-count criterion is exactly equivalent to Delta_AUC>=0.08, and independent review found no remaining design blocker.

## Success Criteria
- A reviewed protocol isolates the combined support/amplitude intervention and freezes a feasible primary criterion
- protected limits
- budget and fail-closed evidence.

## Failure Criteria
- Leakage
- causal ambiguity
- undefined gradient semantics
- unjustified threshold
- or an overconstrained/underconstrained decision hierarchy remains.

## Code Changes
- modify: `docs/research/S09/S09-E010/experiment.md` - Clarify cumulative Level-6 classification and use the exact integer pair-count implementation of the unchanged AUC threshold
- add: `docs/research/S09/S09-E010/design_review.md` - Record the full and focused independent design reviews and implementation safeguards

## Input Assets
- `docs/research/S09/S09-E009/run_analysis_20261018.md` (E009 result analysis; exists)
- `docs/research/S09/S09-E009/post_run_support_diagnostic_20261018.json` (support concentration diagnostic; exists)
- `docs/research/S09/S09-E010/support_mask_threshold_sensitivity_20261018.json` (mask threshold sensitivity; exists)

## Output Assets
- `docs/research/S09/S09-E010/experiment.md` (prospective protocol; exists)
- `docs/research/S09/S09-E010/design_review.md` (independent design review; exists)

## Tests
- None

## Result Interpretation
The three-arm support/amplitude protocol is design-ready for local implementation. This establishes protocol adequacy only; no code candidate, no-step preflight or training result exists.

## Claim After Attempt
S09-E010 protocol v2 has DESIGN_READY_PASS for local implementation, deterministic no-step preflight and exact-commit review.

## Next Action
Implement the frozen three-arm numerical and classifier contract locally, execute only deterministic no-step checks, then submit the exact commit for review. Do not train.
