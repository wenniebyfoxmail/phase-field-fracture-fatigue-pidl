# Multi-trajectory forecast readiness

## Verdict

not_ready_no_training. Training allowed: false.

- Producer contract: blocked_pending_contract
- Independent trajectories: 0
- Field training allowed: false
- Transition training allowed: false
- Risk training allowed: false

## Task readiness

- observed_state_same_regime_h1_h3: false
- autonomous_transition_warning: false
- observation_reset_conditional_propagation: false

## Blockers

- Agent/FEM task 2 trajectory contract is not published
- producer leave-one-combination-out split is not frozen and verified
- road-aware parameter-count manifest is not verified within the sealed tolerance

## Hazard/RUL blockers

- none

## Boundary

This is a tooling/readiness result. Repeated cycles from one numerical trajectory
cannot satisfy the independence gate. Rolling h1-h3 fields and transition
hazard/RUL are separate outputs; an unlimited free rollout is not a road
long-horizon forecast.
