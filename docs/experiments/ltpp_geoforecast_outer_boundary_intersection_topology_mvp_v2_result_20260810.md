# LTPP outer-boundary / intersection-topology MVP v2 — result, 2026-08-10

## Status

`EXPLORATORY_OUTER_FRAME_TOPOLOGY_TOOLING_MVP__NOT_QUALIFIED`

This is an independent, development-only negative tooling result. It neither
overwrites nor changes the completed v1 decision
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`. It creates no crop, control
point, registration transform, residual, final audit, or 2-D-model authority.

## Frozen protocol and verification

- The revised protocol was re-reviewed as `APPROVE_TOOLING_MVP`; see
  `../reviews/ltpp_geoforecast_outer_boundary_intersection_topology_mvp_v2_external_re_review_20260810.md`.
- The single approved primitive chain was `img2table==2.0.0` internal
  `identify_straight_lines`, with the fixed BGR-to-gray adaptive threshold,
  `char_length=11`, and fixed image-size minimum line rule. It used no OCR,
  crop, deskew, text semantics, crack, WIM, repair, distress, manual point, or
  cross-date input.
- The final synthetic package passed all 21 visual fixtures and all 21 exact
  threshold checks before the real pages were read. Its `remote_intersection_corner`
  adversary initially exposed an invalid smaller-frame fallback; that failed
  synthetic package is retained separately. The fixture was made unambiguous,
  tests were rerun, and a new immutable synthetic package passed before the one
  real execution.
- The test module contains five passing regression tests, including exact
  boundary semantics, an exact-ranking tie, and the no-OCR/no-alternative-line
  detector restriction.

## One real development run

All eight already-seen development pages were executed exactly once under the
frozen source. Every page failed closed: it had detected horizontal/vertical
primitives but no rectangle satisfying all observed-side support, aspect,
corner, and distributed-local-crossing conditions.

| Date | horizontal sides | vertical sides | eligible rectangles | result |
|---|---:|---:|---:|---|
| 1991-06-10 | 11 | 4 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1995-10-24 | 9 | 4 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1997-02-28 | 11 | 7 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 1998-04-07 | 12 | 11 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2001-09-13 | 35 | 11 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2003-05-14 | 11 | 11 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2007-11-06 | 9 | 17 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |
| 2012-04-17 | 14 | 14 | 0 | `NO_CANDIDATE__FAIL_CLOSED` |

This negative result is informative: the scans contain grid-like primitives,
but not a fully observed, uniquely rankable four-sided physical frame under
this rule. It is not evidence that the drawn road grid is absent, nor evidence
that any page has been registered.

## Evidence package

The immutable real-page package, including original-size review panels,
`per_date_metrics.csv`, input/code receipts, dependency receipt, `decision.md`,
and `manifest.sha256`, is:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_outer_boundary_intersection_topology_mvp_v2_20260810/one_shot_real_development_run
```

Its manifest SHA-256 is
`f7d2602cbc23e80e07113e5ad8505e3dbc880912944122751f71972718140f62`.

The passed final synthetic package is the sibling directory
`synthetic_threshold_complete_r2`; the preceding failed synthetic package is
retained as `synthetic_threshold_complete` and must not be treated as a result.

## Consequence

This exact outer-frame/topology recipe is exhausted and must not be tuned or
rerun. The scientific registration route remains the separate independent
Tier A/B control-availability path; without independently withheld physical
controls, no algorithmic candidate box can reopen the 2-D route.
