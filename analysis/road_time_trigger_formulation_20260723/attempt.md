# Attempt road-time-trigger-formulation-20260723

- Status: `quarantined`
- Created: 2026-07-24T00:08:22+01:00
- Closed: 2026-07-24T00:08:40+01:00
- Type: `framework-validation`
- Human decision required: True

## Motivation
Define a leakage-safe road-time, short-to-long forecast, and inspection-trigger interface using frozen matched temporal predictions.

## Trigger
User assigned Agent2 to connect h1-h3 conditional propagation to road inspection and RUL.

## Current Claim Before Attempt
One FEM trajectory supports only conditional h1-h3 propagation; no road-time mapping or early-warning generalisation.

## GPT Pro Advice
- Required: False
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Use a calibrated load block with calendar/environment caps; keep h1-h3 as conditional state propagation and long horizon as scenario-conditioned hazard/RUL; audit a model-only trigger offline.

## Rejected Or Modified Advice
Do not use the historical cycle-phase model; do not tune thresholds on c87/c89; do not claim the diagnostic trigger is road validated.

## Decision Rationale
The current FEM cycle has no evidence-based road-time conversion, and unlimited recursion fails the unseen transition.

## Success Criteria
- Deliver valid JSON interfaces
- a model-only trigger trajectory with FEM audit columns excluded from decisions
- figures
- decision note
- tests
- and manifest without training.

## Failure Criteria
- Any trigger reads FEM truth
- maps FEM cycle directly to road time
- uses cycle/89
- or promotes one-trajectory thresholds.

## Code Changes
- add: `source/road_forecast_trigger.py` - Added road-time specifications, model-only trigger signals, frozen envelopes, and Agent1 contract
- add: `SENS_tensile/analyze_road_forecast_triggers.py` - Added analysis-only package generator and figures over 18 frozen matched predictions
- add: `tests/test_road_forecast_trigger.py` - Added leakage, audit-separation, formula, and interface tests
- modify: `SENS_tensile/analyze_road_forecast_triggers.py` - Replaced hard-coded c87/c89 plot markers with dynamically derived request/stop cycles during pre-commit audit
- modify: `tests/test_road_forecast_trigger.py` - Added regression test prohibiting hard-coded c87/c89 trigger markers
- modify: `SENS_tensile/analyze_road_forecast_triggers.py` - Made CSV line endings deterministic LF so package passes git whitespace audit

## Input Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/temporal_architecture_study_20260718` (18 matched temporal prediction archives; exists)
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/fem_anchored_mesh_operator_20260715/data/fem_cycle_peak_mechanism_graph.npz` (FEM audit reference; exists)

## Output Assets
- `analysis/road_time_trigger_formulation_20260723/decision.md` (framework verdict; exists)
- `analysis/road_time_trigger_formulation_20260723/observation_trigger_spec.json` (Agent1-compatible trigger interface; exists)

## Tests
- pass: unit-tests - 10 tests passed; no training loop entered.
- pass: offline-package - 98 rows generated; package validator passed; model-only committee requested at c83 after the audit-only IoU gate had already failed at c81.
- pass: precommit-full-suite - 109 tests pass after figure leakage audit fix.

## Result Interpretation
Road-time and forecast-horizon interfaces are accepted as framework diagnostics. Numerical trigger thresholds are quarantined because the model-only warning lags hidden support failure and only one trajectory exists.

## Claim After Attempt
A rolling observed-state h1-h3 forecast plus scenario-conditioned hazard/RUL is the defensible road formulation; observation innovation and physically diverse calibration are required for inspection triggering.

## Next Action
Integrate Agent1 road_observation_operator_spec and evaluate image/FWD/strain innovations on independent trajectories before any new model training.
