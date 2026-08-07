# LTPP 06-1253 dashed-grid intersection diagnostic — 2026-08-07

## Status

`EXPLORATORY_DASHED_GRID_INTERSECTION_DIAGNOSTIC__NOT_QUALIFIED`

## Question

Can the 1995 engineering MVP avoid treating a continuous crack or road-boundary stroke as a printed-grid control by accepting only intersections between repeated dashed horizontal and vertical grid lines?

## Frozen input and rule

- Input is only the existing 1995 page-frame MVP image. No crack vectors, WIM boxes, repair marks, handwritten labels, cross-date image, or v1/v2 control is an input.
- Ink is `gray < 128`; sampling excludes a fixed 20-pixel page margin and uses a fixed 5-pixel-wide line band.
- A candidate grid line is accepted only when all of these fixed conditions hold: ink fraction in `[0.08, 0.45]`, at least 10 dash runs, no ink run longer than 18 pixels, and median inter-dash gap in `[4, 16]` pixels.
- A candidate control is only an accepted-horizontal × accepted-vertical intersection. A rejected line is never extrapolated, repaired, snapped, or replaced.

## Intended output

A line-evidence CSV and review image: cyan lines are accepted dashed grid evidence, red lines have been rejected because of continuous ink, and green circles are the only intersection candidates. This is a source-confounder diagnostic, not a registration transform or a v2 control extraction method.

## Claim boundary

The result cannot change `SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`, the v2 availability-only approval, final-control custody, or 2-D model eligibility.
