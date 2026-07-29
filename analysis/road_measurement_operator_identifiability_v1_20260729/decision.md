# Road Measurement Operator v1: Decision

## Verdict

**Executable measurement-interface pass; identifiability and real-road validation remain unpassed.**

The package implements adapters for registered crack imagery/geometry, DIC displacement, directional strain, FWD load-deflection basins, WIM load/speed spectra, temperature/time, and maintenance/reset. Every spatial record carries coordinate-frame, registration, uncertainty, timestamp, missingness, and source-hash semantics.

## Firewall

`alpha`, `alpha_bar`, degradation, raw driver, and active driver are forbidden as direct observation channels. DIC/strain can produce a conditional `psi_raw` estimate only after declaring the constitutive model, material parameters, kinematic assumption, and tensile split. That estimate is stored separately with `direct_sensor_observation=false` and `decision_eligible=false`.

## Identifiability decision

A registered crack image alone constrains surface geometry, not energetic history. Image plus FWD adds stiffness-response information but remains confounded. Image plus measured displacement/strain can support conditional hidden-state assimilation; it still does not uniquely identify materials. Material inversion requires repeated independent loads/assets plus sensitivity-rank and posterior checks. Forecast updates additionally require timestamped WIM/environment/maintenance context and calibrated uncertainty.

## Multi-trajectory boundary

The stable envelope is `road_measurement_handoff_v1`. The current `road_observation_state_bundle_v1` has an explicit adapter. Unknown future multi-trajectory schemas receive `versioned_adapter_required_no_schema_guessing`; no names, shapes, or missing measurements are fabricated.

## Evidence boundary

The c87 eta0 source is used only to render a declared synthetic crack-visibility observation and exercise masks/adapters. It is one synthetic trajectory, not real road data, material inversion, calibrated uncertainty, or forecast validation.
