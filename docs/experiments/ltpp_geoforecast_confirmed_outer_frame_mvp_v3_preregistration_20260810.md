# LTPP confirmed-page outer-frame MVP v3 — preregistration

## Status

`EXPLORATORY_CONFIRMED_OUTER_FRAME_MVP_V3__NOT_REGISTRATION`

This is a new engineering model after v2 produced candidates for only 17/40
owner-confirmed map pages.  It does not modify or rescue v2 outputs.

## Frozen input

Use exactly the same 40 owner-confirmed map pages frozen in v2: 1991 pages
06–10; 1995, 1997, 1998, 2001, 2003, and 2007 pages 04–08; 2012 pages 03–07.

## Fixed model

Apply Canny edges and probabilistic Hough lines.  Retain near-vertical segments
at least 22% of page height and near-horizontal segments at least 10% of page
width.  Cluster coordinates within 8 pixels and retain at most the 28 longest
per axis, breaking ties by coordinate.

Enumerate rectangles with width 13–42% of page width, height 38–90% of page
height, and aspect ratio 1.55–5.0.  Each rectangle must contain at least four
other detected lines in each axis.  The frozen score is `200 × page-area
fraction + 500 × mean four-edge ink support + interior vertical count +
interior horizontal count`; edge support therefore outranks a larger rectangle
that splices a summary table onto a map.

Select a non-overlapping left/right pair only when widths agree within 35%,
heights within 15%, and top/bottom coordinates within 8% of page height.  Use
the highest combined score with deterministic coordinate tie-breaking.  Green
is P1, magenta P2; otherwise output `NO_PAIR`.

## Boundary

No v2 candidate, crack, distress, handwriting, WIM, repair, date comparison,
or manual box is used.  No selected rectangle becomes a crop or registration
input.  No controls, transforms, residuals, or qualification decisions are
produced.  Run once after synthetic tests and preserve all 40 outputs.
