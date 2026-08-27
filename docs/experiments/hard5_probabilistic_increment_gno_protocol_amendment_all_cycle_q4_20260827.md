# Protocol amendment: trajectory-wide native-Q4 evaluation

Experiment: `hard5_probabilistic_increment_gno_v1_20260827`

Date: 2026-08-27

Status: `FROZEN_PENDING_EXACT_COMMIT_REVIEW_AND_OWNER_RELEASE_AUTHORIZATION`

## Why this amendment exists

The original pre-launch protocol made U0.12 c20/c40/c60/c80 the primary point-prediction gate. Before any run under that protocol, the user clarified that the FEM archive provides native Q4 fields at every cycle. Restricting the verdict to four inspected cycles would discard valid prediction opportunities and could reward an unrepresentative subset.

GPT Pro independently recommended a symmetric all-legal-pre-hit evaluation across all three held-out folds and treating fixed origins only as secondary diagnostics. Its recorded advice is in `hard5_probabilistic_increment_gno_gpt_pro_advice_20260827.md`.

## Superseded rule

The U0.12-only gate at c20/c40/c60/c80 is superseded before producer execution. No Taobo result was generated under that rule, and it must not be used to determine success.

## Replacement primary rule

- Evaluate every legal pre-hit `t -> t+1` origin on all three held-out trajectories.
- Evaluate all 86,408 native Q4 cells in the whole-domain scope.
- Also evaluate, separately for each origin and channel, the deterministic highest-true-FEM-change cells covering at least 5% of native-cell area.
- The active mask is ground-truth evaluation stratification only. It cannot enter training, normalization, scale fitting, selection or model input.
- Reduce median across origins within seed, median across three seeds within fold, then median across the three folds.
- In each scope, require GNO to beat persistence in at least three of four channels, beat constrained-linear in at least two, and have no channel more than 10% worse than persistence.
- Both scopes must pass. Uncertainty diagnostics cannot rescue either scope.

## Secondary field-map anchors

The previously fixed origins remain non-gating visualization anchors:

- U0.11: c20/c40/c60/c120
- U0.12: c20/c40/c60/c80
- U0.13: c20/c30/c45/c58

They are useful for reading early, middle, accelerating and near-event field behavior, but they do not decide the experiment.

## Claim boundary and release consequence

The experiment remains processed-GRIPHFiTH archive imitation only, with no physics residual or physical validation. This amendment invalidates the prior exact-commit review for launch. A new clean commit, matrix hash, independent review and owner authorization are required before Taobo execution.
