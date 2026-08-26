# D1 transition-aware GNO preregistration

**Date:** 2026-08-26
**Status:** `REVISED_AFTER_INDEPENDENT_REVIEW__ONE_FULL_JOB_SMOKE_AUTHORIZED`
**Training authorization:** one exact hard-5/seed-1 3,000-step Taobo job only;
the remaining 11 jobs require a successful asset/provenance check

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
- Outputs: constrained next-cycle four-field state plus one autonomous,
  uncalibrated transition score. The score is fed to the field decoder; no
  true transition label is fed at inference.
- Context 3; recurrent training rollout 3; 3,000 optimizer steps; AdamW
  learning rate `3e-4`, weight decay `1e-6`; gradient clip 5.
- Sampling alternates 1:1 between transition-containing and ordinary windows.
  The transition label is 1 exactly when a target cycle is at or after the
  training trajectory's first-hit cycle.
- Loss: existing supervised field/support/edge-gradient loss plus `0.25` times
  transition BCE. PDE, equilibrium, AT1, KKT, constitutive and Carrara-history
  residual weights are all exactly zero.
- Seeds: 1, 2 and 3. Total matrix: four folds times three seeds = 12 jobs.

The exact machine-readable lock is
[`at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json`](at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json).

## Locked evaluation

For each held-out trajectory, make autonomous three-step rollouts from the
three origins immediately before first hit. This gives nine warning rows:
three negatives and six positives, matching the prior-control protocol.

This is a **retrospective event-centred benchmark**: held-out first-hit is used
only to select these evaluation origins, never in optimization. The primary
warning is the uncalibrated transition score thresholded at exactly `0.5`;
field-topology hit is diagnostic only.

Primary transition gate, evaluated on seed medians per fold:

1. recall at least 4/6 transition-positive rows and no more than 1/3 false
   warnings in at least three of four folds; and
2. on the same nine states, lower active log-MAE and higher absolute FEM-p99
   IoU than the best locked Markov/TCN/Transformer control in at least three of
   four folds.

Both clauses are required. A transition classifier that does not improve the
predicted fields does not pass. In-sample fitting cannot pass.

PIDL comparison is deferred and `not_evaluable` until an exact matched-state
asset manifest and hashes are frozen. D1 cannot support “better than PIDL.” Its
locked controls are the verified 36/36 Markov/TCN/Transformer factorial
package, with hashes and aggregation semantics stored in the matrix lock.

## Required assets

Each job must contain `RUN_MANIFEST.json`, `training_history.csv`,
`fem_centred_metrics.csv`, `transition_warning_metrics.csv`,
`locked_transition_predictions.npz`, and `final_model.pt`. The aggregate must
add a 12-job completeness table, seed-median fold table, paired-control table
and one decision note. Every manifest must record exact git/code/lock/data and
runtime provenance, `physics_loss_weight: 0.0`,
`heldout_first_hit_used_in_training: false`, `teacher_qualified: false`,
`damage_fixed_point_gate: fail`, and the processed-archive target semantics.

## Runner and current verification

- Model: `source/transition_aware_mesh_operator.py`.
- Single-job runner: `SENS_tensile/train_transition_aware_loco_gno.py`.
- Tests: `tests/test_transition_aware_loco_gno.py` plus the existing
  `tests/test_fem_mechanism_operator.py`.
- Initial local result: 14 tests passed; both new Python files compile; CLI help loads;
  model capacity is 339,461 parameters.
- The runner refuses Mac training, requires `--allow-data-only-d1`, verifies
  the dataset hash manifest, refuses non-fresh output directories and freezes
  the stated hyperparameters.

## Launch boundary

The independent review returned `REVISE`: no P0 training/leakage defect, but it
required immutable code, strict hash enforcement, one frozen warning estimand,
locked controls and fuller provenance. After those revisions pass from a clean
commit, the user's 2026-08-26 request authorizes one exact hard-5/seed-1 Taobo
producer smoke. The remaining 11 jobs stay blocked until the smoke completes
with all assets and hashes valid.
