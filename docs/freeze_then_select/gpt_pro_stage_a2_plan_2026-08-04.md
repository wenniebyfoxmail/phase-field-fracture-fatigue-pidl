# GPT Pro Planning Gate: Stage A2 Sparse Adapter And Forecast

## Adopted design

- Generate damage by rolling the same declared residual equation used for
  selection; do not generate crack geometry independently.
- Fit a deterministic separable spatial-DCT and temporal cubic-B-spline adapter
  from damage observations at or before a fixed cutoff.
- Freeze and hash the reconstructed pre-cutoff field. Derive its time rate from
  the fitted spline and build weak residual systems only before the cutoff.
- Hold out whole synthetic sections. Future environmental/load covariates may
  drive rollout, but future damage cannot enter the adapter or selector.
- Compare oracle SVWS, reconstructed SVWS, reconstructed single-shot, and fixed
  physics using support metrics plus crack-mask IoU, tip error, event-time
  error, area error, and rollout RMSE.
- Classify failures as oracle-, adapter-, selection-, or forecast-limited.

## Fixed gates

- Oracle support Jaccard at least 0.90.
- Adapter validation RMSE at most `max(0.06, 1.5*noise_sigma)` and cutoff
  `d>=0.5` IoU at least 0.65.
- Reconstructed SVWS support Jaccard at least 0.75.
- Forecast `d>=0.5` IoU improvement at least 0.08 over fixed physics, tip error
  reduction at least 15%, and median event-time error at most two steps.
- SVWS superiority over single-shot is claimable only with paired support or
  stability improvement of at least 0.10 and forecast improvement in most
  cases.

## Deferred

The alternating moving-field/sparse-selector diagnostic is Stage A2b. It is not
the real neural PIDL joint-training baseline and is not required for the Stage
A2 leakage-safe closed-loop gate.

## Oracle-smoke design correction

The first true weak-derivative oracle smoke exposed near-perfect correlation
between low-temperature and low-temperature-by-log-traffic columns, plus a
nearly zero freeze-thaw column. Before the main matrix, interaction columns were
centered at the predeclared reference `log(1+500 ESAL)` and the synthetic
temperature range was widened to activate freeze-thaw variation. Selection
thresholds, holdouts, and gates were not changed.

## Claim boundary

All Stage A2 sections, environmental variables, and crack trajectories are
synthetic. Passing supports software/tooling validity only, not road validation,
causal mechanism identification, or neural PIDL improvement.
