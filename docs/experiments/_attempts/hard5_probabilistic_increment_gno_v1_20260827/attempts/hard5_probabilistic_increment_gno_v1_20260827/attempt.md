# Attempt hard5_probabilistic_increment_gno_v1_20260827

- Status: `tested`
- Created: 2026-08-27T00:07:55+01:00
- Closed: None
- Type: `architecture_experiment`
- Human decision required: True

## Motivation
Test direct t+1 four-field increment prediction with an explicit conditional Laplace scale on the existing Hard5 LOAO trajectories.

## Trigger
User authorized the four-field increment model on 2026-08-27.

## Current Claim Before Attempt
Current absolute-state GNO is a processed-GRIPHFiTH imitation diagnostic with frozen aggregate FAIL; seed spread is useful for damage/fatigue but weak for raw psi.

## GPT Pro Advice
- Required: True
- Advice path: ``
- Advice sha256: ``

Not recorded.

## Adopted Decision
Implement t+1 four-field increment mean and conditional Laplace scale only; omit onset heads from v1.

## Rejected Or Modified Advice
Five-member ensemble reduced to three locked seeds for direct comparability and cost; formal calibrated coverage remains prohibited.

## Decision Rationale
This isolates the representation change requested by the user and prevents onset-label design from confounding the point-prediction result.

## Success Criteria
- U0.12 fixed four-origin point gate passes; uncertainty remains non-gating and uncalibrated.

## Failure Criteria
- Leakage
- nonfinite/provenance failure
- or fixed point gate failure.

## Code Changes
- add: `source/probabilistic_increment_mesh_operator.py` - Add separate constrained four-field increment location and bounded Laplace scale decoders
- add: `SENS_tensile/train_probabilistic_increment_loao_gno.py` - Add t+1 LOAO windows, trajectory-balanced sampling, two-stage mean/scale optimization, heldout metrics and selected field export
- add: `tests/test_probabilistic_increment_mesh_operator.py;tests/test_probabilistic_increment_loao_gno.py` - Add model, leakage, sampler, calibration, evaluation and Mac no-training tests
- modify: `SENS_tensile/train_probabilistic_increment_loao_gno.py` - Add fail-before-output Taobo identity, GPU ownership, exact code/data/auth lock, runtime provenance, pending receipt and verified archive finalization
- add: `SENS_tensile/analyze_probabilistic_increment_gno_matrix.py` - Add fail-closed nine-job analyzer, fixed U0.12 point gate, weighted scale-error association, risk-coverage and ensemble total variance
- add: `docs/experiments/hard5_probabilistic_increment_gno_matrix_lock_20260827.json` - Lock three-fold three-seed Taobo matrix, dataset, protocol, code hashes and payload allowlist

## Input Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/hard5_loao_gno_dataset_v1_20260826` (frozen_three_trajectory_dataset; exists)

## Output Assets
- `docs/experiments/hard5_probabilistic_increment_gno_v1_result.md` (decision_note; missing)

## Tests
- pass: focused_and_regression_tests - 66 tests passed; old frozen Hard5 path remains green.
- pass: real_data_forward_backward - shape 86408x4; parameter_count 367400; event windows one per training trajectory; mean and scale gradients finite and phase-isolated.
- pass: production_and_aggregate_regression - 74 tests passed; production preflight missing/corrupt data leaves no output; analyzer PASS/FAIL/nonfinite/complement contracts pass.
- pass: real_three_fold_forward_probe - All folds use exact two-trajectory complement; one event window per training trajectory; 367400 parameters; [86408,4] means and scale losses finite.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
