# Road Observation to Latent Fracture State: Phase-1 Bridge

## Status

Implemented as an offline interface and evidence audit. No PIDL training, FEM
solve, or real-road calibration was performed.

## Scientific boundary

The deployed road problem is

```text
real observation y_t
  -> explicit observation operator H
  -> posterior latent state z_t
  -> common frozen analysis state
  -> h1-h3 state forecast and separate threshold/RUL forecast
```

The current sealed c87 result is not the first arrow. It directly observes FEM
`log10_psi_raw` at 8,641 mesh locations. It is retained only as an oracle
upper bound. A physical sensor budget must instead be stated in registered
image visits/area, FWD test locations and offsets, strain sensor count, WIM
stations and aggregation interval, and temperature/moisture sensor cadence.

## Implemented assets

- `source/road_observation_contract.py`
  - locks `damage`, `alpha_bar`, fatigue degradation, `g(alpha)`, `psi_raw`,
    and `psi_active` as latent rather than direct road measurements;
  - declares image, FWD, strain/DIC, WIM, and environment operators;
  - validates one predictor-independent assimilated-state package;
  - represents unavailable uncertainty as `NaN`, not false zero variance.
- `SENS_tensile/build_road_observation_phase1_package.py`
  - reads the existing sealed inverse package only;
  - writes the road observation spec, actual-budget table, source catalog,
    frozen c87 synthetic-reference interface, manifest, hashes, and decision;
  - leaves real-road metrics blank until paired calibration exists.
- `tests/test_road_observation_contract.py`
  - rejects oracle relabeling;
  - checks per-channel provenance and the common-state interface;
  - rejects false zero uncertainty for an uncalibrated analysis.

## Open/real data roles

1. **FHWA LTPP InfoPave** provides repeated in-service pavement histories,
   including distress, FWD, traffic, climate, structure, and maintenance. It is
   suitable for a real observation/RUL benchmark after section-level alignment,
   but it does not label phase-field hidden states.
2. **MnROAD** provides the strongest candidate for paired observation-operator
   calibration because its official program describes distress/FWD monitoring,
   dynamic strain/load response, traffic/weather, and long-running temperature
   and moisture sensors. Some raw/complex channels require a data request.
3. **RDD2022** is useful for image-domain pretraining and robustness. It is
   cross-sectional object-detection data and cannot validate latent-state
   reconstruction or RUL by itself.

## Required next gate

Before a learned inverse or new Taobo run, assemble at least three physically
different trajectories/assets with synchronized registered imagery,
load/FWD or strain response, traffic load blocks, and environment. Freeze the
observation operator and grouped residual model before holdout. Then evaluate:

- state identifiability and posterior calibration;
- sensor cost against h1-h3 crack/support forecast;
- threshold/RUL calibration as a separate long-horizon task;
- leave-one-trajectory, then leave-one-asset/road-section-out robustness.

The current one-trajectory package cannot support real-road generalization or
material-parameter inversion.

## Authoritative source endpoints

- FHWA LTPP InfoPave: <https://infopave.fhwa.dot.gov/>
- FHWA LTPP IMS User Guide: <https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/21038/21038.pdf>
- MnROAD data: <https://www.dot.state.mn.us/mnroad/data/index.html>
- MnROAD dynamic sensors: <https://www.dot.state.mn.us/mnroad/data/dynamic-sensors.html>
- MnROAD environmental sensors: <https://www.dot.state.mn.us/mnroad/data/environmental-sensors.html>
- RDD2022: <https://github.com/sekilab/RoadDamageDetector>
