# LTPP no-OCR main-grid tooling MVP — result, 2026-08-10

## Status

`EXPLORATORY_MAIN_GRID_TOOLING_MVP__NOT_QUALIFIED`

This is a development-only negative tooling result. It does not alter the completed v1 result `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`, and it creates no crop, control point, registration transform, residual, or 2-D-model authorization.

## Protocol and execution

- The external reviewer first required revisions, then issued `APPROVE_TOOLING_MVP` for the frozen synthetic-suite-to-one-real-run sequence. See `../reviews/ltpp_geoforecast_img2table_main_grid_mvp_external_review_20260810.md` and `../reviews/ltpp_geoforecast_img2table_main_grid_mvp_external_re_review_20260810.md`.
- The `11/11` frozen synthetic fixtures passed under the final source, including large and dense summary-table adversaries, isolated repair rectangles, missing/broken separators, nested borders, exact ties, wrong aspect, and no-grid cases.
- An initial command aborted before any page-level output because an ineligible zero-width component exposed a ranking exception. It is retained in `ltpp_geoforecast_img2table_main_grid_mvp_pre_result_implementation_abort_20260810.md`; the repair adds only a sentinel for an already-ineligible component and a regression test, with no parameter or selection change. The synthetic suite was repeated after that repair before the separately named real run.

## One real development run

The final recipe used `img2table==2.0.0` only through `img2table.tables.bordered.lines.identify_straight_lines`, with no OCR, `Image.extract_tables`, `TableExtractor`, borderless-table, implicit-line, crop, deskew, transform, text, crack, WIM, repair, or manual-corner input.

| Date | detected horizontal lines | detected vertical lines | result |
|---|---:|---:|---|
| 1991-06-10 | 15 | 4 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1995-10-24 | 17 | 4 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1997-02-28 | 20 | 9 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1998-04-07 | 25 | 11 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2001-09-13 | 56 | 12 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2003-05-14 | 30 | 15 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2007-11-06 | 22 | 18 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2012-04-17 | 17 | 14 | `NO_CANDIDATE__FAIL_CLOSED` |

No page contained a single detected connected component satisfying the frozen exact `Nv=11`, `Nh=6`, `I=66` complete-lattice eligibility rule. Accordingly the diagnostic emitted no purple candidate on any date. This is the expected fail-closed behavior, not evidence that the page itself has no printed road grid.

## Interpretation

The tool successfully rejects the synthetic summary-table and rectangle failure modes but is too strict for these scanned, dashed/fragmented real grid strokes. It therefore cannot provide the requested outer-frame candidate under its frozen rule. Changing continuity, count, preprocessing, or candidate construction after seeing these outputs would be a new dated tooling experiment, not a rerun or rescue of this MVP.

The active scientific route remains independent Tier A/B control availability for v2. This negative engineering result neither closes that route nor qualifies it.

## Evidence package

The complete local package, including full-resolution per-date panels, metrics, dependency receipt, input/code SHA-256 receipt, `decision.md`, and `manifest.sha256`, is:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_main_grid_tooling_mvp_20260810/one_shot_real_development_run_after_pre_result_repair
```

The full-resolution contact sheet is `eight_date_main_grid_overview.png`. The absence of purple frames is intentional: each panel is an explicit `NO_CANDIDATE__FAIL_CLOSED` result.
