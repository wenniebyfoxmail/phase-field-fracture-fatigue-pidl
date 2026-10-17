# LTPP cross-state single-owner line annotation preregistration — 2026-08-12

## Status

`REVISED_PENDING_EXTERNAL_APPROVAL__DO_NOT_ANNOTATE`

## Purpose and claim boundary

One owner records the geometry of 11 vertical and 6 horizontal printed grid
lines on each of 14 source maps. The program mechanically derives 66 line
intersections. The output is permanently classified
`EXPLORATORY_SINGLE_OWNER_LINE_ANNOTATION__NOT_INDEPENDENT` and supports only
source-observability and development diagnostics.

It is not two-person Tier B consensus, independent or final controls,
registration qualification, or authorization for transform fitting, a final
audit, or a 2-D crack model. The untouched 66-point owner packet remains
historical and no record is migrated from it.

## Annotation work

Each map contains `V0..V10`, ordered left to right, and `H0..H5`, ordered
bottom to top. Every line receives exactly one status:

- `usable`: exactly two owner clicks on widely separated visible portions of
  the same printed line centre;
- `missing_print`;
- `occluded`;
- `ambiguous`.

Only printed grid, frame, and coordinate-tick ink may identify a line. Crack,
handwriting, WIM, repair, distress, circle, arrow, or other annotation ink is
forbidden evidence.

For `usable` vertical lines, `abs(dy) > abs(dx)` and `abs(dy)` must be at least
50% of the frozen automatic rectangle height. For usable horizontal lines,
`abs(dx) > abs(dy)` and `abs(dx)` must be at least 50% of its width. Failure
blocks map locking.

## Derived intersections

Each usable two-point line is represented in homogeneous source-pixel
coordinates. `G[i,j]` is computed only when both `Vi` and `Hj` are usable.
The result is `invalid_derived` if the homogeneous denominator has absolute
value below `1e-9`, any coordinate is non-finite, or the intersection lies
outside the automatic rectangle by more than 3 source pixels. There is no
snapping, replacement, repair, or extrapolation from an unusable line.

At the rectangle centre cross-section, vertical lines must be strictly ordered
left to right and horizontal lines strictly ordered bottom to top. Same-family
crossing, duplicate lines, non-finite values, or an ordering failure blocks
map locking.

Every valid point is labelled `derived_from_single_owner_lines`; this is a
mathematical line intersection, not a directly observed local grid centre.

## Fixed local spot-check

The owner classifies, without another coordinate click, exactly these eight
derived locations:

`G[0,0]`, `G[10,0]`, `G[0,5]`, `G[10,5]`, `G[2,2]`, `G[8,2]`, `G[2,3]`,
and `G[8,3]`.

Each receives one status:

- `locally_visible`;
- `locally_occluded`;
- `locally_ambiguous`;
- `missing_print`.

These eight positions are development-only spot checks and do not retain or
acquire a `final` role. A non-visible result leaves the mathematical line
intersection available but marks it
`derived_geometry__local_print_not_verified`; it cannot support a local
observability claim or enter an independent-control record.

## Lock and stop rules

A map can lock only when all 17 lines and all eight spot checks are reviewed,
all usable lines satisfy orientation/span rules, and all family-order checks
pass. Missing, occluded, or ambiguous lines deterministically invalidate their
affected intersections. No map may be deleted. Locked records are immutable.

## Required tests before real annotation

Perfect rectangle, mild perspective, family-order reversal, same-family
crossing, duplicate points, short span, near-parallel intersection,
out-of-bounds intersection, unusable-line propagation, source/crop coordinate
round trip, and a locally occluded fixed spot check that must not be labelled
locally observed.
