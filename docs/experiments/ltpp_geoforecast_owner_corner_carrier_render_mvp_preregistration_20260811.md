# LTPP owner-corner carrier render MVP preregistration — 2026-08-11

## Purpose and classification

This is a new `EXPLORATORY_REGISTRATION_IMPROVEMENT` rendering experiment.
It consumes the visually accepted owner-corner construction controls and asks
whether all eight maps can be placed on one exact physical raster carrier
without cropping, flipping, or replacing the accepted corners.

It does not continue or rerun spatial-registration audit v1. The v1 status
remains `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Frozen input

The only control packet is:

`local_archive/real_road_acquisition/ltpp_06_1253_owner_corner_carrier_mvp_v3_20260810/`

- `owner_corners.json` SHA-256:
  `3f86fc7c0d28d578387d5e8d99295faf8e9bc4d45e437f4d1e181940e96a4803`
- `manifest.sha256` SHA-256:
  `b609aba4d3026929e8120e06ae81116cdbf1e1e898f64b403a564cacab8233f2`
- eight-date review contact sheet SHA-256:
  `0b27239519f6aefe86c88eeee3ee4a17c938aab48583337557d042286de631f5`

All eight records are locked. The owner explicitly accepted the eight cyan
outer frames in
`docs/reviews/ltpp_geoforecast_owner_corner_carrier_visual_acceptance_20260811.md`.

## Frozen physical raster convention

The printed frame is exactly 50 ft × 15 ft, equal to 15.24 m × 4.572 m.
Use an isotropic scale of exactly 30 pixel intervals per foot:

- output width: 1501 pixels, representing coordinates 0 through 1500;
- output height: 451 pixels, representing coordinates 0 through 450;
- scale: 0.01016 m per pixel interval in both axes;
- source point order: `TL, TR, BR, BL`;
- target array coordinates: `(0,0), (1500,0), (1500,450), (0,450)`;
- physical x increases left to right from 0 to 50 ft;
- physical y increases bottom to top from 0 to 15 ft, while array row
  increases downward.

The endpoint convention avoids the prior exploratory 5.00 m height error and
places both physical endpoints exactly on pixel centres.

## Frozen transform and rendering

For every date, estimate exactly one four-point projective homography with
`cv2.getPerspectiveTransform`. Render with `cv2.warpPerspective`,
`INTER_LINEAR`, white constant border, and the fixed 1501 × 451 output size.
No model ladder, feature matching, crack shape, WIM, repair, distress mark, or
cross-date image information is allowed.

No corner may be replaced after rendering. If any source hash, manifest entry,
corner order, locked flag, finite-matrix check, positive centre orientation,
output dimension, or corner reprojection check fails, stop without output
qualification.

## Frozen outputs and visual checks

Produce:

- eight registered source maps;
- eight target-grid reference overlays;
- a registered contact sheet;
- a target-grid-overlay contact sheet;
- seven adjacent-date red/cyan overlays, where previous-only ink is red,
  current-only ink is cyan, and coincident ink is dark;
- an adjacent-pair contact sheet;
- per-date structural QC;
- same-stem figure sidecars, result/decision documents, and `manifest.sha256`.

Visual acceptance asks only whether the physical frame is complete, orientation
is correct, and printed grid lines have no obvious large-scale mismatch,
folding, or non-physical stretch. The red/cyan views are registration-diagnostic
visuals, not crack-growth measurements.

## Allowed result

The strongest allowed status is
`EXPLORATORY_OWNER_CORNER_CARRIER_RENDERED__NOT_QUALIFIED`.

Corner reprojection is a construction check because the same points create the
homography. No independent median, p95, or maximum physical registration error
is computed. The final v2 gate is not run and the 2-D model route remains
closed.
