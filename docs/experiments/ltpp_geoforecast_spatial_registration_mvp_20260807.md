# LTPP spatial-registration engineering MVP — 2026-08-07

## Purpose and classification

This is an `EXPLORATORY_REGISTRATION_IMPROVEMENT_MVP` and a `tooling-only`
experiment. It exists to exercise the complete image-registration delivery
path before independent Tier A/B controls are available. It cannot change the
v1 negative result, the v2 availability-only authorization, or the 2-D model
closure.

## Mechanism question

Can the frozen eight source maps be deterministically rendered into one shared
15.24 m x 5.00 m raster coordinate canvas, with provenance, visual inspection
assets, consistent direction, and non-overwrite protection?

## Frozen MVP method

For each date, use only the four pre-existing printed-map frame corners
`(x0,y0)`, `(x1,y0)`, `(x1,y1)`, `(x0,y1)` in the frozen
`grid_gate_results.json`. A single page-frame homography maps these corners to
the 1524 x 500 px output rectangle, at 0.01 m/px and image y increasing down.
No crack, WIM, repair, handwritten mark, distress mask, candidate detection,
or cross-date image feature may enter the transform.

The page-frame corners are **construction controls**. Their reprojection error
only proves that the program applied its specified transform; it is not a
registration error measurement.

## Success and claim boundary

Engineering completion requires all eight maps to produce a 1524 x 500 px
image, a positive local orientation, an exact frame-construction reprojection,
per-date structural QC, source-frame visualizations, registered-grid
visualizations, temporal contact sheet, SHA-256 manifest, and a no-overwrite
receipt.

The only permitted result status is
`EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED`. It must never be
renamed to a registration pass, and it cannot use median/p95/maximum claims.

## Cheapest diagnostic and asset

Synthetic homography tests run before the real frozen input. The minimal output
is `mvp_result.json`, `per_date_structural_qc.csv`, a contact sheet, and
`decision.md` in a new local archive.

## Registry handoff

Record this MVP in the spatial-registration track only. Do not change
`docs/research_frontier.md`: the active 2-D route remains closed.

## Execution result

The code-receipted delivery run completed on 2026-08-07 at
`local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_mvp_20260807_code_receipt/`.
It produced all eight registered maps, a contact sheet, a temporal mean image,
per-date structural QC, and a complete SHA-256 manifest. Its recorded result
is `EXPLORATORY_REGISTRATION_MVP_COMPLETED__NOT_QUALIFIED`; no physical-error
metric is reported or implied.
