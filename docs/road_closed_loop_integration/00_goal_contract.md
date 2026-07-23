# Road Closed-Loop Fracture Forecasting Integration Goal

## Objective

Integrate the three existing research branches into one road-facing closed loop:

1. road observations are assimilated into a predictor-independent latent state;
2. the latent state is propagated for one to three calibrated road load blocks;
3. model uncertainty, observation innovation, exposure shift, and data quality
   decide whether to continue, stop, or request a new inspection;
4. a new observation updates the state before forecasting resumes;
5. longer horizons are represented by scenario-conditioned hazard, threshold
   probability, and RUL distributions rather than unlimited deterministic field
   recursion.

## Evidence boundary

- FEM eta0 is the numerical mechanism reference, not road-deployment evidence.
- A direct FEM hidden-field probe is an oracle upper bound, not a physical
  sensor.
- A FEM-rendered image/FWD/strain channel is synthetic evidence even when it
  follows a realistic observation operator.
- A real-road claim requires measured data, calibrated observation operators,
  grouped road/trajectory holdout, and uncertainty coverage checks.
- Latent phase-field quantities such as fatigue history, degradation, raw
  tensile energy, and active driver are never labelled as direct road
  measurements.

## Canonical workflow

```text
registered road observations + masks + provenance
        -> Agent 1 observation operator and state assimilation
        -> hash-locked analysis-state bundle
        -> Agent 3 direct h1-h3 field forecast under Agent 2 load blocks
        -> Agent 2 model/innovation/OOD trigger
        -> continue | request inspection | stop recursion
        -> optional new observation and re-assimilation
        -> scenario-conditioned hazard / threshold probability / RUL
```

## Hard prohibitions

- No `cycle/89`, known failure cycle, cycle-to-failure, or future observation at
  forecast issue time.
- No comparison with different observed origins, masks, seeds, budgets, or
  future scenarios.
- No conversion of one FEM cycle into one axle, ESAL, day, or inspection
  interval without an independently calibrated mapping.
- No risk/RUL figure from random or otherwise untrained output heads.
- No use of FEM audit errors or FEM support IoU inside the operational trigger.
- No claim of autonomous transition prediction from a c87-reset experiment.

## Current completion gates

1. **Contract gate**: one versioned observation-state-time-forecast-trigger
   contract, adapters for every legacy field name, SHA-256 provenance, and
   explicit missingness/uncertainty semantics.
2. **Closed-loop code gate**: an executable path from observation package to
   assimilation state, h1-h3 forecast, trigger decision, optional reset, and
   risk output availability status.
3. **Matched numerical gate**: identical FEM reference, observed origin, masks,
   scenarios, seeds, capacity, and optimisation budget. Short propagation,
   autonomous transition stress, and post-transition conditional propagation
   are reported as separate tasks.
4. **Trigger gate**: observation-aware triggering is evaluated without audit
   leakage. Single-trajectory lead/lag is diagnostic only.
5. **Reality gate**: at least three independent road/laboratory trajectories or
   road sections with synchronized imagery, FWD or strain response, traffic
   exposure, environment, and maintenance provenance. Grouped holdout and
   calibrated uncertainty are mandatory before a real-road promotion claim.

## Agent ownership

- Agent 1 owns the observation operator, analysis-state bundle, provenance, and
  observation-to-state adapter.
- Agent 2 owns road time/load blocks, future scenarios, observation innovation,
  and request/stop/continue trigger semantics.
- Agent 3 owns the forecasting API, h1-h3 field propagation, long-horizon risk
  availability, and closed-loop orchestration.
- This integration branch owns compatibility, acceptance, and the final
  evidence-bounded decision. It does not silently repair incompatible agent
  outputs.

