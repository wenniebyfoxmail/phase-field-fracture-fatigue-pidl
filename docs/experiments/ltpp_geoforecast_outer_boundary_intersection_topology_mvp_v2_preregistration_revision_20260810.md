# LTPP outer-boundary / intersection-topology MVP v2 — revised preregistration, 2026-08-10

## Status and scope

`EXPLORATORY_OUTER_FRAME_TOPOLOGY_TOOLING_MVP__PENDING_RE_REVIEW`

This is an independent development-only tooling experiment, not a rerun of the rejected complete-grid recipe. It is limited to candidate/`NO_CANDIDATE` overlays and structural metrics. It cannot crop a scientific input, define Tier B/final controls, fit any transform, calculate registration error, change v1, unlock v2, or train a 2-D model.

## Frozen inputs and detector

- Input: original official `<date>/segment_0_50_white.png` pixels for the eight already-seen dates, with no crop, deskew, rescale, cross-date transfer, manual point, OCR, text semantics, crack, WIM, repair, or distress input.
- Primitive detector: only the previously pinned `img2table==2.0.0` geometry function `img2table.tables.bordered.lines.identify_straight_lines`, with the same frozen BGR-to-gray, adaptive threshold, `char_length=11`, and `min_line_length=max(64, round(0.08 * min(height,width)))` call chain. No Hough, LSD, public table extractor, borderless, or implicit-line candidate is available.

## Frozen side evidence and rectangle eligibility

Same-direction detected primitives may merge into an observed-support interval union only when all hold: orientation deviation `<=2.0 degrees`, perpendicular displacement `<=3 source px`, and along-axis gap `<=max(12 px, round(0.015 * relevant_image_dimension))`. The gaps are never counted as observed support.

An outer-frame candidate consists only of two horizontal and two vertical observed side candidates. It is eligible if and only if:

1. each side has support-union coverage `>=0.85` and no unsupported gap longer than `0.08` of that side length;
2. opposite sides differ by at most `2.0 degrees`; every adjacent pair differs from 90 degrees by at most `3.0 degrees`;
3. all four finite pairwise intersections lie within both contributing observed-support intervals to `3 px`; no remote extension is allowed;
4. corners are ordered, in source bounds, and `2.5908 <= width/height <= 3.5052`;
5. every side has at least four actual orthogonal primitive crossings within `3 px` of observed support; crossings closer than `8 px` count once; corners do not count; and at least three of four parameterised side quartiles contain one crossing.

No rule may use candidate enumeration order, position, page semantics, or a manual fallback.

## Frozen ranking and output

For eligible candidates only, compute integer quantities:

```text
total_observed_coverage_q = round(1e6 * sum(four side coverages))
aspect_dev_q = round(1e6 * abs(log((width/height) / 3.048)))
rank = (-total_side_crossings,
        -min_side_crossings,
        -total_observed_coverage_q,
        -area_px,
        aspect_dev_q)
```

Choose the unique lexicographic minimum. No eligible candidate or an exact full-tuple tie is `NO_CANDIDATE__FAIL_CLOSED`. A selected candidate renders a purple boundary, source-observed side segments, and actual crossing dots; it does not crop, transform, or create controls.

## Frozen synthetic suite

Before real data, require selected/rejected synthetic assertions plus full visual panels for: fragmented canonical frame with sufficient local crossings; translation/scale; larger page frame; nested page/road frames; large/dense summary tables; underlines; oblique and near-axis long crack-like lines; WIM/repair rectangles including a large-rectangle arrangement; gap just inside and outside threshold; support just above/below 0.85; a single gap above 0.08; missing side; remote-intersection corner; crossings packed into one side region or only two quartiles; wrong-ratio rectangle; non-parallel perspective-like quadrilateral; exact tie; and no rectangle.

For every numeric threshold (`2 degrees`, `3 px`, merge gap, `0.85`, `0.08`, four crossings, `3/4` bins, `8 px`, and aspect bounds), the suite must include both boundary-side cases to fix `<=` semantics.

## One-shot rule

After re-review approval and passing synthetic tests, execute all eight pages once under this source. A later parameter or algorithm change creates a differently named experiment; it cannot rerun this v2 MVP.
