# Road Observation-State Bundle v1: Decision

## Verdict

**Interface pass; real-road inversion remains untested and quarantined.**

The frozen c87 Agent1 analysis state can now be consumed through one versioned schema by Agent2 and Agent3. The conversion preserves the original evidence class as `oracle`, preserves uncalibrated uncertainty as all-NaN, and does not create image, FWD, strain, WIM, temperature, moisture, timestamp, or equivalent-load values.

## Frozen handoff

- Canonical bundle SHA-256: `b9bb52026737ed11a9463051f31e7c05057595ec0e015d8a6dec6127c2a4c86e`.
- Agent3 history skeleton SHA-256: `e482c52ceff47038493c7563a99133f5e6c4017009d482aea8707a1c58d83e74`.
- Agent2 innovation packet is explicitly `decision_eligible=false`.
- Agent2/3 must receive this same bundle hash and may not select model-specific observations or priors.

## Semantic rules now enforced

1. `observed_channel_mask` attributes latent analysis updates; it is not a sensor-availability mask.
2. Node and global observation masks describe measurement availability. Missing means NaN/null plus `mask=false`, never zero evidence.
3. State uncertainty uses exactly one of std, covariance, or ensemble. Uncalibrated std is NaN, not zero confidence.
4. Timestamp, equivalent load, delta-t, registration, coordinate frame, evidence class, and source hashes are explicit.
5. A maintenance reset requires a declared event id and a new state segment.
6. Hidden damage/history/degradation/raw/active variables are rejected as deployable sensors. An explicitly oracle-suffixed audit channel may exist but cannot enter an operational trigger.

## Unresolved boundary

This package proves interface compatibility on one eta0 FEM trajectory only. It does not validate an image/FWD/strain observation operator, identify material parameters, calibrate posterior uncertainty, map FEM cycles to road time, or demonstrate road-section generalization. A real-road pass requires registered measurements with load/environment/maintenance provenance and physical holdout validation.
