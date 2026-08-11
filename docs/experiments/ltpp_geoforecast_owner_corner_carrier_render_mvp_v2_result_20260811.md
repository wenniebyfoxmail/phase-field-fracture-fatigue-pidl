# LTPP owner-corner carrier render MVP v2 result — 2026-08-11

## Status

`EXPLORATORY_OWNER_CORNER_CARRIER_RENDERED__NOT_QUALIFIED`

Engineering carrier completion: `PASS`.

Spatial-registration qualification: `NOT_ASSESSED`; v1 remains
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Correction from render v1

Render v1 used an invalid 15.24 m × 4.572 m target and is retained as
`EXPLORATORY_RENDER_INVALID_COORDINATE_CONVENTION__NOT_QUALIFIED`. V2 changed
only the target carrier to the project-wide `[0,15.24] × [0,5.00] m`,
`1524 × 500 px`, nominal `0.01 m/px` convention. The eight locked owner corners
were not changed.

## Execution evidence

The immutable local package is:

`local_archive/real_road_acquisition/ltpp_06_1253_owner_corner_carrier_render_mvp_v2_20260811/`

| Asset | SHA-256 |
|---|---|
| `manifest.sha256` | `bccd00a633d5e79c5532748dd298a8d96d79cd243d9989d9318b12c3c8ff6591` |
| `mvp_result.json` | `689e8cc24a5e69b23c36c4921a4212fe506e40c761f8ea5d3fa4326037457460` |
| `registered_contact_sheet.png` | `99debbc60dc05ebb1d7555e2d702022abb922b48e77ae2af3e5cdaefddffb619` |
| `target_grid_overlay_contact_sheet.png` | `fc37e91ec509d6848a12d786953a60fc2de6774bf745bdca576546e9194ef8ba` |
| `adjacent_red_cyan_contact_sheet.png` | `2a3cc39635f7880b477b4d6d58d6cf861d8bf54823202bd5124f86bff65c0089` |
| `per_date_structural_qc.csv` | `e4d17aff8a81407cbdeb0b8f87860399e8cd97bdf452e5b18849c7f7d0042da3` |

All 55 manifest entries recomputed without mismatch. All 26 PNG assets have
same-stem figure sidecars. The combined corner-collector and carrier-renderer
test selection passed `9/9` without warnings.

## Structural and visual findings

- All `8/8` dates rendered at exactly `1524 × 500 px`.
- Every homography was finite and had positive centre orientation; the minimum
  centre Jacobian determinant was `0.4621312916`.
- Maximum construction-corner reprojection was
  `1.7089771980e-13 px`, floating-point roundoff only.
- The eight accepted physical frames are complete with no visible flip or
  boundary crop.
- On the target-grid contact sheet, 0.5 m green and 1.0 m orange references
  broadly coincide with the printed metric grid; there is no obvious
  large-scale frame or orientation mismatch.
- Adjacent red/cyan views retain local coloured fringes. These can arise from
  scan resolution, line style, paper/nonlinear distortion, handwriting,
  distress changes, or residual registration error and are not interpreted as
  crack growth.

## Claim boundary

The same four owner-visible corners construct each homography and cannot
validate it. This MVP reports no independent median, p95, or maximum physical
error and did not run the v2 final gate. It proves that the full engineering
loop and physical carrier are usable for further registration development; it
does not authorize crack-tip tracking, 2-D prediction, CNN/GNN/PIDL training,
or a `SPATIAL_REGISTRATION_QUALIFIED_FOR_2D_MODEL` claim.

## Next discriminator

Use independently adjudicated, non-damage Tier A/B controls to measure internal
physical residuals on all eight dates. If complete independent controls cannot
be established, stop at
`INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`. Do not tune against the
owner-corner construction residual or the adjacent red/cyan figures.
