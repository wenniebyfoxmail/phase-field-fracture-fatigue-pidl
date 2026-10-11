# Attempt S09-E006

- Status: `accepted`
- Created: 2026-10-11T23:33:45+01:00
- Closed: 2026-10-11T23:33:45+01:00
- Type: `multiobjective-gradient-training`
- Human decision required: False

## Motivation
Test whether explicit gradient-space multiobjective control can reduce fixed-damage equilibrium residual without exceeding a per-state displacement guard.

## Trigger
S09-E005 found 102-573x effective physics gradient dominance at nominal weight 0.01 and decoder-local conflicts.

## Current Claim Before Attempt
E004 fixed scalar weighting reduces equilibrium residual but worsens displacement; no general PINO conclusion.

## GPT Pro Advice
- Required: True
- Advice path: `evidence_review.md`
- Advice sha256: `2e098488329ad5e7d3476a4072ed45621f3a09705e4f6c3272aec3eea652bc6f`

Haofan ChatGPT Pro passed protocol v2 and exact commit ae01790 after requested fixes, then independently recalculated the frozen evidence and issued EVIDENCE_READY PASS.

## Adopted Decision
Run two predeclared gradient-balanced arms beta=0.25 and beta=1.0 against an exact data-only replay.

## Rejected Or Modified Advice
Rejected blind scalar-lambda tuning and post-result arm selection beyond the frozen final-only rule.

## Decision Rationale
Gradient-space scaling directly addresses the E005 scale audit while projection protects the data objective under negative dot products.

## Success Criteria
- Mean residual <=0.50 of data-only and every dev-state displacement error <=1.10 of its data-only comparator.

## Failure Criteria
- Any validity failure
- replay mismatch
- or either joint criterion fails.

## Code Changes
- add: `SENS_tensile/run_s09_pareto_rescue.py` - Implement float64 conflict projection, norm targeting, one global clip, and one AdamW step
- add: `SENS_tensile/analyze_s09_pareto_rescue.py` - Recalculate joint criteria and generate decision artifacts from raw outputs

## Input Assets
- `docs/research/S09/S09-E006/experiment.md` (frozen protocol; exists)
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S09-E004/runs/S09-E004-R005/output/common_warmup.pt` (common checkpoint; exists)

## Output Assets
- `docs/research/S09/S09-E006/decision.md` (scientific decision; exists)
- `docs/research/S09/S09-E006/evidence_review.md` (independent evidence review; exists)

## Tests
- pass: code-ready-focused-tests - 20 focused tests passed for projection, replay, clipping, failure isolation, and outputs.
- pass: taobo-r002-production - Three arms completed exactly 700 updates each from identical model and optimizer hashes; data-only replay passed.
- pass: frozen-joint-criterion - beta=0.25 achieved residual ratio 0.396805 and worst per-state displacement ratio 1.096920; beta=1.0 failed displacement guard.

## Result Interpretation
A predeclared weak gradient-balanced arm met the relaxed joint feasibility criterion on three reused fixed-damage dev states; stronger physics moved farther along the trade-off and violated the displacement guard.

## Claim After Attempt
Multiobjective gradient control is feasible for this fixed-damage development comparison; exact equilibrium, Pareto dominance, evolution, and generalization remain unestablished.

## Next Action
Freeze beta=0.25 and evaluate once on a fresh fixed-damage holdout without further tuning on these dev states.
