# LTPP crack recognition B1 failure audit

Status: `READ_ONLY_DIAGNOSTIC__NEW_AMENDMENT_REQUIRED`  
Date: 2026-08-07  
Parent result: `ltpp_geoforecast_crack_recognition_b1_result_20260807.md`

## Purpose

This note diagnoses the frozen B1 result. It does not alter the frozen gold
labels, the six LOSO folds, the B1 scores, or the recognition gate. It is an
analysis-only asset for deciding whether a genuinely different recognizer is
warranted.

## Evidence already established

The B1 challenger had weighted centerline precision `0.2025`, weighted recall
`0.7639`, and mean map F1 `0.2689`. Section recall failed in four sections:
`06-2041`, `06-2647`, `06-8149`, and `06-8150`. The result document identifies
false-positive segmentation of printed form structure and section/style shift,
especially in `06-2041` and `06-8150`, as the dominant error mode.

The post-hoc threshold `0.70` diagnostic changed mean map F1 only from `0.2689`
to `0.2693`; therefore threshold selection alone is not a credible rescue.
Removing the B0 static-line mask reduced mean map F1 to `0.2139`; therefore
the static-line treatment is relevant, but the current single-output B1
representation remains insufficient.

## What this audit can and cannot claim

The existing B1 output and visual panels support a high-level diagnosis:

- recall is not the sole bottleneck;
- false positives from printed/form structures are a primary precision failure;
- section/style shift is material;
- threshold-only tuning is not a new method.

They do **not** provide independent counts for every semantic confounder. The
frozen adjudicated schema does not independently count grid, frame, arrow or
dimension, WIM/patch-box, or hatching/X marks. Those categories therefore need
an auxiliary hard-negative annotation package before a new supervised fit.

## Existing labels first

No duplicate crack annotation is required. The existing packet already
contains the complete human/secondary layer and the adjudicated layer. The
primary independent layer contains 199 `handwritten_code_or_calculation`
features and 67 `lane_or_reference_boundary` features across 31 maps. These
are usable for a first diagnostic overlap audit, but they are not adjudicated
gold and must not silently become training truth.

The first read-only proxy audit is stored at
`local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_failure_audit_20260807/existing_noncrack_overlap_proxy.json`.
Using a 7-pixel diagnostic buffer, B1 centerline predictions overlap the
existing boundary candidates for 25.13% of predicted pixels and handwriting
candidates for 5.56% of predicted pixels. These are proxy overlaps, not final
false-positive counts, because the primary layer is independent rather than
adjudicated.

Only if a later audit shows that the uncovered categories materially explain
the remaining error should we create supplemental, dated labels. The currently
uncovered categories are:

1. `grid_or_printed_frame`
2. `arrow_or_dimension`
3. `wim_or_patch_box`
4. `hatching_or_x_symbol`
5. `other_noncrack_line`

If supplemental labels are needed, create them in a new dated package without
modifying the frozen gold packet. For each source map, mark only visible
non-crack structures that could plausibly be predicted as crack.

The package must record annotator, source hash, coordinate frame, geometry
type, confidence, and whether the mark overlaps the B1 prediction. Held-out
maps must not be used to tune a new model; their hard-negative labels are for
the predeclared error audit unless a subsequent amendment explicitly changes
the training design.

## Decision

Do not run another B1 variant, threshold sweep, model zoo, or generic SAM
zero-shot evaluation under the existing amendment. A new challenger is
scientifically admissible only after the hard-negative package and a new dated
amendment are frozen and externally reviewed.
