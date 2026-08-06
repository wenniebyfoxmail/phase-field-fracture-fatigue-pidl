# LTPP geoforecast spatial-registration track

## Mechanism question

Can the frozen printed-grid rectification support two-dimensional crack-position
and continuation-tip prediction, or is its coordinate uncertainty too large?

## Claim boundary

This track audits the coordinate carrier only. It does not alter frozen crack
labels, train a forecast model, identify the same physical crack across dates,
or prove that a hand-drawn stroke is a material-point observation.

The existing scalar crack-length track remains separate. A failure here blocks
two-dimensional position/tip claims but does not retrospectively invalidate a
separately reviewed scalar-length analysis.

## Current evidence

- The acquisition receipt records a common nominal `15.24 m x 5.00 m` frame
  but explicitly records `direct_pixel_registration = false`.
- Each survey was independently rectified by deskewing, selecting a printed
  grid rectangle, and resizing to `1524 x 500 px`.
- Same-image primary/secondary agreement is not cross-date registration error.

## Experiment states

| State | Status | Evidence |
|---|---|---|
| Existing nominal rectification | coordinate comparison only | `../ltpp_06_1253_rectification_gate_20260805.md` |
| v1 conditional internal-grid audit | approved for one preflight only | `ltpp_geoforecast_spatial_registration_audit_preregistration_v1_20260806.md` |

## Active gate

Only the eight frozen `06-1253` states may be audited. Every date must pass the
fixed held-out printed-grid error gate before this section can enter any 2-D
crack-position or tip algorithm. Failure cannot be rescued by deleting dates,
changing the detector, or trying homography/TPS/piecewise transforms inside v1.

## Next action

Freeze the v1 preregistration and code, run synthetic unit tests, then execute
exactly one read-only `06-1253` preflight. No 2-D model training is authorized.
