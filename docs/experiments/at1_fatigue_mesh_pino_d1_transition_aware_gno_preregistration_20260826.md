# D1 transition-aware GNO preregistration

**Date:** 2026-08-26  
**Status:** `SUPERSEDED_BY_REVIEW_AMENDMENT__NO_LAUNCH`  
**Training authorization:** none

The independent code review found that the original objective, data lock,
evaluation distribution and producer provenance were insufficient. The
corrected contract is
[`at1_fatigue_mesh_pino_d1_review_amendment_20260826.md`](at1_fatigue_mesh_pino_d1_review_amendment_20260826.md).

## Question and claim boundary

Can a transition-balanced, native-mesh graph neural operator reproduce the
held-out FEM terminal transition better than the already locked Markov, TCN and
Transformer controls? This is supervised FEM imitation. The physics-loss
weight is exactly zero, so this experiment must be called `GNO-data`, not a
validated PINO. It cannot establish physical correctness or real-road
forecasting.

## Locked data and split

- Dataset ID: `factorial_loco_fem_states_v1`.
- Local endpoint:
  `$PROJECT/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729/`.
- Dataset manifest SHA-256:
  `b9723d613e7b7a5e33b4fb7c9a9cc65ef6d1ae6c4e9b971f64dc74ad0f955648`.
- Four complete trajectories: hard/soft initial tip crossed with 5/8 retained
  substeps, all at Umax=0.12. First-hit cycles are 83, 86, 84 and 83;
  confirmed cycles are 86, 89, 87 and 86.
- Four leave-one-complete-trajectory-out folds. Normalization, window labels
  and optimization use only the other three trajectories. No element-level
  random split is allowed.

## Locked model and optimization

- Inputs: the previous three FEM cycle-peak states
  `[d, alpha_bar, f, log10(psi_raw)]`, element coordinates, log area, and the
  four known factorial flags `[hard, soft, 5step, 8step]`.
- Prohibited inputs: cycle number, first-hit/confirmed cycle, event distance,
  future field, held-out normalization or held-out transition labels.
- Architecture: local/coarse GNO, hidden width 96, three local and two coarse
  message-passing blocks, 339,461 trainable parameters.
- Outputs: constrained next-cycle four-field state plus one autonomous
  transition probability. The probability is fed to the field decoder; no
  true transition label is fed at inference.
- Context 3; recurrent training rollout 3; 3,000 optimizer steps; AdamW
  learning rate `3e-4`, weight decay `1e-6`; gradient clip 5.
- Sampling alternates 1:1 between transition-containing and ordinary windows.
  The transition label is 1 exactly when a target cycle is at or after the
  training trajectory's first-hit cycle.
- Original loss specification: existing supervised field/support/edge-gradient
  loss plus `0.25` times transition BCE. This was rejected by review because
  transition reset steps dominated ordinary steps by roughly three orders of
  magnitude. The amendment replaces this objective before any training.
- Seeds: 1, 2 and 3. Total matrix: four folds times three seeds = 12 jobs.

The exact machine-readable lock is
[`at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json`](at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json).

## Locked evaluation

For each held-out trajectory, make autonomous three-step rollouts from the
three origins immediately before first hit. This gives nine warning rows:
three negatives and six positives, matching the prior-control protocol.

Primary transition gate, evaluated on seed medians per fold:

1. recall at least 4/6 transition-positive rows and no more than 1/3 false
   warnings in at least three of four folds; and
2. on the same nine states, lower active log-MAE and higher absolute FEM-p99
   IoU than the best locked Markov/TCN/Transformer control in at least three of
   four folds.

Both clauses are required. A transition classifier that does not improve the
predicted fields does not pass. In-sample fitting cannot pass.

Secondary PIDL comparison is restricted to hard-5/hard-8 held-out targets for
which exact same-cycle PIDL state semantics are available. The candidate must
beat PIDL on active log-MAE and absolute FEM-p99 IoU in both matched folds to
support the phrase “better than PIDL.” Missing PIDL states are reported as
`not_evaluable`, never imputed. The soft folds test GNO generalization but do
not create a PIDL comparison claim.

## Required assets

Each job must contain `RUN_MANIFEST.json`, `training_history.csv`,
`fem_centred_metrics.csv`, `transition_warning_metrics.csv`,
`locked_transition_predictions.npz`, and `final_model.pt`. The aggregate must
add a 12-job completeness table, seed-median fold table, paired control/PIDL
table and one decision note. The run manifest must record
`physics_loss_weight: 0.0` and `heldout_first_hit_used_in_training: false`.

## Runner and current verification

- Model: `source/transition_aware_mesh_operator.py`.
- Single-job runner: `SENS_tensile/train_transition_aware_loco_gno.py`.
- Tests: `tests/test_transition_aware_loco_gno.py` plus the existing
  `tests/test_fem_mechanism_operator.py`.
- Local result: 14 tests passed; both new Python files compile; CLI help loads;
  model capacity is 339,461 parameters.
- The runner refuses Mac training, requires `--allow-data-only-d1`, verifies
  the dataset hash manifest, refuses non-fresh output directories and freezes
  the stated hyperparameters.

## Launch boundary

No Taobo command, dispatcher or training process was started. Before a launch,
an independent framework/code review and a new explicit owner approval are
required. The approved producer is Taobo only; each job must use a fresh output
directory and preserve the exact code/data hashes in its manifest.
