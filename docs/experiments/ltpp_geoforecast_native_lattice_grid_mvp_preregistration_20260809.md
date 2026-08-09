# LTPP native-resolution lattice-grid MVP preregistration — 2026-08-09

## Status

`EXPLORATORY_NATIVE_LATTICE_GRID_MVP__NOT_QUALIFIED`

## Mechanism question

Does the preceding detector fail outside 1995 because it uses a 1524×500 resampled image and assumes image-axis-aligned, fixed pixel dash patterns, rather than because printed grid evidence is absent?

## Scope and exclusions

- The only inputs are original `segment_0_50_white.png` pages; no crack vectors, WIM boxes, repair marks, handwritten labels, v1/v2 controls, cross-date correspondences, or residuals are read.
- Output is per-date high-resolution lattice evidence and review imagery only. No registration transform is fitted.
- This is not v2 control collection, model selection, final gate preparation, or an independent-validation result.

## Frozen algorithm

1. Estimate a date's dominant near-horizontal long-stroke angle and rotate its original page by that angle.
2. Use a fixed interior crop: x `[0.04, 0.88]`, y `[0.05, 0.95]` of the deskewed source.
3. Compute one dark-ink density projection per axis, with 7-pixel moving-average smoothing.
4. Evaluate integer periods 40–120 native pixels by the best phase's lower-quartile projection support; choose the smallest period within 98% of the best score. The lower quartile prevents a single unusually dark non-grid stroke from determining a period.
5. Choose the phase having maximum lower-quartile projection support; refine each phase+period position in a ±30%-of-period window.
6. Render the Cartesian intersections of both periodic line families. Do not use a local crack shape to add, delete, or move a line.

## Success and failure interpretation

- Success: visual overlays show cyan line families following printed grid structure, and green points at printed-grid crossings across the dates.
- Failure: incorrect overlays, weak/non-periodic line families, or missing grid coverage. The consequence is a failed engineering diagnostic—not altered final thresholds or a 2-D qualification claim.

## Minimal assets

One per-date summary CSV, full JSON evidence, individual overlays, a contact sheet, `decision.md`, and `manifest.sha256`.
