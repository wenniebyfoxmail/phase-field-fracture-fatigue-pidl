# LTPP GeoForecast crack recognition B1 amendment

Status: `FROZEN_BEFORE_B1_FIT`  
Date: 2026-08-07  
Parent track: `ltpp_geoforecast_crack_recognition_track.md`

## Reason for amendment

B0 was a deterministic baseline and failed badly. The original v1
preregistration explicitly left B1/B2 unselected. This dated amendment
authorizes exactly one lightweight supervised segmentation candidate; it does
not alter B0, the frozen labels, or the section folds.

## Frozen data and split

- Same 37 image/GeoJSON pairs and SHA-256 input receipt as v1.
- Six complete-section LOSO folds: `06-1253`, `06-2041`, `06-2647`, `06-8149`,
  `06-8150`, `06-8201`.
- No target map, target geometry, future map, chronology, climate, traffic,
  maintenance, or B0 output enters training or threshold selection.
- Uncertain gold features are excluded from the training target and masked from
  confirmatory evaluation. Crack polygons remain positive occupancy targets;
  line cracks remain positive centerline targets.

## Frozen B1 algorithm

Architecture: three-level small U-Net, one grayscale input channel, base width
8, channel widths 8/16/32, two 3x3 convolutions per block, ReLU, max-pooling,
bilinear upsampling, skip concatenation, and one-channel logit output. No
pretrained weights.

Training representation: resize each 1524x500 map to 762x250 with bilinear
image interpolation. Rasterize the gold crack line/polygon target at the
original frame, dilate the target by 3 original pixels before nearest-neighbour
resize, and use the resulting binary occupancy target. Input is grayscale
divided by 255; no per-map normalization or source-specific removal rule.

Optimization: Adam, learning rate `1e-3`, weight decay `0`, batch size `2`,
80 epochs, deterministic seed `20260807`, CPU execution, weighted
BCE-with-logits (`pos_weight=8`) plus soft Dice loss with equal weights. All
training maps in a fold are used; no validation map is used for early stopping
or threshold selection.

Prediction: resize probability back to 1524x500, threshold at `0.35`, remove
no components, and skeletonize only for centerline metrics. The threshold,
architecture, seed, epochs, and target dilation are fixed before scores.

## Gate

Use the v1 recognition gate unchanged: pooled centerline F1 >= 0.80, pooled
mean matched centerline distance <= 0.10 m, pooled matched endpoint distance
<= 0.20 m, improvement over B0 in at least four of six sections, no section
recall < 0.70, all confounders reported, no post-freeze exclusions, and hashes
for input/split/code/environment/output.

## Execution boundary

This amendment authorizes only B1. B2/foundation-model assistance remains
unselected. If B1 fails, report `RECOGNITION_GATE_FAILED` with its frozen
error modes; do not alter this amendment or promote a tuned continuation.
