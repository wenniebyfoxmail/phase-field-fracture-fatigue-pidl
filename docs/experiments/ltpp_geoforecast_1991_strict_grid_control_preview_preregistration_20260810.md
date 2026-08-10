# LTPP 1991 strict grid-control preview preregistration — 2026-08-10

## Status

`EXPLORATORY_STRICT_GRID_CONTROL_PREVIEW__NOT_QUALIFIED`

## Reason for a new preview

The preceding native lattice output was rejected for candidate-control use: it rendered grid-family intersections outside the road frame and did not exclude local continuous-ink contamination. It remains an initialization diagnostic only.

## Frozen preview rule

1. Obtain the 1991 printed road-grid quadrilateral solely from long page-frame strokes, and warp that quadrilateral to its own rectangle.
2. Generate periodic lattice candidates only inside the warped frame; exclude a one-lattice-pitch boundary margin.
3. At each remaining candidate, inspect two noncentral arms on each axis, from 0.08 to 0.40 lattice pitches from the point.
4. Accept only if both arms on both axes contain at least two short dark runs and no run exceeds 0.14 lattice pitches. Otherwise render a red rejection cross; never repair, snap, or replace it.

## Boundary

This is one 1991 visual control-quality diagnostic. It does not select a final registration model, estimate a cross-date transform, reuse final controls, or change v1/v2 status.
