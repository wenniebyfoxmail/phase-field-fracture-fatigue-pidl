# LTPP full-source map-panel MVP v1 — preregistration

## Status

`EXPLORATORY_FULL_SOURCE_PANEL_MVP__NOT_REGISTRATION`

This is a one-shot engineering visualization diagnostic.  It does not amend
the closed v1 spatial-registration audit, supply independent controls, estimate
a cross-date transform, calculate registration error, or authorize a 2-D crack
model.

## Objective

On page 4 of each of the eight newly frozen official full-source PDFs, locate a
pair of 50-ft printed map-panel *candidates* using only their long rectangular
outer frames.  The output is a human-review overlay; it is not an image crop
approved for registration.

## Inputs and fixed rule

Input is the eight uncropped, 160-dpi page-4 display rasters from:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_full_source_availability_receipt_20260810_after_render_name_repair/`

For each image, the method applies Canny edge detection and a probabilistic
Hough transform.  It retains only near-vertical and near-horizontal line
segments of at least 170 pixels, clusters lines within 10 pixels, constructs
rectangles only when their width is 13–47% of page width, height is 35–85% of
page height, and height/width is 1.9–4.6.  It chooses the highest-scoring
non-overlapping left-to-right pair only when widths agree within 20%, heights
within 10%, and both top and bottom sides agree within 42 pixels.

The first output pair is green (`P1`); the second is magenta (`P2`).  If no
unique pair satisfies every rule, the date is `NO_PANEL_PAIR`.  There is no
manual completion, date deletion, source substitution, parameter adjustment,
or re-run of this MVP.

## Prohibited information and interpretation

The algorithm uses only long straight line geometry.  It does not identify or
use cracks, distress symbols, WIM/repair boxes, handwriting, text, survey
summary values, or another date.  It produces no affine/projective transform,
physical coordinates, or quantitative registration claim.  A correct-looking
rectangle is evidence only that a printable map-window candidate exists.

## Stop rule

Run once after synthetic tests pass.  Record all eight dates, including every
failure.  A failure stops this MVP; it cannot be repaired by tuning this run.
Even an 8/8 visual success does not change
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.
