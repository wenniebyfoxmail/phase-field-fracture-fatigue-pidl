# Attempt ledger

## Scope

Agent 3 stage 2 connects the frozen Agent1 latent-state bundle, Agent2 road
time/horizon/trigger contracts, and the observation-aware forecaster. The run
is schema, legacy-transfer and offline execution validation only.

## Contract audit

- Agent1 package SHA-256 verified: `276bca62f3955c0948bd23891aa10dcca209f3e562605303b61b263d53759ffe`.
- Agent1 schema: `road_assimilated_state_v1`, c87, FEM eta0, synthetic FEM-oracle evidence.
- Agent1 uncertainty is all NaN with explicit `uncalibrated_not_available` semantics.
- Agent2 v1 time, horizon and trigger hashes were verified before use.
- No Agent1/Agent2 phase-2 v1 package was present at implementation time; the
  adapter accepts their published v1 schemas without changing source names.

## Implementation

- Added strict Agent1/Agent2 loaders and SHA/schema/graph gates.
- Added explicit `alpha_bar -> fatigue_history` adapter.
- Added `RoadClosedLoopForecaster` and stateful Agent2 trigger evaluator.
- Restricted field forecasts to direct h1-h3.
- Hid random/untrained hazard and RUL tensors behind `unavailable_untrained`.
- Added request/stop/re-assimilate handling for innovation, OOD, data quality,
  overdue inspection and maintenance state changes.

## Real-package smoke

The Markov, TCN and diagonal SSM seed-1 legacy checkpoints were transferred and
executed at the same Agent1 c87 state. All used one analysis SHA, one observed
mask SHA and one irregular-dt missing-exogenous scenario SHA.

- Legacy h1 raw maximum absolute error: `0.0` for all three families.
- Missing raw-energy mask: 8,641 observed values; all unobserved values remain missing.
- Nine unavailable Agent2 model-internal trigger signals remain unavailable.
- Maintenance state change: `stop_and_request_observation`; fields withheld.
- Re-assimilation resets trigger history and permits execution again.
- Hazard/RUL: `unavailable_untrained` for every model.

## Failed or rejected paths

- Rejected zero-filling Agent1 all-NaN uncertainty.
- Rejected calling random stage-1 risk heads a forecast.
- Rejected deterministic field recursion beyond h3.
- Rejected training launch because longitudinal Agent1 observations, a frozen
  Agent2 road vectorizer, trajectory holdouts and event/censor diversity are absent.

## Status

`pass_tooling_only`; no producer training was launched.
