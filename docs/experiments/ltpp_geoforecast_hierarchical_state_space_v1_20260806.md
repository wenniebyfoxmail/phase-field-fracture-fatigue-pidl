# LTPP multisection hierarchical state-space gate v1

Date: 2026-08-06  
Status: `RELIABILITY_NEGATIVE`

## Question

Can a regularized hierarchical probabilistic crack-length change model,
conditioned only on the frozen source geometry, interval duration, and
leakage-safe climate forcing, reliably outperform persistence on unseen LTPP
sections while preserving calibrated uncertainty?

## Immutable inputs

- 37 human-adjudicated states, 249 features, 232 crack features;
- 31 transitions: 25 development and six final-time tests;
- adjudicated manifest SHA-256:
  `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad`;
- transition manifest SHA-256:
  `1c38725d23a9cdaea69e3f71b5eaaa6469d02371c85de7a3b2061ba79e92e918`;
- baseline manifest SHA-256:
  `e70564d3e06c81517268c0974845759e7a307769ee3478534cd8f08b8bee2b55`.

The model was run once after the queue reached `139/139`. No target geometry
entered feature construction, model fitting, or threshold selection.

## Frozen controls

On the six future-time transitions:

| model | length MAE (m) | buffered F1 | new-geometry error (m2) |
|---|---:|---:|---:|
| persistence | 7.0543 | 0.4333 | 1.6018 |
| scalar linear growth | 7.8401 | 0.4333 | 1.6018 |
| local-tip extrapolation | 7.8401 | 0.4368 | 1.6847 |

The local-tip F1 change was too small and traded against worse length and new
geometry errors. It is not a credible improvement over persistence.

## Challenger and locked gates

The challenger used ridge-regularized fixed effects for current crack length
and climate summaries, section random intercepts with partial pooling, and a
Gaussian change-rate predictive distribution. Positive status required all of:

1. at least 10% unseen-section length-error improvement;
2. at least 10% unseen-section new-geometry improvement;
3. simultaneous improvement in at least four of six held-out sections;
4. 85-95% coverage for nominal 90% intervals.

## Result

- unseen-section length improvement: `-15.6348%` (failed);
- unseen-section new-geometry improvement: `-6.3066%` (failed);
- sections improving both: `0/6` (failed);
- nominal-90% coverage: `0.9355` (passed).

The final-time-only challenger check had length MAE `6.9093 m`, buffered F1
`0.4355`, new-geometry error `1.6341 m2`, and coverage `0.8333`; it does not
override the primary unseen-section failure.

Decision SHA-256:
`a71e2c87068fc400e12b6e200a6d34c4719545b71819f6f52cdf82650353ecce`.

## Decision

Persistence remains the honest point-forecast control. The state-space model
may be retained only as an uncertainty diagnostic. This negative result blocks
graph-neural, PIDL, and hyperparameter-sweep rescue attempts on the same six
sections. Reopening the method branch requires new independently frozen assets
or new aligned forcing/state channels, not more architecture.

