# LTPP spatial-registration v2 Tier B annotation protocol

## Status and scope

`PENDING_MINIMAL_REVISION_REVIEW`

This protocol collects independent printed-grid geometry only. It neither fits
a transform nor audits registration quality. It applies only after the revised
v2 preregistration has external approval.

## Roles and blindness

Two human annotators, `A` and `B`, work independently. Neither may be the
registration implementer, the external protocol reviewer, or anyone who has
seen v1 residuals, v1 date-level outcomes, v1 candidate overlays, final v2
controls, crack evolution across dates, or any future-date image. The user has
already seen v1 outcomes and therefore must not serve as a final-control
annotator. A separate annotation custodian holds the final-control records.

Each annotator receives one redacted, date-coded source image at a time. They
may inspect only that one image at a fixed 400 percent zoom and may not compare
it with another date. The packet excludes the v1 detector output, all crack
labels, WIM/repair overlays, and any residual or qualification information.

## Candidate universe and allowed evidence

The candidate universe is exactly `G[i,j]` for `i=0..10`, `j=0..5`: the
printed-grid intersections corresponding to the stated `15.24 m x 5.00 m`
survey frame. The annotator may use only printed grid ink, printed road/frame
boundaries, and printed coordinate ticks to locate a candidate. Handwriting,
distress strokes, WIM boxes, repair boxes, circles, arrows, and severity marks
are excluded evidence and may not be used to infer a centre.

## Single-annotator record

For each candidate, each annotator records exactly one of:

- `usable`: one source-pixel click at the intersection of the printed vertical
  and horizontal centre lines;
- `missing_print`: the required printed lines are absent or too faint;
- `occluded`: a forbidden mark covers any part of the centre or the immediate
  printed support needed to locate it;
- `ambiguous`: more than one plausible printed centre remains after applying
  this protocol.

The centre is the crossing of the midlines of the two printed grid strokes.
For each stroke, the midline is the halfway position between its two visible
outer ink edges, judged within a 12-source-pixel arm extending away from the
candidate centre. A candidate is `occluded` if a forbidden mark overlaps the
centre or any of the four required 12-pixel arms. If the centre cannot be
placed from all four visible arms, it is `missing_print` or `ambiguous`; no
extrapolation through an occlusion is permitted.

## Consensus, missingness, and tie rule

An eligible Tier B point requires both annotators to record `usable` and their
two clicks to lie within `4.0` source pixels of each other. Its stored pixel
coordinate is the arithmetic mean of their clicks. Every other combination is
deterministically `missing_or_ambiguous` with the paired reason codes retained.
There is no third-person rescue, majority vote, coordinate snapping, manual
completion, or replacement candidate.

The annotation custodian applies this rule mechanically before releasing only
the fit and development records to the implementer. Final-control coordinates,
reason codes, and images remain withheld until the single final gate.

## Quality receipts

The custodian writes an immutable CSV/JSON receipt containing candidate ID,
annotator statuses, both source-pixel clicks when usable, consensus status,
stored coordinate, reason codes, source hash, protocol hash, and packet hash.
For every usable point, the receipt includes a source-image crop for later
manual verification. The receipt contains no transform, crack geometry, or
cross-date comparison.

## Failure condition

If any date lacks every required development or final candidate, lacks eight
non-collinear fit controls, or cannot preserve final-control blinding, the
route terminates as `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`.
