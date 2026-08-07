# LTPP same-date printed-layout availability diagnostic — 2026-08-07

## Question

For each of the eight 06-1253 dates, does the official viewer provide enough
additional same-date 50-ft pages to determine whether poor 0–50 ft grid
observability is local to that page or systematic for the entire date?

## Fixed read-only method

Use all ten official segment pages (0–50 through 450–500 ft) per date. Alpha
composite each two-colour transparent PNG to white in memory; use the frozen
rectifier's existing deskew, line-position, and regular-rectangle rules. A
page has dense printed-grid evidence only with at least 8/11 vertical and 5/6
horizontal matches. No transform, crack label, distress mark, WIM mark, repair
mark, or cross-date image data is used.

## Interpretation boundary

This can establish only same-date *layout observability*. It cannot transfer a
control point from a different physical 50-ft segment into 0–50 ft, and cannot
prove a cross-date registration. Its value is diagnostic: it distinguishes
page-level missing grid from a date whose source delivery has no usable
vertical printed grid anywhere.

## Output

The evidence package stores per-page and per-date tables, input-code hashes,
decision note, and a manifest. It is recorded in the spatial-registration
track but does not alter the 2-D eligibility state.
