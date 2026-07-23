# Completion Evidence Matrix

This file is the acceptance checklist for the active integration goal. A row is
complete only when the cited evidence directly proves the requirement.

| Requirement | Required evidence | Current evidence | Status |
|---|---|---|---|
| Frozen observation-to-state contract | Versioned schema, adapter, validator, hash and tests | Agent 1 phase-1 schema exists but is not yet compatible with Agent 2/3 | Incomplete |
| Frozen road-time and scenario contract | Versioned load-block/scenario schema with leakage tests | Agent 2 phase-1 JSON exists; no cross-agent adapter | Incomplete |
| Observation innovation trigger | Runtime-only channel packet, no FEM audit leakage, offline lead/lag table | Model-only trigger is two benchmark steps late | Incomplete |
| Observation-aware h1-h3 forecaster | Compatible state/time/observation inputs and matched checkpoint smoke | Agent 3 interface and exact legacy transfer exist | Partial |
| Closed-loop state machine | Executable continue/request/stop/re-assimilate path | No integrated orchestrator | Missing |
| Long-horizon risk boundary | Hazard/RUL availability status and calibrated producer evidence | Heads exist but are untrained | Interface only |
| Fair numerical evaluation | Same origin, masks, scenarios, seeds, budget; separate three tasks | Existing temporal study supplies part of the protocol | Partial |
| Reproducible package | Manifest, hashes, tests, figures, decision and registry endpoint | Three separate packages exist | Incomplete |
| Real-road validation | Measured synchronized assets, grouped holdout, calibrated uncertainty | Candidate data catalog only | Not achieved |

## Required numerical task separation

1. **Same-regime conditional propagation**: observed-state multi-origin h1-h3.
2. **Autonomous transition stress**: free forecast through the sealed transition;
   failure here cannot be hidden by a reset result.
3. **Post-transition conditional propagation**: every model receives the same
   assimilated transition state.
4. **Road risk evaluation**: grouped road/trajectory holdout with event/censor
   diversity; unavailable in the current one-trajectory benchmark.

