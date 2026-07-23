# Road time and observation-trigger formulation decision

## Verdict

The current FEM evidence supports a **rolling conditional forecast**: assimilate a recent state, forecast the next one to three calibrated load blocks, and request a new inspection when uncertainty, observation innovation, or traffic/environment shift exceeds a frozen envelope. It does not support mapping one FEM cycle to one axle, ESAL, day, or inspection interval, and it does not support deterministic field rollout to road failure.

One road forecast step should provisionally be a **calibrated equivalent-load block with calendar/environment caps**. The block closes at a calibrated exposure increment, maximum calendar duration, material environment shift, inspection, or maintenance event. Without WIM/load-spectrum data, the only defensible fallback is inspection-to-inspection state propagation.

Longer-horizon road output must be scenario-conditioned threshold probability, event hazard, and RUL distribution. It must not be presented as unlimited recursion of the h1-h3 field operator.

## Offline trigger diagnostic

The matched Markov/GRU/LSTM/TCN/Transformer/diagonal-SSM prediction ensemble was analysed without retraining. Signal envelopes were frozen from c77-c79 before c80-c89 was audited. Trigger decisions use only model ensemble disagreement and self-state/support drift. FEM IoU and error appear only in columns prefixed `audit_only_` and do not enter the rule.

- First committee candidate inspection request: `83`.
- First committee candidate stop-recursive decision: `84`.
- First audit-only FEM-p99 IoU failure (<0.5): `c81`.
- Candidate request lag relative to that hidden failure: `2` simulation steps; this is not positive early-warning lead time.
- Audit-only committee FEM-p99 IoU at c80: `0.555`.
- Audit-only committee FEM-p99 IoU at c87: `0.010`.

The model-only committee warning **lags** the first hidden support-gate failure and therefore does not provide useful early warning in this trajectory. These cycle values are a one-trajectory diagnostic, not an operational threshold. Three calibration states are too few to estimate false-alarm rate, missed-transition rate, or lead-time generalisation. The trigger is therefore `diagnostic_only_single_trajectory`, and observation innovation is a required next input rather than an optional enhancement.

## Reality-facing trigger hierarchy

1. Use model ensemble/latent uncertainty as a warning, never as the only proof of physical change.
2. Compare predicted and measured crack geometry, FWD deflection basin, and strain localization through Agent1's observation operator.
3. Treat WIM/load-spectrum, temperature, moisture, sensor drift, and maintenance as OOD/data-quality gates.
4. Request image/FWD/strain when one model warning is corroborated by one observation/OOD warning, or when a hard safety/data-quality gate fires.
5. Stop recursive field rollout after two consecutive model warnings, a hard innovation, an OOD exposure, an overdue inspection, or maintenance-induced state reset.

## Scope and blockers

- Exactly one eta0 FEM trajectory is available; no road early-warning generalisation is claimed.
- Current data contain no WIM/ESAL calibration, timestamps, temperature, moisture, FWD, strain, or maintenance records.
- The historical data-efficiency runner contains privileged cycle-phase inputs and is excluded from the operational trigger.
- c89 remains an autonomous-transition stress test, not a normal road forecast target.
- Promotion requires physically diverse trajectories, synchronized road/laboratory observations, calibrated likelihoods, and leave-one-trajectory/load/road-section-out validation.

## Decision

Accept the time/horizon and interface formulation as a **framework-validation diagnostic**. Quarantine the numerical trigger thresholds. Do not launch new training until Agent1 supplies a frozen observation-operator contract and the project has physically diverse traffic/environment trajectories.
