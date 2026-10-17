# Preregistered protocol v1

**Experiment:** S02-E001  
**Freeze date:** 2026-08-27  
**Execution authorization:** none  
**Target:** real-road crack forecasting; synthetic FEM is a diagnostic tier

## 1. Estimands

At observation origin `t`, define a causal state `O_<=t` containing only values
available by the origin timestamp.

1. **Transition warning:** for each horizon `h in {1,2,3}` estimate
   `p_h(t) = P(T_event in (t, t+h] | O_<=t)`. A trajectory contributes origins
   only while at risk. Post-event origins are not negatives.
2. **Regime-conditioned propagation:** estimate the next state distribution
   `p(X_(t+1) | X_t, R_t, O_<=t)` and recursively roll out to h1-h3 and beyond.
3. **Assimilated rollout:** when an observation arrives, update the state using
   only that observation, then restart the forecast. Report free and assimilated
   forecasts separately.

For irregular road observations, `h` means the next observation interval. The
actual elapsed time, accumulated WIM/ESAL exposure, temperature and moisture
integrals over completed intervals are causal covariates. Target interval
duration or forcing unavailable at issue time must not enter an operational
forecast; an explicitly declared scenario forecast is a separate estimand.

## 2. Event and regime semantics

Each trajectory must freeze, before model fitting:

- `state_time`: timestamp/cycle and loading branch represented by every state;
- `event_predicate`: causal observable or qualified simulation predicate;
- `first_detect`: first state satisfying the predicate;
- `confirmation`: optional later evidence, never substituted for first detect;
- `regime`: pre-transition, transition interval, post-transition, or censored;
- maintenance/reset and missing-observation semantics.

Tier A uses the already frozen connected right-boundary first-detect predicate;
confirmed cycles are metadata only. Tier B requires a road-observable ontology,
for example first adjudicated new connected component, branching/area-growth
change, pothole conversion, or maintenance reset. The exact ontology and
minimum detectable change must be frozen using development assets only.

P0 and T3 are not accepted as trajectory identifiers until each resolves to a
unique manifest row, source hash or commit identity, state convention, loading
branch, first-detect predicate, and censoring status. A label match alone is not
state alignment.

## 3. Input tiers

### Tier A — simulation hidden fields

- registered mesh geometry and area;
- current/past `d`, `alpha_bar`, fatigue degradation `f`, and undegraded/raw
  tensile driver;
- known past loading and current configuration flags.

Tier A is an oracle/mechanism diagnostic. It cannot support a road-observable
or physical-truth claim.

### Tier B — road-observable inputs

- registered crack geometry from image/3-D/distress maps;
- FWD or stiffness, sparse strain and/or AE;
- WIM/traffic load history available at issue time;
- temperature, rainfall/moisture, structure/material metadata;
- maintenance/reset and censoring records.

Phase-field damage/history/driver fields, future surveys, target-derived masks,
future loads/weather, final lifetime and event distance are prohibited.

## 4. Split and leakage firewall

- Primary split: leave one complete trajectory/physical asset out.
- Road claim: a held-out asset contributes no frames, preprocessing statistics,
  thresholds, topology templates, calibration residuals, or model selection.
- Tier-A factorial claim: hold out the complete factorial trajectory. All four
  share geometry/material/Umax and are not four independent roads.
- Nested selection: tune hyperparameters and thresholds inside training
  trajectories only. The outer held-out trajectory is opened once.
- Normalization, CUSUM reference statistics, hazard baseline, graph transition
  probabilities, conformal/calibration residuals and regime definitions are
  training-fold only.
- Windows may not cross split, event-reset, maintenance, missing-identity, or
  incompatible loading-branch boundaries.
- No cycle/random-frame/node/cell split. Seeds are optimization repeats, not
  scientific replicates.
- Event-aligned stress panels are labelled retrospective and are never the only
  evaluation population.

## 5. Transparent controls in mandatory order

1. **Persistence:** `X_(t+h)=X_t`; warning probability is the training-fold
   prevalence conditional on current declared regime, never held-out prevalence.
