# LTPP cross-state single-owner grid annotation — 2026-08-12

## Status

`SUPERSEDED_UNUSED_BY_LINE_ANNOTATION__NOT_INDEPENDENT__NO_FINAL_GATE`

This point-by-point packet had 0/924 completed tasks and zero locked maps when
the owner selected the lower-labour line-based route. It remains unchanged for
provenance and must not be resumed while the line packet is active. See
`ltpp_cross_state_single_owner_line_annotation_result_20260812.md`.

## Purpose

One owner annotates all 66 printed-grid intersections on each of the six
`27-6251 c3` and eight `08-1053 c2` maps. The records support current-stage
source observability, missingness, and development diagnostics.

## Reused logic

- exact candidate universe `G[i,j]`, `i=0..10`, `j=0..5`;
- original `usable`, `missing_print`, `occluded`, and `ambiguous` statuses;
- source-image crop and source-pixel coordinate convention;
- existing geometry-assisted interface, including projective suggestions,
  row/column guides, click correction, draft save, and date lock;
- original rule that crack strokes, handwriting, WIM, repair and distress marks
  are not printed-grid evidence.

The frozen automatic rectangle supplies only the four-corner projective
suggestion and evidence window. The owner must accept or correct every point.

## Claim boundary

The user is the sole annotator and has seen prior outcomes. These records are
therefore `exploratory_single_owner` controls. They may be used for current
development/availability summaries but are not two-person Tier B consensus,
independent final controls, or registration qualification. They cannot by
themselves authorize transform selection, the one-shot final audit, or any 2-D
crack model.

The immutable two-person packet remains unchanged and may be retained as an
optional future validation route. No owner click may be copied into it.

## Completion rule

Every one of the 14 maps must contain a non-`unreviewed` status for all 66
points and must be explicitly locked. No date deletion or automatic acceptance
of an entire map is allowed.

The reused interface supports keyboard review: `A` accepts the displayed
suggestion and advances; `1/2/3/4` records usable/missing/occluded/ambiguous and
advances; arrows or `N/P` move between points; `S` saves the current date.
