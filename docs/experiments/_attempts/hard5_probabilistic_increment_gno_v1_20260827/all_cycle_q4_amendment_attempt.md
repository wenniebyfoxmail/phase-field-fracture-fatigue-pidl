# Attempt hard5_probabilistic_increment_gno_all_cycle_q4_amendment_20260827

- Status: `tested`
- Created: 2026-08-27T09:54:01+01:00
- Closed: None
- Type: `evaluation_protocol_amendment`
- Human decision required: True

## Motivation
Use FEM native Q4 truth at every legal pre-hit cycle instead of deciding the experiment from a few representative origins.

## Trigger
User clarified on 2026-08-27 that FEM provides native Q4 fields for every cycle and fixed c20/c40/c60-style cycles should be a starting visualization only.

## Current Claim Before Attempt
No producer run has occurred for the probabilistic increment model; the previous fixed-origin release candidate is superseded for launch.

## GPT Pro Advice
- Required: True
- Advice path: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-loao-gno-20260826/docs/experiments/hard5_probabilistic_increment_gno_gpt_pro_advice_20260827.md`
- Advice sha256: `8d239579d973c53d369d3564ca66afe48d7e9ee32c198095f4c953aa2bf865bd`

GO_AFTER_PROTOCOL_AMENDMENT: primary evaluation must be symmetric and trajectory-wide across all legal pre-hit origins and native Q4; fixed origins are secondary only.

## Adopted Decision
Freeze all-cycle native-Q4 whole-domain plus true-change top-5%-area primary scopes across all three folds; keep selected cycles non-gating.

## Rejected Or Modified Advice
Uncertainty and three-seed disagreement remain diagnostic and cannot rescue point-prediction failure.

## Decision Rationale
This uses all available FEM prediction opportunities while retaining readable field-map anchors and preventing low-change background dominance.

## Success Criteria
- Both whole-Q4 and FEM true-change top-5%-area trajectory-wide gates pass under the frozen hierarchical reduction.

## Failure Criteria
- Any scope fails; any fixed representative origin influences the primary verdict; leakage
- nonfinite data
- provenance or archive contract fails.

## Code Changes
- add: `docs/experiments/hard5_probabilistic_increment_gno_protocol_amendment_all_cycle_q4_20260827.md` - Record the pre-result supersession and replacement all-cycle native-Q4 gate
- modify: `SENS_tensile/train_probabilistic_increment_loao_gno.py` - Export both scopes for every legal pre-hit origin
- modify: `SENS_tensile/analyze_probabilistic_increment_gno_matrix.py` - Aggregate all origins seeds and folds and keep representative origins secondary

## Input Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/hard5_loao_gno_dataset_v1_20260826` (frozen_three_trajectory_dataset; exists)

## Output Assets
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-loao-gno-20260826/docs/experiments/hard5_probabilistic_increment_gno_v1_result.md` (decision_note; missing)

## Tests
- pass: all_cycle_native_q4_contract - 88 tests passed, including a negative test proving good representative origins cannot rescue bad trajectory-wide performance.
- pass: real_frozen_all_cycle_q4_probe - u011/u012/u013 provide 119/80/56 legal origins; all 1020 origin-channel active masks are finite and cover at least 5% area.

## Result Interpretation
Not recorded.

## Claim After Attempt
Not recorded.

## Next Action
Not recorded.
