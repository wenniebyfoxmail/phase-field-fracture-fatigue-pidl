# LTPP cross-state spatial-registration Tier B packet amendment — 2026-08-12

## Status

`FROZEN_PENDING_EXTERNAL_REVIEW__DO_NOT_ANNOTATE`

This is a collection-only extension candidate for `27-6251 c3` and
`08-1053 c2`. It does not reopen the terminal v1 result
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`, fit a transform, compute a
registration residual, disclose final controls, or authorize a 2-D model.

## Mechanism question

Do the 6-date Minnesota and 8-date Colorado source maps contain enough
independently adjudicated, non-damage printed geometry to make a future frozen
registration audit possible?

## Frozen inputs

Only the two all-date automatic geometry-pass receipts are accepted:

- `27-6251 c3`: exactly 6/6 dates in `grid_gate_results.json`, SHA-256
  `21d6be554982908579caf2270c792989f7bf26f865f7413aa6975e4191777511`;
- `08-1053 c2`: exactly 8/8 dates in `grid_gate_results.json`, SHA-256
  `6abdb5fdcb67818c56b9269e94eb9f824bff0f376afeab872e2f7d3144212020`.

Every source image must match the per-date SHA-256 stored in its receipt. A
missing date, failed date, count mismatch, or source-hash mismatch terminates
packet construction. No date may be deleted or replaced.

## Narrow source-window change

For each source image, the already frozen automatic grid rectangle
`(x0, y0, x1, y1)` is used only to choose an unrectified evidence window.
Expand it by exactly 48 source pixels on every side, clip only to image bounds,
and use half-open slicing. The image is not rectified, rescaled, thresholded,
enhanced, denoised, or masked.

The automatic rectangle is a construction control, not Tier A/B evidence. It
cannot be clicked, fitted, averaged, evaluated as a residual, or used to select
a transform. Because automatic line extraction can be influenced by arbitrary
page ink, this extension requires separate external approval before annotation.

## Rules retained without change

- Candidate universe: exactly 66 printed intersections `G[i,j]`, `i=0..10`,
  `j=0..5`, at `(15.24*i/10, 5.00*j/5)` metres.
- Roles: the existing 50 fit, 8 development, and 8 final identities remain
  unchanged.
- Two eligible blind human annotators are required. Neither the user nor the
  implementer is eligible.
- Each annotator sees one map at a time and may use only printed grid, frame,
  and tick ink. Cracks, handwriting, WIM, repairs, distress marks, circles, and
  arrows are forbidden evidence.
- Consensus requires two `usable` clicks within 4.0 source pixels, followed by
  arithmetic averaging. There is no rescue, replacement, snapping, or third
  annotator.
- Section/date mappings and final-control records remain sealed until the
  existing authorization sequence permits their release.

## Stop rules

Before external approval, all records remain empty and unlocked. Annotation,
consensus, transform fitting, residual evaluation, or final-control unsealing
before approval invalidates the packet.

Approval, if granted, may authorize only independent Tier B collection and the
mechanical availability consensus. It cannot authorize transform fitting or
the one-shot final registration gate. Any date missing a required development
or final point, or fewer than eight non-collinear fit points, terminates that
section as `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL` without deleting
dates or changing the method.
