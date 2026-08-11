# LTPP geometry-assisted development8 MVP v2 preregistration — 2026-08-11

## Status

`EXPLORATORY_DEVELOPMENT8_REGISTRATION_MVP__NO_FINAL_GATE`

This is a separately named reduction of the 66-point geometry-assisted pilot.
One date in the old pilot was already reviewed before this document was
frozen; that record is preserved and is not copied into this experiment.

## Frozen construction and check points

The same four owner-accepted outer-frame corners construct one projective
homography per date. The only user-reviewed points are the eight development
identities already frozen in the original v2 protocol:

`G[5,0]`, `G[5,5]`, `G[0,2]`, `G[0,3]`, `G[10,2]`, `G[10,3]`, `G[3,1]`,
and `G[7,4]`.

No final-audit identity is displayed or evaluated. No point may be replaced,
added, or removed after review begins.

## Interaction and missingness

The projective construction supplies one suggestion per point. The user must
accept it, click the visible printed-grid intersection to move it, or record
`missing_print`, `occluded`, or `ambiguous`. Crack, distress, WIM, repair,
handwriting, and cross-date shape are prohibited evidence.

If any of the eight points on a date is not `usable`, that date receives no
complete development metric and is reported fail-closed as
`DEVELOPMENT8_INCOMPLETE`.

## Frozen exploratory metric

For a usable click, add the deterministic crop origin to recover source-pixel
coordinates. Apply the already constructed source-to-physical homography and
compare with the candidate's exact physical coordinate
`(15.24*i/10, j)` metres. Compute Euclidean error in metres, then:

```python
median = numpy.median(errors)
p95 = numpy.quantile(errors, 0.95, method="linear")
maximum = numpy.max(errors)
```

The existing engineering numbers `0.05`, `0.10`, and `0.20 m` may be shown as
fixed diagnostic references only. Passing them on these exposed development
points is not registration qualification.

## Outputs and claim boundary

After all dates are locked, produce per-point coordinates/errors, per-date
median/p95/maximum/missing counts, and source-image error-arrow overlays with
same-stem sidecars and SHA-256 receipts.

The strongest possible label is
`EXPLORATORY_DEVELOPMENT8_WITHIN_ENGINEERING_THRESHOLDS__NOT_QUALIFIED`.
This experiment cannot supply independent controls, reveal or use final
controls, select or tune a model, run the one-shot gate, or authorize a 2-D
model. A failure cannot trigger point replacement or a different transform.
