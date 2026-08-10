# LTPP eight-date outer-boundary owner visual review — 2026-08-10

## Scope

This receipt records the owner's review of the fixed-rule exploratory source-range figures in `ltpp_06_1253_eight_date_solid_outer_boundary_inventory_v4_20260810`. It does not alter that package, its hash receipt, or its frozen rule.

## Decisions received

| Date | Owner decision | Exact finding | Consequence |
|---|---|---|---|
| 19910610 | accept | Orange range is acceptable despite small visible deviations. | May be used only as an engineering range reference. |
| 20010913 | reject | The selected lower range starts at `y=0.5 m`; the physical `y=0–0.5 m` band is clipped. | Cannot enter grid-control candidate extraction. |
| 20030514 | reject | Overall selected range is wrong. | Cannot enter grid-control candidate extraction. |
| 20071106 | reject | Overall selected range is wrong. | Cannot enter grid-control candidate extraction. |
| 20120417 | reject | Selected left boundary is wrong. | Cannot enter grid-control candidate extraction. |
| 19951024 | pending | No owner decision received in this review turn. | Hold. |
| 19970228 | pending | No owner decision received in this review turn. | Hold. |
| 19980407 | fail closed | The frozen rule produced no candidate. | Hold; no fallback was applied. |

## Diagnosis

The fixed outer-solid-rectangle heuristic is inadequate as a universal frame locator. It can choose an internal horizontal line (`20010913`), internal solid/summary-page structures (`20030514`, `20071106`), or an internal left edge (`20120417`). A candidate satisfying the fixed aspect range therefore does not prove it is the enclosing road frame.

## Claim boundary and next action

This review rejects four candidate ranges; it does not authorize changing thresholds inside the completed inventory. Any replacement must be a separately preregistered frame-range method that uses only stable paper/measurement evidence and is externally reviewed before execution. No rejected date may supply grid controls, a transform, registration metrics, or a v2 final-gate result.
