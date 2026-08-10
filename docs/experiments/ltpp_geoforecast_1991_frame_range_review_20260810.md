# LTPP 1991 frame-range review — 2026-08-10

## Status

`EXPLORATORY_FRAME_RANGE_REVIEW__NOT_QUALIFIED`

## Purpose

Confirm the complete road-grid extent before any clipping. The previous strict-control preview is not used to define the range because its detected inner frame may omit valid road-map content.

## Frozen candidate construction

- Purple `I1–I4`: the prior long-frame candidate.
- Orange `O1–O4`: the outermost supported long, near-horizontal/vertical solid-line rectangle in the original source page, restricted to the page's central road-map region.
- Neither candidate uses crack geometry, crack labels, WIM, repair marks, tables, or cross-date information.

## Required human decision

Select a candidate only if it encloses all actual road-grid content (including cracks near the boundary) and excludes page margins/side summary tables. If neither is correct, report which boundary is too far in/out. No control points or registration transform may be generated before this is resolved.
