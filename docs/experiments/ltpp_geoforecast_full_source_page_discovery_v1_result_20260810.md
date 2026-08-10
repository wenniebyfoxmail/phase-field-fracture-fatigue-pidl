# LTPP full-source map-page discovery v1 — result

## Decision

`FULL_SOURCE_PAGE_DISCOVERY_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION`

All 79 pages from the eight frozen official PDFs rendered successfully and the
89-entry output manifest verified.  The completed package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_full_source_page_discovery_v1_20260810_after_import_repair/`

The initial similarly named output directory is empty: it stopped at direct
script import before rendering any PDF page.  The repaired run changes only
that import path and uses the new `..._after_import_repair` directory.

## What the visual inventory establishes

The per-date contact sheets show that map-page positions are not constant:

| Date | visually apparent five-page map block | Fixed page-4 assumption |
|---|---|---|
| 1991-06-10 | pages 6–10 | false: page 4 is a form |
| 1995-10-24 | pages 4–8 | plausible but not yet an input selection |
| 1997-02-28 | pages 4–8 | plausible but not yet an input selection |
| 1998-04-07 | pages 4–8 | plausible but not yet an input selection |
| 2001-09-13 | pages 4–8 | plausible but not yet an input selection |
| 2003-05-14 | pages 4–8 | plausible but not yet an input selection |
| 2007-11-06 | pages 4–8 | plausible but not yet an input selection |
| 2012-04-17 | pages 3–7 | false: page 4 is the second map page |

These are a source-layout inventory based on rendered originals, not selected
registration inputs and not independent physical controls.

## Important negative finding

The fixed grid-coverage rank cannot select map pages: large summary tables can
outscore actual map pages.  For example, page 11 ranks first for 1991 because
it is a dense tabular summary, while the visible maps are pages 6–10.  The
coverage metric is therefore retained only as a diagnostic column, not used to
choose pages.

## Next condition

Before any new frame detector is run, an explicit source-page candidate
inventory must be frozen (including why a particular page is the 0–100-ft map
pair for each date), then visually reviewed.  Only then can a distinct panel
model restrict its search to the correct page band.  None of this changes
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.
