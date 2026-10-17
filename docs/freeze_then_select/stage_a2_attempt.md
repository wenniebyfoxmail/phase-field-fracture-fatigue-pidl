# Attempt freeze_select_stage_a2_20260804

- Status: `quarantined`
- Created: 2026-08-04T12:22:30+01:00
- Closed: 2026-08-04T12:37:02+01:00
- Type: `framework-validation`
- Human decision required: False

## Motivation
Validate leakage-safe sparse observations through structured freeze, stable selection and future crack forecast

## Trigger
Stage A frozen-field gate passed but full goal still lacked sparse reconstruction and forecast evidence

## Current Claim Before Attempt
Stage A proves tooling support recovery only on complete manufactured frozen fields

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/freeze_then_select/gpt_pro_stage_a2_plan_2026-08-04.md`
- Advice sha256: `514c21d89c4c1af5b7f0e786bec83979d39633201ba8b98814effc5e472db326`

Adopt dynamic equation-linked synthetic sections, cutoff-safe DCT-B-spline adapter, whole-section holdout and forecast gates

## Adopted Decision
Implement and run narrowed Stage A2 smoke before the 16-case matrix

## Rejected Or Modified Advice
Deferred moving/joint selector to A2b and retained explicit non-neural non-road claim boundary

## Decision Rationale
Oracle-first synthetic gate is the cheapest way to falsify leakage, adapter, selection and forecast integration

## Success Criteria
- Oracle
- adapter
- reconstructed support and holdout crack forecast gates pass without future damage leakage

## Failure Criteria
- Oracle
- adapter
- selection or forecast gate fails; classify limitation without road claim

## Code Changes
- add: `SENS_tensile/freeze_select/structured_adapter.py` - Add cutoff-safe spatial-DCT temporal-B-spline adapter and immutable freeze hash
- add: `SENS_tensile/freeze_select/synthetic_forecast.py` - Add equation-linked synthetic sections, grouped selection, rollout and crack geometry metrics
- add: `tests/test_freeze_select_stage_a2.py` - Add adapter leakage, dynamic-link and forecast-package tests
- modify: `SENS_tensile/freeze_select/weak_system.py` - Add compact interior time weak derivative by integration by parts
- add: `SENS_tensile/run_freeze_select_stage_a2_matrix.py` - Add predeclared 16-case robustness matrix and aggregate gates
- modify: `SENS_tensile/freeze_select/selectors.py` - Add independent validation-section minimal near-best support selection

## Input Assets
- `SENS_tensile/run_freeze_select_stage_a2.py` (dynamic synthetic sparse observations; exists)

## Output Assets
- `_analysis_freeze_select_stage_a2_smoke_20260804/decision.md` (Stage A2 classified decision; exists)

## Tests
- pass: stage_a2_unit_tests - 7 passed without warnings; dynamic linkage, cutoff leakage guard, adapter and package checks passed
- pass: stage_a2_smoke - Single smoke passed oracle, adapter, support and forecast gates; reconstructed SVWS exact versus single-shot Jaccard 0.429
- fail: stage_a2_16_case_matrix - Matrix rejected: oracle and adapter pass; median SVWS support Jaccard 0.292 below single 0.354; IoU gains positive but support and tip gates fail; 2/16 cases pass

## Result Interpretation
Leakage-safe closed loop is implemented and one smoke passes, but the predeclared 16-case matrix rejects reliable support recovery and SVWS superiority; positive IoU gains do not compensate for mechanism and tip failures

## Claim After Attempt
Tooling can reconstruct and forecast synthetic sections, but Freeze-Then-Select is not yet shown to improve reliable road-crack mechanism selection or overall prediction reliability

## Next Action
Do not launch producer training; first design an uncertainty-aware weak selector or adapter-residual calibration that improves support accuracy on the sealed matrix without changing holdouts or gates
