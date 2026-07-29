# Multi-trajectory forecast readiness

## Verdict

ready_for_fair_training. Training allowed: true.

- Producer contract: contract_loaded
- Independent trajectories: 4
- Field training allowed: true
- Transition training allowed: true
- Risk training allowed: false

## Task readiness

- observed_state_same_regime_h1_h3: true
- autonomous_transition_warning: true
- observation_reset_conditional_propagation: true

## Blockers

- none

## Hazard/RUL blockers

- calibrated uncertainty is unavailable on at least one eligible trajectory
- every LOTO training fold needs both event and right-censored trajectories

## Boundary

This is a tooling/readiness result. Repeated cycles from one numerical trajectory
cannot satisfy the independence gate. Rolling h1-h3 fields and transition
hazard/RUL are separate outputs; an unlimited free rollout is not a road
long-horizon forecast.
