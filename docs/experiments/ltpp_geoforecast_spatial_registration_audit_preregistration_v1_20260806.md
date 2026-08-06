# LTPP geoforecast spatial-registration audit preregistration v1

## Status and authorization

`APPROVED_FOR_CONTROL_POINT_FREEZE_AND_ONE_06_1253_PREFLIGHT_ONLY`

This preregistration applies only to a conditional audit of the already frozen
rectification receipt. It is not an independent external-ground-truth
registration validation and does not authorize 2-D prediction.

## PIDL Experiment Gate

- **Mechanism question:** Is residual nonuniformity in the frozen printed-grid
  carrier small enough for 2-D crack-position and continuation-tip prediction?
- **Claim changed if success:** The eight-state `06-1253` coordinate carrier is
  qualified to enter a separately preregistered 2-D algorithm decision.
- **Claim changed if failure:** The current carrier is not qualified for 2-D
  position/tip prediction; scalar-length work remains a separate claim.
- **Cheaper diagnostic first:** Reuse the frozen grid-detection receipt; do not
  rerun image detection, modify labels, or train a model.
- **Minimal output asset:** Per-date and per-axis CSV, control-point receipt,
  eight-panel overlay with sidecar, decision note, and SHA-256 manifest.
- **Code/producer alignment:** Deterministic offline Mac analysis only; no PIDL
  training and no producer machine required.
- **Success criteria:** All eight dates pass the fixed held-out grid-error gate.
- **Failure criteria:** Any missing fixed control line or any threshold failure.
- **Registry destination:** This track document first; research frontier only
  after the result changes the active 2-D route.
- **Decision:** Launch one read-only preflight after code/tests are frozen.

## Frozen inputs

1. `grid_gate_results.json` from the existing `06-1253` rectification gate.
   Its frozen SHA-256 is
   `5b787c11f69d61fadd124cbdd488f24c12d0cbab8a0ab2d8b3ec2c03d37f6e42`.
2. The eight final frozen adjudicated states `A001` through `A008`, spanning
   `1991-06-10` through `2012-04-17`.
3. The exact SHA-256 of this preregistration and the audit script at execution.

The 2015 map is not part of the frozen 37-state adjudicated packet and is not
audited. No crack coordinates, chronological outcomes, prediction scores, or
forcing variables may influence control-line extraction.

## Conditional measurement procedure

The audit does not rerun deskewing or line detection. For each included date it
reads only the already frozen values:

- `x0`, `x1`, `y0`, `y1`;
- `detected_vertical_positions`;
- `detected_horizontal_positions`.

Expected line centres are:

```text
x_nominal(i) = x0 + i * (x1 - x0) / 10,  i = 0..10
y_nominal(j) = y0 + j * (y1 - y0) / 5,   j = 0..5
```

For each expected centre, the candidate window is exactly `0.18` times the
adjacent nominal spacing. Candidates are frozen detected positions inside the
closed window. The chosen centre is the candidate with minimum absolute
distance from nominal; an exact tie selects the lower pixel coordinate.

No manual completion is allowed. If any required calibration or held-out line
has no candidate, that date is `INSUFFICIENT_CONTROL_POINTS`. The detector,
window, line indices, and tie-break cannot be changed after execution.

## Fixed affine audit

Calibration indices:

```text
x = {0, 2, 4, 6, 8, 10}
y = {0, 2, 4}
```

Held-out indices:

```text
x = {1, 3, 5, 7, 9}
y = {1, 3, 5}
```

Ordinary least squares independently fits:

```text
x_m = a * x_pixel + b
y_m = c * y_pixel + d
```

Held-out coordinates never enter these fits. Homography, TPS, piecewise affine,
manual corners, alternate line sets, or per-date rescue are prohibited.

## Fixed metrics and gate

The audit saves five signed/absolute x-line residuals and three signed/absolute
y-line residuals. Their Cartesian product forms 15 **dependent** held-out
intersections; it is not interpreted as 15 independent samples.

For intersection error `e = sqrt(dx^2 + dy^2)`:

- median: `numpy.median(errors)`;
- p95: `numpy.quantile(errors, 0.95, method="linear")`;
- maximum: `numpy.max(errors)`.

The a-priori engineering qualification thresholds are:

1. every fixed calibration and held-out line exists;
2. intersection median `<= 0.05 m`;
3. intersection p95 `<= 0.10 m`;
4. intersection maximum `<= 0.20 m`.

These are engineering error budgets, not confidence bounds inferred from the
same-image annotation disagreement values.

Date statuses are limited to:

- `SPATIAL_REGISTRATION_QUALIFIED`;
- `INSUFFICIENT_CONTROL_POINTS`;
- `SPATIAL_REGISTRATION_NOT_QUALIFIED`.

The section passes only if all eight dates are qualified. There is no borderline
status and no deletion of failed dates.

## Perturbation analysis

The proposed 500-draw covariance/residual perturbation is removed from v1.
With only three y calibration lines, its uncertainty model is not sufficiently
identified. It must not be run, reported, or added after seeing v1 results. Any
future perturbation analysis requires a separate preregistration and review.

## Termination and claim boundary

One execution is allowed. Any failure yields
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`. The result may motivate a
newly reviewed acquisition or registration track, but v1 itself cannot be
rescued. Frozen AI, human, and adjudicated labels remain unchanged.

## External review

The initial design received `REVISE_V1_BEFORE_PREFLIGHT`. After adopting the
six required changes, the exact revised design received
`APPROVE_REVISED_V1_PREFLIGHT_ONLY`. The review record is
`../reviews/ltpp_geoforecast_spatial_registration_v1_external_review_20260806.md`.
