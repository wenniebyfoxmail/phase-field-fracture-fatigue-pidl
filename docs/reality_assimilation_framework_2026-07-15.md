# Reality-Facing Crack Assimilation Framework

**Status**: implemented analysis framework; current local FEM library is a code/semantics gate, not deployment evidence.

## Objective

Predict future road/infrastructure crack geometry and remaining life from data that can actually be collected. Phase field, FEM, PIDL, reduced models, and empirical fatigue laws are candidate transition models, not the objective. The deployed object is a sequential posterior over physical state and model uncertainty:

```text
latent state x_t --transition model--> x_(t+1)
       |                                |
observation model H                 forecast distribution
       |                                |
image / 3D / strain / AE / load / environment / maintenance
```

The phase-field damage and fatigue-history variables may remain latent. Real observations constrain their posterior through an explicit observation model; computer vision is not expected to manufacture phase-field labels.

## Implemented first rung

- `SENS_tensile/reality_assimilation.py`
  - defines observable, synthetic-proxy, and oracle-only channels;
  - converts cycle-resolved FEM handoffs into a locked observation table;
  - performs sequential Bayesian model averaging over a direct FEM trajectory library;
  - predicts an RUL posterior and future crack-tip distribution;
  - reports MAE, RMSE, CRPS, 90% coverage/width, and future crack-tip MAE.
  - accepts either cycle-resolved combined handoffs or sparse per-inspection MAT keyframes on a shared mesh.
  - accepts completed `reality_obs_v1` laboratory/field histories as empirical transition trajectories, without FEM or phase-field labels.
  - retains right-censored trajectories through an explicit survival lower bound plus auditable tail prior.
  - maps FEM mechanical/damage-activity proxies into versioned DIC/strain and AE measurement features, with calibrated residual uncertainty.
- `SENS_tensile/run_reality_assimilation_benchmark.py`
  - runs leave-one-trajectory-out sensor-tier ablation;
  - writes predictions, summary, sensor observability catalog, figure, manifest, and `decision.md`;
  - is analysis-only and must not enter a PIDL training loop.
  - accepts `--trajectory-manifest` so combined full-cycle handoffs and sparse keyframe trajectories can coexist in one library.
  - runs an independent package validator before reporting success; the validator checks probability ordering, coverage bounds, training prohibition, physics-family/quarantine consistency, parameter identifiability, and sensor-approval semantics.
- `SENS_tensile/run_reality_assimilation_inference.py`
  - validates a calibrated, versioned observation sequence;
  - updates the FEM-library posterior after each real/laboratory inspection;
  - writes RUL/crack-tip posterior intervals and per-model weights without requiring future ground truth.
- `SENS_tensile/build_vision_observation_table.py`
  - converts registered crack-probability masks into physically scaled crack-tip, area, and width observations;
  - records a 0.5-to-0.9 segmentation-threshold uncertainty band;
  - keeps raw RGB segmentation outside the assimilation contract so the CV model can be replaced independently.
- `SENS_tensile/calibrate_reality_sensor_observation_model.py`
  - fits transparent DIC/strain and AE observation mappings from paired FEM/laboratory features;
  - estimates residual uncertainty with leave-one-calibration-group-out predictions rather than in-sample residuals;
  - writes a calibration report, hashes, manifest, and an unapproved model candidate for independent review.

Observation tiers are cumulative:

1. `tip_only` — registered visible crack-tip position only; used for same-observation transition-model comparison.
2. `vision_only` — calibrated crack geometry.
3. `vision_plus_load` — geometry plus known loading.
4. `vision_load_mechanical` — adds a synthetic mechanical-energy proxy; replace with DIC/strain observation likelihood.
5. `vision_load_mechanical_activity` — adds synthetic damage/history activity; replace with calibrated AE features.
6. `oracle_hidden_state` — includes FEM fatigue history/degradation/active driver and is never a deployable tier.

Two additional deployable contracts separate measured sensor features from FEM proxies:

