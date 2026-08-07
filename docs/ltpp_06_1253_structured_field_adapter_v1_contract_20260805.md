# LTPP 06-1253 Minimal Structured Field Adapter v1 Contract

## Evidence status

Single-annotator, post-pilot exploratory field qualification. This adapter does
not create physical phase-field ground truth and cannot overwrite the frozen
observation fields.

## Frozen scope

- Spatial panel: 0-50 ft only.
- Input dates: the seven within-monitoring-history dates from 1991-06-10 through
  2007-11-06.
- The 2012 and 2015 post-Out-of-Study maps are excluded from fitting and gates.
- Input channel: frozen `combined_damage` proxy.

## Adapter

1. Use the rectified spatial grid cells as fixed spatial basis functions.
2. At each grid cell, compute the equal-weight least-squares isotonic projection
   of the seven observed proxy values.
3. Fit a monotonicity-preserving PCHIP spline through the projected values using
   actual elapsed days.
4. Save projected observation fields and spline coefficients in an independent
   artifact. Do not mutate labels or the original NPZ.

This is a minimal deterministic structured adapter, not a neural or learned
low-rank field adapter.

## Frozen qualification checks

1. Adapted values and dense spline evaluations remain in `[0,1]` within `1e-7`.
2. Dense spline evaluations have no temporal decrement below `-1e-7`.
3. Global projection RMSE against the frozen proxy is at most `0.15`.
4. Maximum per-date projection RMSE is at most `0.25`.
5. In leave-one-interior-date-out tests, adapter RMSE is lower than prior-date
   persistence for at least three of five dates.
6. Median relative RMSE improvement over persistence is at least 5%.

All checks must pass. Thresholds cannot be relaxed after seeing the result.

## Interpretation

A pass authorizes regeneration of climate-free weak systems and an unchanged
A/B comparison. It does not validate a PDE, crack causality, or natural crack
morphology. A failure localizes the problem to cross-date observation
consistency or the minimal adapter assumptions and blocks downstream A/B reruns.
