# LTPP owner-confirmed map-panel MVP v2 — preregistration

## Status

`EXPLORATORY_CONFIRMED_MAP_PANEL_MVP_V2__NOT_REGISTRATION`

This is a new engineering visualization after panel MVP v1.1 failed.  It does
not reuse or repair any v1.1 rectangle and does not change the closed spatial
registration v1 result.

## Owner-confirmed source pages

The owner visually reviewed the complete PDF contact sheets and confirmed the
only eligible map-page ranges:

| Date | PDF pages |
|---|---|
| 1991-06-10 | 06–10 |
| 1995-10-24 | 04–08 |
| 1997-02-28 | 04–08 |
| 1998-04-07 | 04–08 |
| 2001-09-13 | 04–08 |
| 2003-05-14 | 04–08 |
| 2007-11-06 | 04–08 |
| 2012-04-17 | 03–07 |

Exactly these 40 rendered pages are read.  There is no page substitution,
ranking, or deletion.

## Fixed panel rule

Threshold ink with Otsu.  Close 11-pixel gaps independently in each axis, then
retain horizontal strokes at least `max(45 px, 5.5% page width)` and vertical
strokes at least `max(110 px, 10% page height)`.  Connect nearby grid strokes
with fixed 7-pixel dilation and 15-pixel closing.

Candidate connected components must be 13–48% of page width, 38–90% of page
height, and have height/width 1.55–5.0.  A pair must be non-overlapping,
left-to-right, agree in width within 35%, height within 20%, and top/bottom
position within 10% of page height.  Select the highest component-area pair,
breaking ties by left coordinates.  Green is P1 and magenta is P2.

If no pair satisfies the rule, the page is `NO_PAIR`.  There is no manual
completion or parameter change after the 40-page run.

## Claim boundary and stop rule

The method uses only long orthogonal printed-grid geometry.  It does not use
crack, distress, handwriting, WIM, repair, date correspondence, or another
page to choose a pair.  Outputs are visual candidates only: no crop becomes a
registration input, no control point is extracted, no transform is fit, and no
registration error or qualification status is computed.

Run synthetic tests, then execute the fixed 40-page input once.  Report every
page and preserve every failure.  Even 40/40 candidate output cannot alter
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.
