# Transition, Forecast, And Decision Adapter

Read this reference when the target is later than the prediction origin:
future crack geometry/state, transition time, risk, calibrated uncertainty, or
inspection/maintenance utility.

## Freeze The Forecast Object

Declare:

- physical evaluation unit and grouping key;
- origin, horizon, target, and whether the task is one-step, conditional
  continuation, or autonomous rollout;
- information actually available by the origin, including whether future
  weather/load/action is known, forecast, scheduled, or unavailable;
- maintenance/intervention and censoring semantics;
- the simplest honest comparator using the same information.

Use future-time and physical asset/site/environment holdouts. Random frames,
nodes, patches, or overlapping windows from the same trajectory do not establish
generalisation. Report teacher-forced or post-observation updates separately
from autonomous prediction.

## Comparator Ladder

Use only as much ladder as the claim needs:

```text
persistence -> linear/secant/exposure -> probabilistic state-space
            -> learned temporal model -> physics-hybrid model
```

A more complex model advances only if it adds stable value over the strongest
simpler admissible comparator. Architecture novelty is not a success criterion.

## Smallest Primary Criterion

- deterministic future state: one decision-relevant future loss or baseline
  improvement aggregated by independent unit;
- event timing/risk: one frozen time-to-event or risk metric with censoring
  handled explicitly;
- probabilistic prediction: a proper scoring rule; add a coverage condition only
  when calibrated coverage is itself part of the claim;
- decision policy: net benefit or loss under a fixed policy, budget, and action
  set on independent or prospective units.

Diagnostics may include mask/tip/area error, event timing, calibration curves,
failure strata, and rollout drift, but they do not vote unless declared in the
single primary claim.

## Stop Rules

Stop architecture expansion when trajectories are not qualified, leakage-safe
holdout is impossible, persistence/simple state-space remains unbeaten, or
autonomous rollout fails while teacher-forced prediction passes. A realistic
generated video is not physical forecasting evidence.
