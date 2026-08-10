# LTPP eight-date solid outer-boundary inventory result — 2026-08-10

## Result

`EXPLORATORY_SOLID_OUTER_BOUNDARY_INVENTORY__NOT_QUALIFIED`

The unchanged 1991-accepted outer-solid-rectangle rule was applied once to the original official 0–50 ft page for each v1 date. It produced seven orange candidates and one explicit fail-closed no-candidate result. This is not a registration result.

| Date | Rule result | Range (deskewed source pixels) | Aspect |
|---|---|---:|---:|
| 19910610 | owner accepted; small visible deviations retained | 2370 × 694 | 3.4150 |
| 19951024 | pending review | 1967 × 654 | 3.0076 |
| 19970228 | pending review | 2039 × 645 | 3.1612 |
| 19980407 | `NO_CANDIDATE__FAIL_CLOSED` | — | — |
| 20010913 | owner rejected; `y=0–0.5 m` is clipped | 2046 × 580 | 3.5276 |
| 20030514 | owner rejected; overall range is wrong | 369 × 110 | 3.3545 |
| 20071106 | owner rejected; overall range is wrong | 942 × 288 | 3.2708 |
| 20120417 | owner rejected; left boundary is wrong | 2316 × 713 | 3.2482 |

## Evidence

The immutable local package is `local_archive/real_road_acquisition/ltpp_06_1253_eight_date_solid_outer_boundary_inventory_v4_20260810/`. It includes full-size review PNGs and sidecars, `per_date_boundary_metrics.csv`, `input_and_code_receipt.sha256`, `manifest.sha256`, and `decision.md`.

## Interpretation and next action

No candidate is a permitted crop, control point, or registration transform. Owner review accepted only 1991 and rejected the 2001, 2003, 2007, and 2012 candidates; 1995 and 1997 remain pending, while 1998 is fail closed. A rejection remains a source-range limitation; it does not authorize post-hoc threshold tuning. Any follow-up must use a separately preregistered method, then obtain review before execution. v2 still requires independent Tier A/B controls before its final gate.
