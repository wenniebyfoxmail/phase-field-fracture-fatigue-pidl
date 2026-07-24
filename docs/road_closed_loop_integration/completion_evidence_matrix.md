# Completion Evidence Matrix

| Requirement | Authoritative evidence | Verdict |
|---|---|---|
| Frozen observation-to-state contract | `road_observation_state_bundle_v1`; bundle SHA `e9402754...f253`; clean rebuild and SHA check | Pass |
| Frozen road-time and scenario contract | `road_time_mapping_v1`, `road_forecast_horizon_v1`, identical scenario hash in final audit | Interface pass; road calibration absent |
| Observation innovation trigger | Runtime leakage firewall; model/image/oracle comparison; image-only lead `0` | Diagnostic pass; early-warning claim fails |
| Observation-aware h1-h3 forecaster | Corrected adapter, exact legacy h1 transfer for Markov/TCN/SSM, field horizon hard-limited to h1-h3 | Tooling pass; new heads untrained |
| Closed-loop state machine | Continue/request/stop/re-assimilate path, maintenance stop and reset smoke | Pass |
| Long-horizon risk boundary | Untrained hazard/RUL returns `unavailable_untrained` | Boundary pass; scientific risk model absent |
| Fair numerical evaluation | Same analysis/mask/scenario hashes and FEM eta0 audit reference | Compatibility pass; no new performance ranking |
| Reproducible package | Central integration branch, builders, manifests, SHA checks, final audit, 153 tests | Pass |
| Real-road validation | Requires synchronized measured imagery, FWD/strain, WIM, environment and maintenance with grouped holdout | Not achieved |

## Numerical tasks remain separate

1. **Same-regime conditional propagation** uses matched observed origins and h1-h3.
2. **Autonomous transition stress** remains a sealed free forecast; existing
   models still miss the c87 transition.
3. **Post-transition conditional propagation** uses the same assimilated state
   for every model and does not prove autonomous transition prediction.
4. **Road risk evaluation** requires independent event/censor diversity and is
   unavailable in the current single-trajectory benchmark.

