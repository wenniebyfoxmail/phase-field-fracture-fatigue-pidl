# Attempt road-observation-aware-stage1-20260723

- Status: `quarantined`
- Created: 2026-07-24T00:11:39+01:00
- Closed: 2026-07-24T00:12:28+01:00
- Type: `framework-validation`
- Human decision required: True

## Motivation
Add a reality-facing road observation/time/scenario interface without changing the matched temporal state path or fabricating road evidence.

## Trigger
User assigned Agent3 road observation-aware predictor goal.

## Current Claim Before Attempt
Graph operators support short observed-origin h1-h3 propagation but do not autonomously generate the c87 transition.

## GPT Pro Advice
- Required: False
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Implement only schema, backward-compatible conditioning paths, direct short-horizon and probabilistic risk heads, and a real-checkpoint offline transfer audit.

## Rejected Or Modified Advice
Rejected producer training, random RUL figures, invented road metadata, and further single-trajectory architecture sweep.

## Decision Rationale
Agent1/2 interfaces are not frozen and Mac training is prohibited; the user already fixed the architecture roles and scientific boundaries, so the cheapest falsification is strict transfer equivalence.

## Success Criteria
- Markov
- TCN
- and diagonal SSM preserve the first raw forecast exactly when new inputs are absent; schemas validate masks/provenance; no training is launched.

## Failure Criteria
- Legacy state path changes
- missingness is ambiguous
- or synthetic tooling output is presented as road/RUL evidence.

## Code Changes
- modify: `source/temporal_mesh_operator.py` - Add optional node-level metadata while preserving zero-dimension legacy behavior
- add: `source/road_observation_aware_operator.py` - Add versioned road observation sequence, future scenario, Markov/TCN/SSM forecaster, direct h1-h3 state heads, hazard/RUL heads, and legacy transfer
- add: `SENS_tensile/audit_road_observation_aware_transfer.py` - Audit three real matched checkpoints on the 86,408-element FEM graph without training

## Input Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/temporal_architecture_study_20260718/multi_origin_reanalysis_20260720/analysis/decision.md` (matched temporal evidence; exists)

## Output Assets
- `docs/road_observation_aware_stage1_20260723/decision.md` (stage decision; exists)
- `docs/road_observation_aware_stage1_20260723/legacy_transfer_audit.csv` (offline transfer table; exists)

## Tests
- pass: road and temporal unit regression - 31 tests passed; four existing Transformer nested-tensor warnings only.
- pass: real checkpoint legacy transfer - All three formal checkpoints have first raw horizon max absolute error 0.0; no training launched; risk heads remain random_untrained.
- pass: post-maintenance-contract regression - 32 tests passed after requiring explicit historical maintenance state reset and a future maintenance-effect model id.
- pass: censor-aware risk primitive regression - 33 tests passed after adding right-censored log-normal RUL likelihood and expected-RUL primitive.
- pass: static quality checks - Ruff and Python compilation pass with no findings.

## Result Interpretation
The road-aware interface is code-valid and preserves the matched state path, but no observation-aware or RUL scientific claim is possible before Agent1/2 specs and multi-trajectory data are frozen.

## Claim After Attempt
A legacy-compatible road observation/time/scenario interface now exists; road benefit, calibration, and transition prediction remain untested.

## Next Action
Ingest Agent1 and Agent2 frozen specs, rematch capacity, and gate one-seed identical-input producer smoke before any matrix training.
