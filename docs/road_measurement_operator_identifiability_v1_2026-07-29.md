# Road Measurement Operator and Identifiability Interface v1

## Scope

This interface converts road-measurable observations into a versioned,
predictor-independent handoff. It does not solve the inverse problem and does
not promote synthetic or latent FEM fields to road sensors.

Allowed direct observations are:

- registered crack images, masks, width, length, and tip;
- registered DIC displacement or directional strain sensors;
- FWD load and deflection basin;
- WIM axle load, speed, and load spectrum;
- temperature and timestamp;
- maintenance events and state-segment resets.

Every record carries units, a timezone-aware timestamp, uncertainty,
missingness, evidence class, and, for spatial data, a registration contract.

## Latent Firewall

Damage `alpha`, fatigue history `alpha_bar`, degradation `g(alpha)`, raw
driver, and active driver are forbidden direct-observation names. A DIC or
strain field can be converted to a conditional tensile-energy estimate only
after declaring the constitutive model, material parameters, kinematic
assumption, and tensile split. The result remains in `derived_estimates` with:

```text
direct_sensor_observation = false
decision_eligible = false
```

## Interfaces

- `road_measurement_operator_v1`: operator and measurement semantics.
- `road_measurement_handoff_v1`: stable asset/trajectory/inspection envelope.
- `road_observation_state_bundle_v1_adapter_v1`: maps only measurement arrays
  into the current bundle; it never creates `state_mean`.
- Unknown multi-trajectory schemas require a new versioned adapter. The v1
  interface does not infer future channel names, dimensions, or defaults.

## Identifiability Ladder

The ladder separates three questions:

1. Hidden-state assimilation: repeated registered geometry plus a mechanical
   response channel is the first conditional candidate.
2. Material-parameter inversion: this additionally requires independent loads,
   multiple assets or specimens, sensitivity-rank checks, and posterior tests.
3. Forecast update: this additionally requires WIM/environment/maintenance
   context, calibrated uncertainty, and physical holdout validation.

Passing an earlier rung never implies passing a later one.

## Offline Smoke

The frozen c87 eta0 package is used only as a synthetic contract source. A
declared sigmoid visibility operator renders 1,351 sampled crack-probability
values from 86,408 latent nodes. All other unavailable sensor families remain
`NaN` with `mask=false`.

The smoke passes with zero forbidden latent channels, zero oracle-raw entries
in the state-bundle measurement adapter, no generated state mean, and
`decision_eligible=false`. This is not real-road validation, material inversion,
uncertainty calibration, or forecast validation.

Primary decision package:

`analysis/road_measurement_operator_identifiability_v1_20260729/decision.md`
