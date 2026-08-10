# LTPP 1991 solid outer-boundary review — 2026-08-10

## Status

`EXPLORATORY_SOLID_OUTER_BOUNDARY_REVIEW__NOT_QUALIFIED`

## Motivation

The previous Hough-frame candidate may use an inner vertical stroke and truncate valid road-map content. This review identifies the enclosing solid rectangle before any clipping or control generation.

## Frozen rule

1. Deskew only from dominant long near-horizontal strokes.
2. At every image row/column, measure the longest continuous dark-ink run in a fixed five-pixel band.
3. Find the outer aspect-compatible rectangle formed by sufficiently continuous vertical and horizontal solid strokes in the central map region. Accepted aspect is `[3.0, 3.6]`.
4. Show no controls and make no crop. Human review must confirm the rectangle contains all road-grid/crack content but excludes side summary tables.

## Boundary

This visual source-range diagnostic uses no crack geometry to choose an edge and does not register images, calculate residuals, collect v2 controls, or change any qualification state.
