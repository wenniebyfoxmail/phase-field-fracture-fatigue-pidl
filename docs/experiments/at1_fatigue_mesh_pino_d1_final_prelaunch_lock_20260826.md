# D1 transition-aware GNO final pre-launch lock

**Date:** 2026-08-26
**Status:** `POST_REMEDIATION_REVIEW_APPROVED__OWNER_AUTHORIZED_FOR_TAOBO`
**Claim class:** synthetic FEM imitation / trajectory sufficiency
**Training authorization:** frozen 12-job Taobo D1 matrix only

## PIDL Experiment Gate

- **Mechanism question:** can a transition-aware native-mesh GNO reproduce an
  unseen complete FEM trajectory's terminal transition and fields better than
  the locked data-only controls and matched PIDL states?
- **Claim changed if success:** only that this four-trajectory, shared-mesh,
  Umax=0.12 synthetic FEM transition is learnable by the frozen GNO-data
  protocol.
- **Claim changed if failure:** the current four trajectories and architecture
  are insufficient; no conclusion follows about FEM physical correctness.
- **Cheaper diagnostic first:** the prior 36-run LOCO failure, two independent
  code reviews, unit/static checks, event-predicate replay and four-fold
  gradient-calibration probe are complete.
- **Minimal output asset:** a 12-job completeness table, seed-median fold table,
  paired control/PIDL table, locked predictions and one `decision.md`.
- **Registry destination:** update the existing D1 row in
  `docs/pidl_experiment_inventory.md` and this canonical track; do not create a
  parallel success narrative.
- **Decision:** owner launch authorization was received on 2026-08-26 for the
  frozen 12-job Taobo D1 matrix. Each job must pin the final commit SHA and
  matrix-lock SHA.

## Frozen training contract

The data, split, model, inputs, prohibited leakage features, context/rollout,
3,000 steps, three seeds and zero physics-loss contract are those in
[`at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json`](at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json).

The loss amendment is final before launch:

1. training-fold residual-scaled SmoothL1 field loss;
2. stable logits-based support loss;
3. training-fold derived-active residual scale;
4. ordinary and transition buckets divided by their separate mean persistence
   **prediction-gradient L2 norms**, not their loss values;
5. alternating 1:1 bucket sampling and transition BCE weight 0.25.

The calibration is computed only from the three training trajectories in each
fold. The frozen diagnostic tolerance is that each bucket's mean persistence
prediction-gradient divided by its stored scale lies in `[0.99, 1.01]`. Any
fold outside this range stops before optimizer step 1.

## Evaluation populations

### Primary retrospective transition stress test

The primary remains the locked nine `(origin, target)` opportunities adjacent
to the held-out first hit: three negatives and six positives. It is explicitly
retrospective and event-aligned.

Using seed medians per fold, both conditions must hold in at least three of
four folds:

1. recall at least `4/6` and false warnings at most `1/3`;
2. lower derived-active log-MAE and higher absolute FEM-p99 IoU than the best
   locked Markov/TCN/Transformer control on the same nine opportunities.

### All legal forecast opportunities

The secondary population is every legal overlapping `(origin, horizon)` pair.
It is not called a natural cycle distribution. Report overall, h1, h2 and h3
precision, recall, FPR, Brier and fixed 10-bin ECE, plus the unique-cycle h1
summary. Threshold is fixed at 0.5 and may not be tuned on held-out results.

This secondary gate fails if, using seed medians, either overall recall is
below `2/3` or overall FPR exceeds `0.10` in at least two of four folds. It also
fails if any single horizon has FPR above `0.20` in at least two folds. Brier
and ECE are mandatory diagnostics but are not promotion thresholds with only
four independent trajectories.

### Matched PIDL comparison

“Better than PIDL” may be written only if both hard-5 and hard-8 matched folds
have lower derived-active log-MAE and higher absolute FEM-p99 IoU than PIDL on
exact same-cycle states. Missing states are `not_evaluable`, never imputed.
Soft folds do not support a PIDL superiority claim.

## Success, failure and stop rules

All primary transition/field conditions and the forecast-opportunity stop gate
must pass. PIDL superiority additionally requires the separate two-hard-fold
condition. In-sample reconstruction, damage-only improvement, event timing
alone, or one favorable seed cannot pass.

Stop and classify D1 negative if any of the following occurs:

- fewer than three folds pass the conjunctive primary gate;
- the forecast-opportunity stop gate fails;
- any held-out value enters training, normalization, calibration or threshold
  selection;
- any of 12 jobs is missing, non-finite, hash-mismatched or provenance-invalid;
- post-result architecture, loss, threshold or mask tuning is attempted on
  these same four held-out trajectories.

The first complete four-fold result is exploratory because only four
independent trajectories exist. Seeds are optimization repeats, not scientific
replicates.

## Producer and release lock

The runner requires one idle Taobo RTX 4090, mounted `/mnt/data2` with at least
50 GiB free, fresh job output/archive roots, and task-owned archive/log/temp/
cache environments. It writes `LAUNCH_RECEIPT.json` before dataset load and
records argv, cwd, PID, session, launch time, device, environment and hashes.
On successful completion it mirrors every non-receipt payload into the task
archive, freezes the full payload SHA-256 inventory, and only then atomically
writes identical completion receipts to output and archive. A finalization
error downgrades both receipts to `archive_finalization_failed`; success
requires matching complete receipts plus the matching payload inventory.

The code lock includes the model, runner, tests,
`source/fem_mechanism_operator.py` and
`SENS_tensile/train_fem_mechanism_mesh_operator.py`. Owner authorization must
provide the final 40-character commit and matrix-lock SHA; the runner verifies
both against the clean checkout or declared rsync snapshot.

## Current evidence boundary

Local verification after remediation:

- 30 unit/contract tests pass; Python compilation, strict JSON parsing, exact
  dataset lock and `git diff --check` pass.
- The four held-out folds contain 12 transition windows and 232--235 ordinary
  windows in their respective training splits.
- Before gradient calibration, transition/ordinary mean persistence-gradient
  ratios are `0.370510`, `0.380303`, `0.390826` and `0.377615` for hard5,
  hard8, soft5 and soft8 holdouts. After division by the training-fold bucket
  gradient scales, both bucket baselines are `1.000000` in all four folds.
- The complete mocked Taobo preflight contract passes; Mac, missing producer
  identity and multiple-visible-GPU cases fail before output creation.

An earlier Taobo batch from the pre-remediation snapshot was discovered during
the launch audit. Its queued workers were stopped without terminating the two
jobs already completing; all of its outputs are quarantined from this frozen
matrix because that snapshot lacked the final release/provenance contract.

Local tests and read-only probes establish only that the amended experiment
contract is mechanically coherent. They do not establish GNO efficacy, PIDL
superiority, physical validity or road prediction.
