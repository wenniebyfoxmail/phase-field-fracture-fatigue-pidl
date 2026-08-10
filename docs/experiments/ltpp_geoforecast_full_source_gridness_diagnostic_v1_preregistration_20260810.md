# LTPP full-source gridness diagnostic v1 — preregistration

## Status

`GRIDNESS_DIAGNOSTIC_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION`

This follows the failed full-source panel MVP v1.1.  It does not repair, reuse,
or rank its candidate rectangles.  It only shows where source pixels exhibit
co-occurring horizontal and vertical short-stroke density, so a subsequent
page-layout model can be specified before it tries to select a frame.

## Fixed method

On each frozen page-4 source raster, apply: Otsu ink threshold; an 11-pixel
horizontal closing and 11-pixel vertical closing; pixelwise intersection of
those two responses; then a 121×121 mean filter.  Overlay a fixed Turbo heatmap
for human viewing.  The 99.5th percentile is used only to display a colour
scale and is not a selection threshold.

No component, rectangle, map-band, crop, point, date correspondence,
transformation, crack, handwriting, WIM, repair, or other semantic object is
selected.  Output is exactly eight per-date overlays, one overview, metrics,
and a manifest.  It runs once after synthetic tests pass.
