# External review — LTPP outer-boundary / intersection-topology MVP v2, 2026-08-10

## Verdict

`REVISE_TOOLING_MVP_BEFORE_RUN`

The reviewer accepted this as a genuinely different, permissible *development-only* hypothesis: it first seeks a four-sided outer frame and then tests local crossings, rather than demanding a single connected `11 x 6` interior lattice. It remains exploratory because all eight real pages have already been seen.

## Blocking items to freeze before execution

1. Use exactly one primitive detector chain, not a post-hoc choice among Hough, LSD, and `img2table` outputs.
2. Collinear side evidence may merge only with orientation deviation `<=2.0 degrees`, perpendicular displacement `<=3 px`, and along-axis gap `<=max(12 px, round(0.015 * relevant_image_dimension))`. Gaps remain unobserved support.
3. Each side needs observed-support coverage `>=0.85` and longest unsupported gap `<=0.08` of its side length.
4. Opposite-side orientation difference must be `<=2.0 degrees`; adjacent-side deviation from 90 degrees `<=3.0 degrees`; every corner must lie within both supporting observed intervals to `3 px`.
5. Apply physical aspect as a hard gate: `2.5908 <= width / height <= 3.5052` (`3.048 +/-15%`).
6. Each side must have at least four true orthogonal crossings, deduplicated at `8 px`; crossings must occur in at least three of four side-length quartiles and cannot be corners.
7. Rank eligible candidates only by `(-total_side_crossings, -min_side_crossings, -total_observed_coverage_q, -area_px, aspect_dev_q)`, with fixed `1e6` quantisation and exact-tuple `NO_CANDIDATE__FAIL_CLOSED`.
8. Freeze the listed threshold-boundary synthetic suite before a real development run.

Even a visually successful output remains exploratory and cannot create controls, authorize registration, or alter v1/v2 final-gate status.
