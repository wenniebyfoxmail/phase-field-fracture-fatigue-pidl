# Reality Transition-Model Evidence Matrix

**Question**: should the reality-facing predictor use direct FEM, reproduce FEM with a surrogate, or bypass FEM with observation-only/empirical models?

The current evidence does not support one global winner because available results use different trajectory families. This matrix preserves those differences instead of building an invalid numeric leaderboard.

| transition strategy | implemented path | strongest current evidence | missing evidence | current role |
|---|---|---|---|---|
| Observation-only grouped ridge | `run_m2s_next_stage_feasibility.py` | leave-one-trajectory-out code exists; legacy five-Umax scalar suite shows visible-damage RUL is weak and hidden state-driver reductions help | no calibrated uncertainty; hidden FEM features are not deployable observations; not evaluated on the locked reality observation contract | data-only sanity baseline |
| Local observable-growth particles | `observable_growth_baseline.py` | now evaluated with exactly the same crack-tip observation and holdouts as direct FEM; emits RUL/future-tip distributions | constant local rate misses acceleration; current cadence family is not physical generalisation | probabilistic no-physics baseline |
| Direct FEM trajectory-library posterior | `reality_assimilation.py` | sequential weights, RUL/crack-tip distribution, right censoring, inverse-parameter posterior, missing/noisy observations, CV/DIC/AE operators | third compatible physical trajectory and paired sensor calibration | **primary reference transition model** |
| Historical measured trajectory library | `source_kind=observation_csv` in `reality_assimilation.py` | implemented and integration-tested with `reality_obs_v1`; uses the same sequential posterior and holdout metrics without FEM hidden state | sufficient compatible completed asset histories with failure/censor labels | preferred empirical alternative when field history is available |
| Online direct FEM re-solve | Windows-FEM/GRIPHFiTH producer | highest-fidelity reference path in principle | computational workflow for per-asset updating, uncertain parameters, and repeated posterior propagation | expensive reference / selective update |
| PIDL as transition model | existing PIDL runners and archives | scalar event timing can align in selected cases | active-driver/process-zone/history co-location remains wrong; no same observation-contract physical holdout | diagnostic candidate, not promoted |
| Single-trajectory temporal mesh operator | `fem_mechanism_operator.py` | coherent graph/state constraints and recurrent field metrics; unit contract passes | only one c1--c89 trajectory, no physical conditioning/uncertainty/checkpoint/unseen-trajectory test | quarantine / tooling-only |
| Multi-trajectory FEM surrogate | not yet approved | architecture ingredients exist in the single-trajectory prototype | externally reviewed dataset/split/conditioning design plus compatible trajectories | pending evidence, no training launch |
| Empirical fatigue/crack-growth law | legacy scalar reductions provide possible inputs | interpretable and cheap candidate | locked load-spectrum definition, crack-geometry factor, censored likelihood, uncertainty and same holdout protocol | required baseline before model promotion |

## Decision

1. Use direct FEM library assimilation as the present reference implementation because it already supports uncertainty, inverse parameters, real observations, and censoring without requiring PIDL to reproduce FEM fields. As completed field histories accumulate, run them through the same engine as an empirical trajectory library rather than forcing them into phase-field labels.
2. Keep both the local observable-growth particles and existing grouped ridge as lower-cost baselines. The local model now shares the exact tip observation protocol; grouped ridge still needs rerunning on compatible physical trajectories.
3. Add an empirical fatigue law as an interpretable baseline only after load-spectrum and failure semantics are locked; do not infer Paris-law parameters from mixed physics families.
4. Do not train/promote the mesh surrogate from the current single trajectory. Its next legitimate test is leave-one-physical-trajectory-out, not a later-cycle holdout.
5. PIDL or a surrogate replaces direct FEM only if it matches the same RUL CRPS/coverage, future crack geometry, inverse-parameter recovery, and FEM-centred field-mechanism gates at materially lower cost.

## Common comparison package required

Every transition model must eventually emit the same objects for each inspection:

- posterior RUL support/weights and 5/50/95% interval;
- future crack-tip/geometry distribution at a fixed horizon;
- posterior over declared load/material/fatigue/precrack/environment parameters;
- model-family weight and uncertainty contribution;
- provenance, physics family, observation-model version, and censoring semantics.

The headline split is by compatible physical trajectory. Cycle slices, element splits, cadence variants, and mixed BC/constitutive families cannot serve as substitutes.
