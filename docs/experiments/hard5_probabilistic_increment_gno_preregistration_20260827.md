# Hard5 probabilistic increment GNO v1 preregistration

Status: `DRAFT_CODE_AND_REVIEW_ONLY`

Experiment ID: `hard5_probabilistic_increment_gno_v1_20260827`

User scope authorization: 2026-08-27, four-field increment model on the existing three Hard5 amplitudes. This does not waive code review, data-contract review, or Taobo release authorization.

## PIDL Experiment Gate

- Mechanism question: does direct one-cycle increment parameterization improve observation-conditioned t+1 prediction of `damage`, `alpha_bar`, fatigue `f`, and `log10(psi_raw)`, while learning a useful conditional error scale?
- Claim changed if success: direct-increment GNO is retained as the next processed-GRIPHFiTH surrogate representation and may support further uncertainty work.
- Claim changed if failure: keep the frozen absolute-state GNO as the diagnostic reference; do not add probabilistic or onset claims.
- Cheaper diagnostic first: completed three-seed disagreement maps, risk-coverage analysis, and train-fold onset analysis from the frozen `a220491` run.
- Minimal output asset: one per-fold/seed t+1 increment table, one probabilistic diagnostic table, selected native-cell field exports, and a final decision note.
- Code/producer alignment: Mac performs code/unit/forward-backward checks only; training is Taobo-only in a fresh run directory after exact-commit review and release authorization.
- Success criteria: the U0.12 development fold meets the fixed point-prediction gate below; uncertainty diagnostics are reported separately and do not rescue a failed point-prediction gate.
- Failure criteria: leakage, post-hit training origin, nonfinite value, incomplete provenance/archive, or failure of the fixed U0.12 point-prediction gate.
- Registry destination: this preregistration and one later result document under `docs/experiments/`; claim boundary remains processed-GRIPHFiTH imitation.
- Decision: implement and diagnose first; launch remains blocked pending exact-code review and release authorization.

## 1. Frozen data and split

- Dataset: `hard5_loao_fem_states_v1`.
- Dataset manifest SHA-256: `9267a102a38375ebc815404a5ae81b2d3b23622448b5b178a2c4c1a5696e202a`.
- Dataset hash-file SHA-256: `7bff035eaa618a7517335a3adb436e14d8bf606c6fa4e202497355518e82a55e`.
- Trajectories: U0.11, U0.12, U0.13 only.
- Split: three-fold leave-one-complete-Umax-trajectory-out.
- Inputs: the latest three archived cycle-peak states plus geometry, cell area and scaled Umax metadata. No cycle number, first-hit distance, confirmed cycle or future field is an input.
- Target: the next cycle-peak increment in all four archived state channels.
- Training origins are strictly before the training trajectory's first-hit. A target may equal first-hit; no post-hit origin is permitted.
- Normalization uses the two training trajectories only and gives each trajectory equal weight.

U0.12 remains a model-parameter holdout, but it is a development fold rather than a virgin scientific holdout because its fields have already been inspected. U0.11/U0.13 remain endpoint-extrapolation diagnostics. No calibrated cross-regime coverage claim is permitted from these three trajectories.

## 2. Model and output contract

- Native-mesh local/coarse GNO backbone, context 3, hidden width 96.
- One mean decoder returns four normalized residual locations.
- The mean state is the latest state plus the decoded increment, passed through the existing irreversible channel constraints.
- A separate scale decoder returns four bounded normalized Laplace log-scales using a smooth transform into `[-5, 2]`.
- There is no transition or onset head in v1. This isolates the increment-representation question.
- There is no equilibrium, phase-field, KKT, constitutive or PINO residual. `physics_loss_weight=0` and `physical_validation=false` remain mandatory.

## 3. Two-stage optimization

### Phase A: mean increment

