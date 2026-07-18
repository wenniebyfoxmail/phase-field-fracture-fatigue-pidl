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
