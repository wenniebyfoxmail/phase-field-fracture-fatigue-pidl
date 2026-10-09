# S04-E013 Stage 1 supervised-capacity authorization

Review date: 2026-10-08
Planning verdict: `PLAN PASS`
Execution status: `ATTEMPT_B_COMPLETE__FAIL_FIXED_PROCEDURE__EVIDENCE_PASS`
External review conversation: <https://chatgpt.com/c/6ac816d7-8430-8329-98bb-a23484959fad>

## Purpose

Stage 1 asks whether one fixed finite-budget supervised procedure can reproducibly fit the four admitted conditional UV displacement targets across three prescribed seeds. It is not a test of theoretical network capacity, unsupervised physics recovery, native FEM fidelity, or FEM-teacher qualification.

## Planning review and adopted corrections

The first external planning review returned `NO-GO` with four blockers. The revised contract:

1. replaced the theoretical-capacity interpretation by a fixed-procedure reproducibility claim;
2. defined mass-proportional sampling without applying nodal mass a second time;
3. separated displacement/strain fit from the additional native-Q4 residual gate; and
4. fixed initialization, RNGs, optimizer, scheduler, determinism, coordinate normalization, metric definitions, and exact reference identities.

The second review returned `PLAN PASS`. It authorized contract freeze, runner implementation, and local non-training checks only. Taobo training remains blocked until an independent exact-commit `Code Ready PASS` reviews the implemented runner, evaluator, tests, data lock, and output contract.

The first exact-commit Code Ready review of `5767e6c` returned `NO-GO`. It found no optimizer-contract blocker, but the initial aggregator trusted the stored `joint_pass` field and did not require the complete checkpoint/prediction/receipt package. The bounded correction makes aggregation fail closed: it recomputes all thresholds from finite numeric metrics, requires strict Boolean consistency, checks final-step checkpoint and prediction hashes/content, verifies reference before/after identity and the Taobo run receipt, and emits `INADMISSIBLE` for malformed evidence. Synthetic non-training regression tests cover all four decision outcomes and the identified corruption paths. Re-review of exact commit `769396f93ae5258eb984e1585d4274f7990afb11` returned `CODE READY PASS`.

## PIDL Experiment Gate

- Mechanism question: can the registered architecture and finite-budget supervised procedure reproduce all four admitted early/middle/late/transition UV targets across three fixed initializations?
- Claim changed if success: grant `SUPERVISED_CAPACITY_PASS` only for this fixed procedure and admitted target set.
- Claim changed if failure: grant `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`; architecture representability remains unresolved.
- Cheaper diagnostic first: exact asset/hash/schema/BC/evaluator validation plus Mac unit and import checks; no Mac training.
- Minimal output asset: a 12-row `metrics.csv`, aggregate `summary.json`, final-only checkpoints with identities, and run receipts.
- Code/producer alignment: Mac implements and checks without entering a training loop. Formal execution is Taobo CUDA after exact-commit review.
- Success criteria: all 12 state-seed runs are valid and pass every frozen fit and mechanics gate.
- Failure criteria: one or more valid runs fails a gate. Missing or interrupted runs make the matrix `INCONCLUSIVE`; systemic identity/evaluator invalidity makes it inadmissible.
- Registry destination: S04-E013 decision record, S04 storyline, attempt ledger, and `censor.md` after execution/evidence review.
- Decision: implement and obtain Code Ready review; do not launch yet.

## Frozen matrix and outcome map

Required states are `c20s4`, `c60s4`, `c82s4`, and `c83s4`. Seeds are `1`, `7`, and `19`. Every state-seed pair uses a separately initialized network with no sharing or warm start.

- `12/12` valid joint passes: `SUPERVISED_CAPACITY_PASS`.
- `1--11/12` valid joint passes: `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`.
- Any missing or interrupted run: `INCONCLUSIVE`, unless a systemic validity failure invalidates the matrix.

No seed substitution, majority rule, retry, optional-state rescue, early stopping, result-driven budget extension, or checkpoint selection is allowed.

## Frozen training procedure

- Model: existing `NeuralNet(2, 2, 8, 400, "TrainableReLU", 1.0)` in float64.
- Input: affine-normalized physical coordinates in `[-1,1]^2`.
- Output: displacement only. The exact SENS ansatz imposes `u=0` at top and bottom, `v=0` at bottom, and `v=Us` at top.
- Initialization: CPU float64 Xavier uniform using the existing ReLU gain and zero linear biases. Trainable activation coefficients start at `1.0` and are optimized.
- RNG: model/CUDA seed `S`; NumPy PCG64 sampling seed `S+1000003`.
- Sampling: 16,384 nodes with replacement per step using normalized native-Q4 nodal mass. The sampled loss is the unweighted mean squared two-component displacement error divided by `abs(Us)^2`.
- Optimizer: AdamW, learning rate `1e-3`, betas `(0.9,0.999)`, epsilon `1e-8`, weight decay `1e-8`, AMSGrad false.
- Scheduler: cosine annealing for exactly 10,000 optimizer steps to `1e-5`; scheduler steps after each optimizer step.
- Determinism: deterministic PyTorch algorithms are mandatory; an unsupported nondeterministic operation fails validity.
- Checkpoint: only the final step-10,000 checkpoint may be evaluated or retained for the result.
- Producer evidence: every formal run records the clean Git commit, command, host, explicit GPU, paths, timestamps, checkpoint/prediction/reference hashes, and the required `/mnt/data2/drtao/.../<run_id>` roots in `RUN_RECEIPT.json`.

The machine-readable constants and exact reference hashes are in [stage1_contract.json](stage1_contract.json).

## Frozen final-checkpoint gates

Each valid run must pass all clauses:

| Gate | Threshold |
|---|---:|
| essential-BC maximum absolute error | `<= 1e-12` |
| mass-weighted displacement RMS / `abs(Us)` | `<= 1e-3` |
| native-Q4 strain relative L2 | `<= 1e-2` |
| native-Q4 mass-dual `rho_u` | `<= 1e-3` |
| reference, damage and metadata mutation | exact zero / identity |

The fit metrics and residual are reported separately. A run that fits displacement and strain but fails `rho_u` is a fixed-procedure joint-gate failure, not proof that the architecture cannot represent the field. The residual uses the admitted state-specific fixed damage, excludes prescribed boundary reactions, and performs no damage solve or history update.

## Authorization boundary

`CANDIDATE_TRAINING_AUTHORIZED=true` applied only to the frozen 12-run Stage 1 matrix at reviewed commit `769396f93ae5258eb984e1585d4274f7990afb11`. Attempt A stopped before its first optimizer step because the external dispatcher lacked the CuBLAS deterministic workspace setting and is retained as `INCONCLUSIVE`. A supplied-incident review allowed a launcher-only correction and a wholly fresh attempt without a new code review. Attempt B used fresh R016--R027 identities and `CUBLAS_WORKSPACE_CONFIG=:4096:8` and is complete. The fail-closed aggregate result is `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE` with architecture representability `UNRESOLVED`. Independent supplied-evidence review returned `EVIDENCE PASS` and required no numerical rerun. `SUPERVISED_CAPACITY_PASS`, Stage 2, route promotion, `FULL_FEM_REPRODUCTION`, and `QUALIFIED_FEM_TEACHER` remain unavailable or unauthorized. See [stage1_launch_record.md](stage1_launch_record.md), [stage1_result.md](stage1_result.md), and [stage1_evidence_review.md](stage1_evidence_review.md).
