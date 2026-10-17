# Attempt freeze_select_stage_a_20260804

- Status: `tested`
- Created: 2026-08-04T12:06:42+01:00
- Closed: None
- Type: `framework-validation`
- Human decision required: False

## Motivation
Build a bounded frozen-field weak residual selector before any producer or road-data claim

## Trigger
Active Freeze-Then-Select research goal

## Current Claim Before Attempt
No implementation or validation exists; literature route only

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/freeze_then_select/gpt_pro_plan_2026-08-04.md`
- Advice sha256: `3d9d8e0a7e157576e991a04b775d347a9e6a599426e0ac060015bacd3d564de5`

Path correction: adopted isolated tooling-only frozen snapshot selector, grouped stability validation, explicit thresholds and road claim boundary

## Adopted Decision
Implement and test Stage A on Mac without training

## Rejected Or Modified Advice
Deferred spatial derivative candidates, existing-field Stage B, joint training, and all road mechanism claims

## Decision Rationale
Cheapest diagnostic can falsify schema, weak assembly, support stability and leakage before producer work

## Success Criteria
- Exact declared-support recovery
- deterministic grouped trials
- >=5% held-out improvement
- tooling-only claim

## Failure Criteria
- Unstable support
- leakage
- no held-out improvement
- oracle use
- or known-physics selection

## Code Changes
- add: `SENS_tensile/freeze_select/` - Add isolated schema, library, weak system and selectors
- add: `SENS_tensile/run_freeze_select_synthetic.py` - Add deterministic manufactured Stage A runner
- add: `tests/test_freeze_select.py` - Add schema, claim-boundary, fixed-physics and deterministic support tests
- modify: `SENS_tensile/freeze_select/weak_system.py` - Replace warning-prone BLAS weighted products with explicit finite weak sums
- modify: `SENS_tensile/freeze_select/selectors.py` - Add trial support Jaccard and candidate correlation warnings
- add: `docs/freeze_then_select/stage_b_c_producer_protocol_2026-08-04.md` - Record current FEM23 insufficiency and exact producer export/fair comparison protocol
- add: `SENS_tensile/run_freeze_select_from_snapshot.py` - Add generic hashed frozen-snapshot analysis package runner

## Input Assets
- `SENS_tensile/run_freeze_select_synthetic.py` (manufactured frozen snapshots; exists)

## Output Assets
- `_analysis_freeze_select_stage_a_20260804/decision.md` (tooling gate decision; exists)

## Tests
- pass: dedicated_unit_tests - 3 passed; schema boundary, fixed-physics exclusion, determinism, grouped holdout and exact support recovery passed
- pass: manufactured_stage_a - Exact 3-term stable support; Jaccard 1.0 across thresholds 0.60-0.90; mean grouped holdout improvement 0.997; single-shot also exact; correlation warnings retained
- pass: generic_snapshot_package_test - 4 passed including generic hashed nonroad package output and road-claim false guard

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
