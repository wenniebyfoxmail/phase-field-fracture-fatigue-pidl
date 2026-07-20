# Temporal architecture study protocol (sealed 2026-07-18)

## Scientific status

This study is a **within-trajectory temporal diagnostic**, not a trajectory-generalisation benchmark. The available FEM package contains one compatible c1-c89 trajectory. In addition, c77-c89 and c89 have already informed prior operator decisions, so this interval is a reused evaluation benchmark rather than a statistically virgin locked test. No result from this study is assimilation-eligible.

The machine-readable protocol is `SENS_tensile/temporal_architecture_protocol_v1.json`. Its dataset hash, split, features, parameter target, optimisation budget, model widths, seeds, and selection metric are sealed before remote training.

## Leakage boundary

- Normalisation: c1-c67 only.
- Training: every history window and every rollout target lies wholly within c1-c67.
- Architecture, checkpoint, and context selection: c67-origin recurrent rollout through c76 only.
- Evaluation: c76-origin c77-c89 rollout, reported as reused evaluation.
- Twenty-cycle diagnostic: c69-c89, reported as reused because c69-c76 belongs to the validation interval.
- Observation reset: c87 raw/full point resets and a true-history c87 restart are oracle diagnostics.
- Forbidden inputs: cycle index, `cycle/89`, cycle-to-failure, or any future loading value.
- Loading metadata ablation is structurally unavailable in the sealed dataset and must not be simulated with cycle number.

## Architecture and fairness

All core models use the same four state channels, geometry, graph/coarse graph, latest-state fine message passing, history-to-coarse area pooling, mesh decoder, irreversible directional update, loss, optimiser budget, split, contexts, and seeds. The temporal block is the only core substitution. Temporal processing is performed over time independently for each of about 983 coarse tokens; there is no global attention over 86,408 mesh elements.

The six matched models are Markov residual MLP, GRU, LSTM, TCN, causal temporal-only Transformer, and a stable diagonal linear SSM. The latter is explicitly not Mamba. Total trainable parameter counts are 326k-332k around the 329k reference, with the same encoder and decoder. Training time, peak CUDA memory, and recurrent inference seconds per cycle are recorded per run.

## Staged execution

1. Remote two-step smoke for every family; this is a code/cost check and produces no scientific evidence.
2. Core stage 1: Markov, GRU, and diagonal SSM, seeds 1/2/3.
3. Core stage 2: LSTM, TCN, and Transformer, seeds 1/2/3, only after the implementation gate passes. It is required before answering the Transformer comparison.
4. Ablations use validation-only selection: context length, graph versus pointwise, parameter matching, teacher-forced versus autoregressive, one-step versus multi-step loss, and observation reset. Loading metadata is recorded unavailable. Material one-seed ablation signals are repeated with all three seeds.

The reused c77-c89 interval is opened only after each run has selected its checkpoint and context from c67-c76. It cannot change architecture, hyperparameters, or stopping.

## Decision rule

A temporal family is useful only if multiple seeds improve validation rollout and the reused evaluation is directionally consistent, with better FEM-like active support/localisation rather than diffuse smoothing. Whole-domain MSE or event timing alone cannot pass the gate. Seeds quantify optimisation stability only; without additional physical trajectories, Transformer or SSM generalisation remains unproved.

## Completed result

The staged campaign completed 18 core runs (six families × three seeds) and
14 formal ablation runs. The final package validator passed all expected runs
and eight analysis assets.

- Transformer achieved the best c67-c76 validation composite
  (`0.5493 +/- 0.0740`), followed by diagonal SSM (`0.5654 +/- 0.0751`).
- Neither improved mean teacher-forced next-cycle active log MAE over Markov.
- Transformer modestly improved c76-origin h5/h10 error over Markov, but TCN
  was stronger at h10-h20.
- All families missed the c87 raw-driver redistribution. At c89, FEM-p99 IoU
  was about `0.01` and support-area ratio about `97`, which is a diffuse
  mechanism failure.
- A c87 observation reset restored c89 IoU to `0.891-0.956`, diagnosing
  missing transition/state information rather than successful free rollout.
- Parameter-matched ablations support the combined value of graph encoding,
  autoregressive exposure, and multi-step loss; selected Transformer contexts
  were not stable across seeds, so the gain cannot be assigned to temporal
  memory alone.

Final decision: **do not promote Transformer or diagonal SSM**. Retain the
implementation as a quarantined within-trajectory diagnostic. Do not enlarge
the single-trajectory architecture sweep; require multiple compatible FEM
trajectories and a newly sealed trajectory-held-out test before revisiting a
generalisation claim.

## 2026-07-20 matched multi-origin correction

The old `current_multiscale` operator is no longer a formal baseline. Its
spatial features include `target_cycle/89`, `sin(2*pi*phase)`, and
`cos(2*pi*phase)`, which reveal absolute cycle and the complete trajectory
length. It is retained only as a historical, cycle-conditioned, single-seed
reference. The three-seed Markov graph model is the formal multiscale control.

All 18 core checkpoints were re-evaluated without retraining from identical
observed FEM histories at c76, c79, c82, and c84, for 11 same-regime h1--h3
forecasts ending no later than c86. Pooled three-seed means are:

| family | active log-MAE | FEM-p99 IoU | support ratio |
|---|---:|---:|---:|
| Markov graph | 0.0905 | 0.6842 | 1.034 |
| GRU | 0.0900 | 0.7020 | 1.004 |
| LSTM | 0.0879 | 0.7007 | 0.986 |
| TCN | 0.0873 | 0.6882 | 1.015 |
| Transformer | **0.0871** | **0.7139** | 1.012 |
| diagonal SSM | 0.0911 | 0.7109 | 1.021 |

Transformer and diagonal SSM improve pooled IoU over same-seed Markov in 3/3
seeds, but their descriptive n=3 paired intervals both cross zero:
Transformer +0.0296 [-0.0379, 0.0972], SSM +0.0267 [-0.0447, 0.0980].
Transformer's pooled MAE difference is -0.0034 [-0.0224, 0.0155]. Thus the
short-horizon localisation signal is directional, not a stable proof that
temporal memory helps.

All families also received the identical full c87 reset, raw-only c87 reset,
and sparse c87 assimilation state. Free c89 rollout remains a universal
transition failure (IoU about 0.01, support ratio about 97). The shared sparse
c87 state restores c89 IoU to 0.873--0.932, confirming conditional
post-transition propagation but not autonomous transition forecasting.

Correct attribution: under the new matched graph and autoregressive training
framework, several models retain pre-transition localisation longer than the
historical cycle-conditioned multiscale operator. The additional benefit of
temporal memory remains unstable. Full evidence is in
`local_archive/.../temporal_architecture_study_20260718/multi_origin_reanalysis_20260720/analysis/decision.md`.
