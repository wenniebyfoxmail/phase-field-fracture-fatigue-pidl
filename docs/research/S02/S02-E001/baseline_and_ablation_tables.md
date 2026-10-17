# Baseline and ablation tables

These tables distinguish already observed evidence from preregistered future
rows. Blank values are `not_evaluated`, not zero.

## Existing evidence carried into S02-E001

| Tier | Control/challenger | Population | Warning evidence | Rollout evidence | Status |
|---|---|---|---|---|---|
| A | persistence | three cross-Umax Hard5 trajectories | not evaluated as calibrated warning | strong adjacent-state control | retained |
| A | two-frame secant | three cross-Umax ordinary h1/h2 | no warning probability | active log-MAE reduction vs persistence: U0.11 14.1%/33.8%; U0.12 17.2%/41.6%; U0.13 41.1%/48.2% | strongest transparent short-horizon control; transition topology unproved |
| A | matched Markov graph | one reused c1-c89 trajectory, observed-origin h1-h3 | terminal c87/c89 transition missed | active MAE 0.0905; FEM-p99 IoU 0.6842; support ratio 1.034 | within-trajectory diagnostic |
| A | Transformer | same matched population | terminal transition missed | active MAE 0.0871; IoU 0.7139; support 1.012; seed interval crossed zero vs Markov | no promotion |
| A | diagonal SSM | same matched population | terminal transition missed | active MAE 0.0911; IoU 0.7109; support 1.021 | no promotion |
| A | all temporal families, autonomous c76 to c89 | one trajectory | failed at c87/c89 | c89 IoU about 0.01; support ratio about 97 | negative transition stress |
| A | c87 observation reset | same one trajectory | not autonomous warning | sparse/full/raw reset restored c89 IoU roughly 0.831-0.956 | supports assimilation/state-information interpretation only |
| B | persistence | six LTPP frozen future-time transitions | no regime-warning ontology | length MAE 7.0543 m; buffered F1 0.4333; new-geometry error 1.6018 m2 | honest road point control |
| B | local-tip extrapolation | same six future-time transitions | no regime warning | F1 0.4368; length MAE 7.8401 m; new-geometry error 1.6847 m2 | negative |
| B | hierarchical state-space | leave-one-section-out, six sections | no frozen regime-warning evaluation | length error +15.63% and new-geometry error +6.31% vs persistence; 0/6 joint wins; nominal-90% coverage 0.9355 | reliability negative; uncertainty diagnostic only |

## Mandatory baseline result table for the first admissible run

| Tier | Fold | Model | Independent trajectories | h | at-risk origins | event positives | AP | recall | FPR | false alarms/trajectory | median lead intervals | Brier | calibration slope | field/geometry score | uncertainty score | pass |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A/B | each LOTO fold | persistence |  | 1/2/3 |  |  |  |  |  |  |  |  |  |  |  |  |
| A/B | each LOTO fold | secant |  | 1/2/3 |  |  |  |  |  |  |  |  |  |  |  |  |
| A/B | each LOTO fold | CUSUM |  | 1/2/3 |  |  |  |  |  |  |  |  |  |  |  |  |
| A/B | each LOTO fold | discrete-time hazard |  | 1/2/3 |  |  |  |  |  |  |  |  |  |  |  |  |
| A/B | each LOTO fold | matched Markov graph |  | 1/2/3 |  |  |  |  |  |  |  |  |  |  |  |  |

## Preregistered ablations

Run only after the full transparent-control table is complete.

| Ablation | Comparison | Question | Allowed interpretation |
|---|---|---|---|
| no transition head | matched propagator with/without warning coupling | does explicit transition supervision improve autonomous transition fields? | architecture-local incremental value |
| no regime conditioning | one propagator versus pre/post-regime propagators | does switching improve held-out rollout without oracle labels? | held-out family only |
| no assimilation | free rollout versus causal observation reset | how much error is corrected by new observations? | observation value, not autonomous skill |
| geometry only | Tier-B geometry versus geometry+forcing | do causal road covariates add held-out value? | only for fully joined channels |
| remove mechanics | full Tier B versus no FWD/strain/AE | does sparse mechanics add value? | no causal mechanism claim without variation/identifiability |
| remove WIM | full Tier B versus no load history | does observed load add forecast value? | dataset-specific increment |
| remove environment | full Tier B versus no temperature/moisture | does environment add forecast value? | requires actual moisture, not humidity substitution |
| oracle Tier A | hidden fields versus road observables on aligned state pairs | quantify observability gap | diagnosis only; never deployment evidence |

## Table integrity rules

- Report folds and trajectories before pooled rows.
- Do not treat seeds, nodes, elements, windows or horizons as independent roads.
- Mark unavailable metrics `not_evaluable`; do not impute missing PIDL/road states.
- Keep same-regime, autonomous transition, post-transition reset and rolling
  assimilation in separate blocks.