- 3000 AdamW steps, learning rate `3e-4`, weight decay `1e-6`.
- t+1 only; no autoregressive rollout enters this experiment.
- Alternate first-hit-target and ordinary buckets. Within a bucket, select trajectory uniformly and then origin uniformly.
- Mean loss is the existing training-fold-scaled field loss: four constrained state channels, derived-active field, FEM-p99 support logits and edge-gradient error.
- Persistence prediction-gradient calibration is recomputed using only the two training trajectories for each fold.

### Phase B: conditional scale

- Freeze the complete backbone and mean decoder.
- Train only the scale decoder for 500 AdamW steps with the same hierarchical sampling contract.
- Minimize area-weighted Laplace negative log likelihood of the normalized increment residual around the frozen mean. The mean error is detached, so Phase B cannot change point predictions.
- The scale is an uncalibrated conditional-error model, not a posterior standard deviation.

Seeds are `[1, 2, 3]`; the frozen matrix contains three folds by three seeds, nine jobs.

## 4. Fixed evaluation

### Point prediction

For each legal held-out pre-hit origin, report area-weighted t+1 increment MAE separately for all four channels for:

1. probabilistic-increment GNO mean;
2. persistence, whose predicted increment is zero;
3. constrained-linear extrapolation.

The U0.12 development gate uses exactly origins c20, c40, c60 and c80, reduced first by median across those four origins within each seed, then median across the three seeds.

The point gate passes only if:

- GNO has lower increment MAE than persistence in at least three of four channels;
- GNO has lower increment MAE than constrained-linear in at least two of four channels; and
- no channel is more than 10% worse than persistence.

These fixed tolerances decide whether to retain the representation for another experiment; they do not promote a scientific or real-road uncertainty claim.

### Uncertainty diagnostics

For each channel and held-out fold report:

- Laplace NLL;
- nominal central 90% interval coverage and width, explicitly uncalibrated;
- area-weighted association between predicted scale and absolute increment error;
- area-weighted Pearson association between predicted scale and absolute increment error (zero if either weighted variance is zero);
- risk-coverage after sorting native cells by increasing predicted scale and retaining up to 100%, 90%, 75% and 50% of native-cell area;
- after all three seeds complete, ensemble location spread and total predictive variance `2 E[b^2] + Var(mu)`.

Cells and cycles are not independent replicates. Aggregate first within trajectory/seed; do not pool cells or overlapping cycles to create sample size or coverage claims. Uncertainty metrics cannot rescue a failed point gate.

## 5. Fixed selected origins and outputs

- U0.11: c20, c40, c60, c120.
- U0.12: c20, c40, c60, c80.
- U0.13: c20, c30, c45, c58.

Every job must write:

- `RUN_PROVENANCE.json`, `RUN_MANIFEST.json`, `LAUNCH_RECEIPT.json`;
- `final_model.pt`, `training_history.csv`;
- `heldout_increment_metrics.csv`, `heldout_uncertainty_metrics.csv`;
- `selected_increment_fields.npz`.

The aggregate analyzer must fail closed on nonfinite values, wrong folds/seeds, training-ID complement mismatch, wrong origins, unexpected payloads, dataset/code identity mismatch or incomplete receipts.

## 6. Stop rules

- Any held-out state, event metadata or metric enters normalization, optimization, scale fitting, sampling thresholds or model selection.
- Any post-hit origin enters training.
- A threshold, loss weight, origin set, baseline or reduction is changed after results are seen.
- U0.12 is called a virgin onset holdout or any 80%/90% coverage is called calibrated.
- Spatial cells or cycles are treated as independent experimental replicates.
- The output is described as physical truth, FEM uncertainty, a posterior, PINO physics or real-road prediction.
- Exact-commit independent review or release authorization is absent.

## 7. Pre-launch status

`BLOCKED_PENDING_EXTERNAL_ARCHITECTURE_ADVICE_EXACT_COMMIT_REVIEW_AND_RELEASE_AUTHORIZATION`.

The model, runner, fail-closed aggregate analyzer and matrix-lock draft are implemented. No Taobo launch is allowed until the experiment-gate external architecture advice is recorded, the resulting exact clean commit is independently reviewed, and an owner release authorization binds that commit, matrix hash and all nine jobs.
