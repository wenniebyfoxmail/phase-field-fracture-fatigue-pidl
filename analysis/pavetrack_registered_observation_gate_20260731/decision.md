# PaveTrack provenance, split and registration gate

## Verdict

**Provenance counts reconciled and a location-isolated split is frozen. Pairwise
image-space registration is partial (18/21); mechanical assimilation
and RUL remain blocked.**

The workbook has 9,447 annotation rows. Removing 200 exact duplicate
location-image-category rows gives the manifest's 9,247 rows. These represent
8,928 unique location-image pairs. The old report's 8,625 image count is the
filename-only count and incorrectly merges 303 names reused at different
locations. The workbook and manifest triple sets are otherwise identical.

The deterministic location split contains 118
train, 23 validation and
24 test locations. No location crosses splits and
all four distress categories occur in every split.

Sequential SIFT/RANSAC registration passed 18/21 sampled transitions
under the predeclared match, inlier, reprojection and projected-area gates.
Failed transforms remain explicit missing registration; they are not imputed.
Even passing transforms are only between consecutive pixel frames. No physical
scale, timezone, model-coordinate registration, load, environment or measured
maintenance channel exists, so the result cannot support hidden-state,
mechanism or remaining-life claims.
