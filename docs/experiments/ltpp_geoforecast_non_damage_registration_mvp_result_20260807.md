# LTPP 06-1253 non-damage registration MVP result — 2026-08-07

## Result

`EXPLORATORY_REGISTRATION_MVP__NOT_VALIDATED_FOR_2D_MODEL`

The eight-date non-damage registration delivery path is implemented and
executed, but the available source controls do not validate an eight-date
physical registration. This is a new exploratory MVP result; it does not
amend, rerun, or conceal the terminal v1 result
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## What ran successfully

The page-frame-only MVP rendered all eight 0–50 ft official maps to a common
15.24 m x 5.00 m, 1524 x 500 px canvas with a fixed y-down convention. Its
package contains all registered images, source-frame overlays, grid overlays,
temporal views, per-date structural QC, code/input hashes, and verified
manifests:

- `local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_mvp_20260807_code_receipt/`;
- `local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_mvp_temporal_views_20260807/`.

This proves an auditable image delivery path only. Four page-frame corners
construct the transform, so their near-zero reprojection residual is not an
independent physical-registration error.

## Fixed Tier-C grid diagnostic

The follow-up used only printed-grid candidates (no crack, WIM, repair,
handwritten, or distress geometry). All 66 logical grid intersections were
constructed from 11 longitudinal and 6 transverse printed lines. The 16 v2
reserved positions were excluded; the remaining fixed split was 42 fit and 8
development controls. The single predeclared ladder was diagonal affine, then
full affine, then homography only after a simpler development failure.

| Date | First selected model | Best evaluated final ladder result | Why it is not validation |
|---|---|---|---|
| 1991 | none | homography p95 0.106 m | exceeds 0.10 m diagnostic limit |
| 1995 | none | homography p95 0.267 m | systematic weak vertical grid |
| 1997 | none | homography p95 0.263 m | exceeds diagnostic limit |
| 1998 | none | homography p95 0.146 m | exceeds diagnostic limit |
| 2001 | none | homography p95 0.216 m | exceeds diagnostic limit |
| 2003 | none | homography p95 0.222 m | exceeds diagnostic limit |
| 2007 | none | homography p95 0.130 m | exceeds diagnostic limit |
| 2012 | diagonal affine | median 0.017, p95 0.029, max 0.029 m | Tier-C controls are non-independent |

The full metric table, extracted control candidates, transformed images where
a diagnostic model was selected, and manifest are in
`local_archive/real_road_acquisition/ltpp_06_1253_exploratory_tier_c_grid_registration_mvp_20260807_code_receipt/`.

## Source-observability boundary

All ten official 50-ft pages per date were inspected without fitting a
cross-date transform. This separates a bad 0–50 ft page from a date whose
entire source delivery lacks a usable vertical printed grid:

| Date | Dense-grid official pages | Interpretation |
|---|---:|---|
| 1991 | 10/10 | consistent printed-layout candidate |
| 1995 | 0/10 | no date-level vertical-grid support |
| 1997 | 10/10 | consistent printed-layout candidate |
| 1998 | 8/10 | partial layout candidate |
| 2001 | 5/10 | partial layout candidate; 0–50 loss is not uniquely date-wide |
| 2003 | 10/10 | consistent printed-layout candidate |
| 2007 | 10/10 | consistent printed-layout candidate; 0–50 loss is not uniquely date-wide |
| 2012 | 10/10 | consistent printed-layout candidate |

The official source PNGs have only transparent background and black ink; they
contain no separable printed-grid/annotation layer. Same-date pages have
different physical 50-ft segments, so they may diagnose print visibility but
cannot donate a control point to the 0–50 ft map.

The evidence package is
`local_archive/real_road_acquisition/ltpp_06_1253_registration_layout_inventory_20260807/`.

## Decision and next condition

The current source permits a repeatable exploratory pipeline but does not
establish physical 2-D registration for all eight dates. In particular, 1995
has no source-proven internal x reference across any of its ten official pages;
page corners plus horizontal grid cannot prove interior longitudinal alignment.

The only evidence-changing next inputs are either:

1. independent measurement/chainage/fiducial data for 1995; or
2. independently annotated non-damage grid, boundary, tick, or chainage
   controls under the already approved v2 availability protocol.

Until one of those exists for every date, this result cannot open the 2-D
crack-position, continuation-tip, or prediction route.
