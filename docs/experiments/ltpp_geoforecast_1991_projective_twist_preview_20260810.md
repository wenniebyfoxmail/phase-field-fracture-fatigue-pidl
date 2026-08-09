# LTPP 06-1253 1991 projective-twist preview — 2026-08-10

## Status

`EXPLORATORY_PROJECTIVE_TWIST_PREVIEW__NOT_QUALIFIED`

## Purpose

Visually test whether 1991 needs a four-corner projective correction after rotation, using only its printed page-grid frame.

## Frozen preview rule

- Detect long near-horizontal and near-vertical page-frame strokes in the original `segment_0_50_white.png` image.
- Select the leftmost/rightmost supported vertical frame strokes and the highest/lowest full-width horizontal strokes; their intersections form a quadrilateral.
- Warp that quadrilateral to a rectangle whose dimensions are the corresponding mean source edge lengths.
- Redetect only the high-resolution printed lattice on the warped image and draw large review markers.

## Boundary

No crack geometry, crack label, WIM/repair mark, cross-date correspondence, transform fitting for science data, residual metric, or final audit is used. A visually good preview does not select homography for v2.
