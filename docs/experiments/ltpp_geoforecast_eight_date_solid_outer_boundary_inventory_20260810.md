# LTPP eight-date solid outer-boundary inventory — 2026-08-10

## Status

`EXPLORATORY_SOLID_OUTER_BOUNDARY_INVENTORY__NOT_QUALIFIED`

## Mechanism question

Can the already accepted 1991 outer-solid-rectangle rule consistently identify the road-map range on the original 0–50 ft page of each of the eight v1 dates, before any crop or grid-control candidate extraction?

## Frozen method

The inventory imports `ltpp_review_1991_solid_outer_boundary.py` without changing its deskew estimator, ink threshold, five-pixel support band, continuous-support thresholds, central-page search bounds, or `[3.0, 3.6]` aspect range. For each date it renders an orange O1–O4 rectangle and records the measured source-space range and support lengths.

The only reviewer question is whether orange encloses the road grid and nearby crack ink while excluding page header/side-table material. Crack geometry is not an input to rectangle selection.

## Predeclared scope and stop rule

- Sources: the original official `segment_0_50_white.png` page for each v1 date only.
- No range is altered after seeing a review image during this inventory run.
- Any disputed date stops the next control-candidate stage for that date; it does not authorize tuning to obtain an apparently better range.
- A visually accepted range permits only a later exploratory grid-control-candidate diagnostic. It does not authorize cropping for science, registration fitting, a v2 final audit, or a 2-D model.

## Output

The local evidence package contains eight source-range review PNGs, sidecars, per-date metrics, SHA-256 input/code receipt, a decision note, and a package manifest.

## One-shot inventory observation

The fixed rule was executed once against all eight pages. Seven dates yielded a candidate for human range review; `19980407` yielded `NO_CANDIDATE__FAIL_CLOSED`. The candidate ranges are not silently accepted: `20030514` and `20071106` visibly demonstrate why a numerical candidate must still be reviewed before any later use. The range rule has not been altered in response.

Only `19910610` has an owner-confirmed range review so far. The next action is to record accept/reject feedback on the remaining seven full-resolution orange-frame panels. This does not alter the independent-control requirement for v2.
