# LTPP owner-corner carrier render MVP v2 preregistration — 2026-08-11

## Amendment scope

MVP v1 is retained as
`EXPLORATORY_RENDER_INVALID_COORDINATE_CONVENTION__NOT_QUALIFIED`. V2 changes
only its target physical/raster convention. The eight frozen source images,
locked owner corners, homography method, interpolation, visual outputs,
fail-closed checks and claim boundaries are unchanged.

## Frozen target convention

Use the project-wide coordinate extent `[0,15.24] × [0,5.00] m` with the
existing downstream raster convention:

- output array: 1524 columns × 500 rows;
- nominal cell scale: 0.01 m/pixel;
- source order: `TL, TR, BR, BL`;
- OpenCV target corner centres: `(0,0), (1523,0), (1523,499), (0,499)`;
- x increases left to right; physical y increases bottom to top while array
  row increases downward;
- target-grid visualization: 0.5 m green intervals and 1.0 m orange intervals,
  plus the 15.24 m right boundary.

This matches the frozen v1/v2 registration, vectorization and recognition
coordinate system. It must not be changed after viewing v2 output.

## Outcome and claim boundary

The strongest permitted status remains
`EXPLORATORY_OWNER_CORNER_CARRIER_RENDERED__NOT_QUALIFIED`. Construction-point
reprojection cannot validate the homography. No independent error metrics or
final gate are run, and the 2-D model route remains closed.
