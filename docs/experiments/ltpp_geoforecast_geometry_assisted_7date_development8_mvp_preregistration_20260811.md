# LTPP geometry-assisted seven-date development8 MVP preregistration — 2026-08-11

## Status and scientific question

`EXPLORATORY_7_DATE_REGISTRATION_MVP__NOT_QUALIFIED`

This separately named experiment asks only whether the 1995–2012 subseries
can complete the four-corner construction plus eight exposed development-point
error loop. It excludes 1991 because its printed transverse carrier is
`0–15 ft = 4.572 m`, while the later forms use approximately `0–5 m`.

This exclusion changes the scientific question. It is not an amendment that
rescues the original eight-date gate, and it cannot erase or reinterpret the
preserved 1991 record or v1 result.

## Frozen dates and controls

The exact dates are `19951024`, `19970228`, `19980407`, `20010913`,
`20030514`, `20071106`, and `20120417`. No date may be added, replaced, or
removed after review begins.

Each date uses its already accepted four outer-frame construction corners and
exactly the pre-existing development identities:

`G[5,0]`, `G[5,5]`, `G[0,2]`, `G[0,3]`, `G[10,2]`, `G[10,3]`, `G[3,1]`,
and `G[7,4]`.

The target carrier is `[0,15.24] × [0,5.00] m`. The same geometry-assisted
suggestion, user correction, status rules, source-coordinate restoration, and
missingness rule from development8 v2 apply unchanged.

## Frozen evaluation

Only after all 7 × 8 = 56 tasks are reviewed and all seven dates are locked,
apply the fixed four-corner homography and compute each click's Euclidean
physical error from `(15.24*i/10, j)` metres. Per date report median,
`numpy.quantile(errors, 0.95, method="linear")`, maximum, and missing count,
plus error-arrow overlays and SHA-256 receipts.

The `0.05/0.10/0.20 m` values may be displayed only as diagnostic references.
No model tuning, point replacement, final controls, consensus, or final gate
is allowed.

## Allowed interpretation

Even a 7/7 within-threshold result may establish only
`EXPLORATORY_7_DATE_DEVELOPMENT8_WITHIN_THRESHOLDS__NOT_QUALIFIED`.
It cannot support 1991–2012 crack evolution, the missing 1991→1995 interval,
`SPATIAL_REGISTRATION_QUALIFIED_FOR_2D_MODEL`, or 2-D training. The original
eight-date route remains closed until a separately reviewed native-coordinate
solution handles 1991 without nonphysical stretching.