- `vision_load_dic` consumes `dic_tip_response` and `dic_strip_response`;
- `vision_load_dic_ae` additionally consumes `ae_log_event_rate` and `ae_log_energy_rate`.

Their observation operator is a versioned JSON file. `docs/templates/reality_sensor_observation_model_template.json` is intentionally marked `synthetic_only`; real/laboratory inference rejects it until it is replaced by paired-data calibration with non-zero residual uncertainty. Linear mappings are the first transparent baseline, not an assertion that the final DIC/AE physics is linear.

## Experiment gate

1. **Mechanism question**: which observable sensor tier first makes future crack geometry and RUL identifiable?
2. **Claim change**: a tier is promoted only if it improves proper probabilistic scores and calibrated coverage on physical-trajectory holdout.
3. **Cheaper check**: use existing FEM exports and direct library assimilation before producing new simulations or laboratory tests.
4. **Minimal output**: one decision note plus the posterior prediction and sensor-ablation tables.
5. **Registry**: keep this as `framework-validation`; do not use it to claim closure of the forward PIDL field mechanism.

## Required next data package

The current strict handoffs vary numerical cadence at one `Umax`; this is not sufficient physical diversity. The next producer export must vary at least:

- load amplitude/spectrum;
- material or fatigue parameters;
- initial crack/precrack geometry and severity;
- one environmental degradation proxy;
- failure and censored trajectories.

Each trajectory must include cycle/load index, geometry/mesh, damage, raw mechanical response, fatigue history and degradation for synthetic-oracle auditing. Deployment features must be generated only through the declared observation model.

Before any new solve, Request 25 in `docs/handovers/windows_fem_inbox.md` asks Windows-FEM to recover/re-export the already completed `Umax=0.08...0.12` FEM family. This is archive/export only. If three or more physical-load trajectories survive with full fields, they become the next benchmark library; if only scalar summaries survive, they remain useful RUL baselines but cannot validate spatial observation operators.

The Mac recovery audit has already restored usable sparse keyframes for `Umax=0.10` (`c1/80/140/170`) and `Umax=0.11` (`c1/55/95/117`), with all four required element fields on the shared 77,730-element mesh. `trajectory_from_keyframes()` loads them directly and normalizes damage/history activity by the actual inspection gap. A third physical trajectory is still required before leave-one-load-out evaluation; two trajectories are not enough to distinguish generalisation from pairwise matching.

The starter library manifest is `docs/templates/reality_trajectory_manifest.csv`. Add the recovered third trajectory, then pass it to the benchmark with `--trajectory-manifest`. Every row must declare a `physics_family`: one identifier for trajectories sharing boundary conditions, constitutive/fatigue semantics, state definition, and compatible failure rule. Scientific benchmarking and real inference require exactly one family. `--allow-mixed-physics-family` exists only for tooling stress tests and automatically quarantines the result. Columns prefixed `parameter_` declare candidate transition-model parameters (for example fatigue threshold, precrack length, or environment index). Sequential output contains their posterior mean and 5/50/95% quantiles; the benchmark writes a separate parameter-recovery table and refuses to label a constant parameter as identifiable. A right-censored row carries `censored=true`, a blank `failure_cycle`, and a known `censor_cycle`; it is retained as a candidate library member but is not used as an exact-RUL holdout.

Historical laboratory/road histories use `docs/templates/reality_historical_trajectory_manifest.csv` with `source_kind=observation_csv` and a declared `observation_tier`. Each CSV must already satisfy `reality_obs_v1`, share one coordinate/registration chain, contain its declared failure/censor terminal inspection, and use a compatible asset/failure `physics_family`. Run only tiers present in those histories, for example `--tiers tip_only` or `--tiers tip_only,vision_only`. This makes the sequential library model source-agnostic: candidate trajectories may come from direct FEM or from historical measured evolution, but mixed semantics remain forbidden.

