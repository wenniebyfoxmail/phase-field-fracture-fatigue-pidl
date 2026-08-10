# LTPP full-source gridness diagnostic v1 — result

## Decision

`GRIDNESS_DIAGNOSTIC_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION`

The one-shot diagnostic completed all eight fixed page-4 source rasters.  Its
heatmap makes the paired manual-map grids visibly prominent in seven pages, but
it also responds to handwriting and form/table grids.  It did not select any
rectangle, crop, control point, or registration model.

The central finding is source-layout, not registration: 1991 page 4 is a
`SHEET 1` survey-summary form rather than a distress-map page.  Thus a fixed
page-4 input is invalid as a common map-page assumption.

## Evidence

The completed package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_full_source_gridness_diagnostic_v1_20260810/`

It has eight per-date heatmaps, an overview, `gridness_result.json`, and a
verified `manifest.sha256`.  No assertion is made that a heat hotspot identifies
a valid map boundary; it only identifies local co-occurrence of orthogonal
short ink strokes.

## Consequence

The next source-layout task must discover the relevant map pages per date
before attempting to find a panel.  It must not use a heatmap peak as a map-page
selection rule without a separately frozen structural criterion.
