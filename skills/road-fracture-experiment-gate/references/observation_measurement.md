# Observation And Measurement Adapter

Read this reference only when the claim depends on real or experimental
observations, labels, registration, or physical reference measurements.

## Admissible Unit

Identify the physical unit before modelling: asset/site/specimen, lane or
coordinate segment, observation time, sensor/view, and acquisition protocol.
Repeated images are not longitudinal evidence unless this identity is stable.

Freeze only the validity checks needed by the claim:

- provenance, licence/access state, file/schema identity, and exclusions;
- asset-time key and independence unit;
- coordinate registration and its error when spatial change is evaluated;
- label/reference protocol, repeatability, adjudication, and uncertainty;
- resolution, visibility, missed observations, irregular intervals, and OOD;
- intervention, maintenance, replacement, and censoring boundaries.

Unknown or unavailable fields remain unknown. Do not silently join sources into
a fictitious trajectory or use future geometry to fit an origin-time transform.

## Smallest Primary Criterion

Match the criterion to the claim:

- data capability: whether the required unit/fields/time relation exist and are
  auditable;
- registration: physical-coordinate error against independent controls;
- current-state measurement: error or risk against an independent reference,
  interpreted relative to reference repeatability;
- selective measurement: fixed-budget risk or coverage, not prettier heatmaps.

Segmentation overlap is appropriate only when segmentation itself is the target.
It does not establish width, tip, topology, persistent crack identity, or future
prediction unless those objects are independently referenced.

## Stop Rules

Stop or narrow the claim when the asset-time key is unresolved, the reference
cannot identify the estimand, registration error exceeds the effect of interest,
or maintenance/censoring makes the transition ambiguous. More architecture
cannot repair an unqualified observation.