For a censored candidate, the RUL support starts at the survival lower bound `censor_cycle - current_cycle` and adds an exponential tail. The mean tail is explicit (`--censor-tail-scale`, default 50 cycles), its posterior contribution is reported as `censored_posterior_mass`, and its numerical quadrature resolution is recorded in the run manifest. This tail is a declared prior, not learned evidence. Any scientific result using censored trajectories must repeat the benchmark over plausible tail scales and report whether the sensor-tier conclusion changes.

## Promotion criteria for the laboratory rung

A sensor tier may determine the laboratory instrumentation only when:

- it beats `vision_plus_load` on held-out physical trajectories in CRPS and future crack-tip MAE;
- empirical 90% RUL coverage is plausibly calibrated, not achieved by an unusably wide interval;
- improvement survives sparse/noisy/missing observations;
- no oracle-only state enters the deployable feature set;
- the same locked metric code evaluates data-only, empirical fatigue, direct FEM, and surrogate-FEM baselines.

The first laboratory test should then collect synchronized load-displacement, calibrated repeated images/full-field DIC, and preferably localized AE. Its purpose is to calibrate the observation likelihood and test identifiability, not to produce another scalar `N_f` match.

## Real/laboratory observation contract

The template is `docs/templates/reality_observation_template.csv`. Required metadata are observation-space version, asset/inspection IDs, UTC timestamp, strictly increasing cycle or equivalent-load index, coordinate frame, and one registration chain. `reality_obs_v1` means raw sensor data have already passed through a documented observation model into the same units/semantics as the selected tier.

Do not place raw pixels or waveforms directly in this table. A maintenance event currently forces the sequence to be split because posterior state reset is not implemented; the validator rejects such rows instead of silently treating repair as natural crack evolution.

### Vision/CV entry point

`docs/templates/reality_vision_inspection_manifest.csv` describes already registered probability masks, physical pixel sizes, origins, load index, and registration provenance. `build_vision_observation_table.py` maps each mask into `reality_obs_v1`: the `p>=0.9` support defines the crack-tip/high-confidence area, and `p>=0.5` defines visible support/width. Their difference is retained as a threshold-sensitivity diagnostic. This is a replaceable observation operator, not phase-field supervision: a classical thresholding pipeline, U-Net, foundation segmentation model, or manual annotation may all produce the mask if their calibration and registration are recorded.

For DIC/AE tiers, `run_reality_assimilation_inference.py` also requires `--sensor-model-json`. Each predicted sensor channel declares its FEM source feature(s), coefficients, offset, and residual standard deviation. The library is projected into this sensor space before posterior updating; missing values are skipped channel-by-channel, and measurement variance is combined with the library likelihood scale. A `synthetic_only` calibration is accepted by the benchmark for stress testing but rejected by real/laboratory inference.

Paired calibration data use `docs/templates/reality_sensor_paired_calibration_template.csv`. `calibration_group` must identify independent specimens/assets/sessions, not random rows from one trajectory. The calibration command fits on all but one group and predicts the held-out group to estimate each channel's `sigma`. Its output always starts with `approved_for_inference=false`; real inference rejects it until an independent review confirms group independence, coordinate registration, residual structure, extrapolation range, and acceptable uncertainty.

## First local execution result

The analysis package `_analysis_reality_assimilation_20260715/` was generated from the three available strict cycle-resolved handoffs (`nstep2/3/10`) with five-cycle inspections and a five-cycle crack-tip forecast horizon.

| observation tier | RUL MAE | CRPS | 90% coverage | future-tip MAE |
|---|---:|---:|---:|---:|
| vision only | 0.644 | 0.489 | 0.667 | 0.00197 |
| vision + load | 0.644 | 0.489 | 0.667 | 0.00197 |
| vision + load + mechanical proxy | 0.736 | 0.625 | 0.667 | 0.00233 |
| plus damage-activity proxy | 0.736 | 0.625 | 0.667 | 0.00233 |
| DIC observation contract, synthetic identity bridge | 0.736 | 0.625 | 0.667 | 0.00233 |
| DIC + AE contract, synthetic identity bridge | 0.736 | 0.625 | 0.667 | 0.00233 |
| hidden-state oracle | 0.410 | 0.368 | 0.667 | 0.00178 |

