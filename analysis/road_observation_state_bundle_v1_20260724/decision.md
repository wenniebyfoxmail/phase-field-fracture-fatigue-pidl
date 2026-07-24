# Road Observation-State Bundle v1: Decision

## Verdict

**Interface pass; real-road inversion remains untested and quarantined.**

The frozen c87 Agent1 analysis state can now be consumed through one versioned schema by Agent2 and Agent3. The conversion preserves the original evidence class as `oracle`, preserves uncalibrated uncertainty as all-NaN, and does not create image, FWD, strain, WIM, temperature, moisture, timestamp, or equivalent-load values.

The final downstream contracts are pinned to Agent2 commit `19ca9c73a36a4fb80119a49c9234d6ee11501052` and Agent3 commit `e55070e4b29a1da39262e0138e2c4efc7240c195`, with independent content hashes for every consumed file.

This regeneration supersedes bundle hash `b9bb52026737ed11a9463051f31e7c05057595ec0e015d8a6dec6127c2a4c86e` and history hash `e482c52ceff47038493c7563a99133f5e6c4017009d482aea8707a1c58d83e74`. The underlying c87 state source remains byte-identical; hashes changed because final downstream provenance and packet semantics are now embedded.

## Frozen handoff

- Canonical bundle SHA-256: `e94027542484431d3a53222d930c81e9ed6c655b86a822ced1452fa8c4c0f253`.
- Agent3 history skeleton SHA-256: `5e5599d91d6caec35587892ce9f53d9672751c3a4b413af9d7a83f62f66bef88`.
- Agent2 innovation packet is explicitly `decision_eligible=false`.
- Agent2/3 must receive this same bundle hash and may not select model-specific observations or priors.

## Semantic rules now enforced

1. `observed_channel_mask` attributes latent analysis updates; it is not a sensor-availability mask.
2. Node and global observation masks describe measurement availability. Missing means NaN/null plus `mask=false`, never zero evidence.
3. State uncertainty uses exactly one of std, covariance, or ensemble. Uncalibrated std is NaN, not zero confidence.
4. Timestamp, equivalent load, delta-t, registration, coordinate frame, evidence class, and source hashes are explicit.
5. A maintenance reset requires a declared event id and a new state segment.
6. Hidden damage/history/degradation/raw/active variables are rejected as deployable sensors. An explicitly oracle-suffixed audit channel may exist but cannot enter an operational trigger.

7. Agent2 receives exactly `registered_crack_geometry_image`, `fwd_deflection_basin`, and `strain_localization`; all are fully masked in this oracle-only handoff. `decision_eligible=false` prevents the packet from producing an operational request or stop.

## Reproduction check

The builder was run against the clean `codex/road-closed-loop-integration` checkout with both downstream roots pointing to that checkout. The regenerated canonical bundle and Agent3 history skeleton were byte-identical to this package.

## Unresolved boundary

This package proves interface compatibility on one eta0 FEM trajectory only. It does not validate an image/FWD/strain observation operator, identify material parameters, calibrate posterior uncertainty, map FEM cycles to road time, or demonstrate road-section generalization. A real-road pass requires registered measurements with load/environment/maintenance provenance and physical holdout validation.