2. **Two-frame secant:** projected extrapolation from `X_t-X_(t-1)`; use the
   same physical bounds and registered domain as every propagator.
3. **CUSUM/change point:** training-fold standardized innovations from causal
   geometry/stiffness/strain/AE channels; threshold selected inside the inner
   fold to a frozen false-alarm budget. No future-centred smoothing.
4. **Discrete-time hazard:** regularized complementary-log-log or logistic
   hazard with explicit right censoring, interval duration/exposure and
   training-fold-only features. Report coefficients and missingness terms.
5. **Matched Markov graph:** same state channels, graph, context, decoder,
   projection, optimization budget and seeds used for neural comparisons; no
   cycle/final-life/phase proxy. Regime probabilities are inferred, not fed as
   truth at inference.

Only after all five controls have frozen, complete held-out outputs may one
neural switching-state model be compared. TCN and Transformer are later
challengers, not simultaneous rescue arms.

## 6. Evaluation populations and metrics

### Transition warning

- all legal at-risk origins, overall and by h1/h2/h3;
- event-aligned diagnostic panel, labelled retrospective;
- precision-recall curve and average precision;
- recall/sensitivity at a training-selected operating point;
- false alarms per trajectory and per observation-year/cycle exposure;
- earliest correct warning lead in intervals and physical time/load exposure;
- Brier score and reliability diagram; calibration intercept/slope when
  estimable;
- censoring-aware counts and the number of independent trajectories.

### Propagation and rollout

- same-regime h1-h3: damage/crack geometry error, history/forcing-state error,
  active-driver error for Tier A, registered mask/length/area/tip error for
  Tier B;
- autonomous transition: warning plus transition-state field/topology;
- post-transition conditional rollout after exact/observable reset;
- rolling forecast with observation assimilation;
- uncertainty width, empirical coverage and proper score versus horizon;
- per-trajectory results first; pooled cell/window rows are descriptive only.

Tier-A field panels use area weighting, common FEM-p99 support, own-p99 support,
active log-MAE/correlation, support IoU and support-area ratio. Tier-B headline
metrics are registered mask/geometry, event timing, calibration and utility;
hidden-field similarity is not a deployment metric.

## 7. Baseline pass and neural-entry gate

No universal numerical promotion threshold is invented from the current four
synthetic or six road trajectories. Before execution, a dated amendment must
freeze the operating false-alarm budget and the smallest decisive improvement
threshold using domain utility and training-only variability.

Neural training is scientifically eligible only when all conditions hold:

1. every included trajectory passes identity, event, state and censoring gates;
2. Tier A contains multiple independent geometry/material/loading groups, or
   the claim is explicitly restricted to the current shared family;
3. Tier B has a complete road-observable join for the claimed channels;
4. every outer training fold contains both event-positive and at-risk negative
   opportunities without borrowing the holdout event time;
5. persistence, secant, CUSUM, hazard and matched Markov are complete;
6. probability calibration is assessed on independent trajectories, not cells;
7. a frozen code/data/protocol review passes and the owner separately
   authorizes the named producer run.

## 8. Stop rules

- Stop on any future-cycle, event-distance, held-out-normalization or
  target-derived feature leakage.
- Stop if P0/T3 or another alias maps ambiguously to source states.
- Stop if first detect is replaced by confirmation/terminal cycle.
- Stop if a single transition or a single physical family is presented as a
  general transition predictor.
- Do not relax the event predicate, false-alarm budget, calibration bins,
  threshold, mask or holdout after results.
- A failed transparent-control gate does not authorize a neural rescue on the
  same frozen release.

## 9. Required outputs

- complete trajectory inventory and exclusion log;
- fold-by-fold leakage receipt;
- warning predictions for every legal origin;
- baseline/ablation tables;
- warning, reliability, free-rollout, reset and assimilation figures;
- uncertainty-versus-horizon figure;
- `decision.md` with allowed and blocked claims.