These numbers validate execution and semantics only. All handoffs use `Umax=0.12`, and failure cycles span only 69--70. The unchanged and under-calibrated coverage plus the negative mechanical-proxy result mean that no sensor tier is scientifically promoted. The next discriminating asset is a physically diverse trajectory library, not a more complex estimator on these same three paths.

A separate deterministic stress run is stored in `_analysis_reality_assimilation_noise_stress_20260715/`. It uses `docs/templates/reality_sensor_observation_model_synthetic_stress.json`, approximately 10% proxy-scale DIC/AE noise, 25% random sensor missingness, and seed 42. DIC-only RUL CRPS is 0.625 and DIC+AE CRPS is 0.630, versus 0.489 for vision+load; coverage remains 0.667. This verifies the missing/noisy observation path and supplies a regression asset. It is further negative evidence against promoting the present proxies on the cadence-only library, not evidence against real DIC or AE.

The inverse-parameter table correctly marks current `Umax` recovery as non-identifiable because every strict trajectory has the same `Umax=0.12`. This is a guardrail: zero error on a constant parameter is not inverse-problem evidence. Parameter recovery can only be scored after the physically diverse trajectory family is restored.

## Same-observation data baseline

`SENS_tensile/observable_growth_baseline.py` supplies a probabilistic observation-only baseline. It sees only registered crack-tip positions and inspection intervals. A tempered particle posterior tracks a non-negative local crack-growth rate; it uses no FEM damage/history/energy state and is explicitly not labelled as a Paris law.

On the current cadence-only strict library, using exactly `crack_tip_x_d09` in both models:

| transition prior | RUL MAE | CRPS | 90% coverage | future-tip MAE |
|---|---:|---:|---:|---:|
| full FEM trajectory library, tip likelihood only | 0.644 | 0.489 | 0.667 | 0.00195 |
| local observable-growth particles | 26.8 | 18.9 | 0.422 | 0.00824 |

This does not establish FEM generalisation: the FEM library contains almost the same complete transition curve as the held-out cadence variant. It shows that the strong tip-only result comes from a full transition prior, not from the current image alone. The local-rate model has extremely wide early uncertainty before extension and then misses the strongly accelerating propagation regime. This supports collecting load/strain/AE and testing richer transition models; it is not a reason to treat simple linear crack growth as a serious deployment competitor.

## Mixed-provenance quarantine stress

The only locally available third physical amplitude is a reverseBC `Umax=0.12` trajectory whose physics/state family is not compatible with the legacy FEM5 `Umax=0.10/0.11` keyframes. The benchmark now rejects this mixture by default. An explicit tooling-only run with `--allow-mixed-physics-family` is stored in `_analysis_reality_assimilation_mixed_provenance_20260715/` and records `claim_quarantined=true`.

That deliberately confounded library produces vision+load RUL MAE `41.2` cycles, CRPS `41.7`, and 90% coverage `0.049`; the hidden-state oracle is worse. This is not evidence against vision, FEM, or hidden-state observations. It is evidence that incompatible BC/constitutive/state semantics cannot be treated as useful physical diversity.

## FEM-surrogate status

The existing temporal mesh-operator prototype is audited in `docs/fem_surrogate_transition_gate_2026-07-15.md`. It uses a single c1--c89 FEM trajectory with within-trajectory cycle splits and lacks physical parameter conditioning, uncertainty, a trained checkpoint, and unseen-trajectory validation. Dataset/training manifests now force tooling-only/quarantine semantics, and the runner requires an explicit diagnostic-only acknowledgement. It cannot enter the assimilation library until a reviewed multi-trajectory design passes the same observation, RUL, crack-geometry, and FEM-centred mechanism gates as direct FEM.
