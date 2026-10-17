# LTPP non-destructive two-channel recognition freeze candidate

Status: `REVISED_FOR_EXTERNAL_NO_FIT_REVIEW__NO_FIT`  
Date: 2026-08-10  
Parent amendment: `ltpp_geoforecast_crack_recognition_document_aware_amendment_candidate_20260807.md`  
External review disposition addressed: `REVISE_BEFORE_NO_FIT`

## Scope and mechanism question

Can one fixed document-structure cue improve current-map crack recognition over
the failed B1 Tiny U-Net without deleting any raw crack evidence?

This candidate concerns scanned-map recognition only. It does not authorize or
support registration, physical crack width, future-map prediction, mechanistic
forecasting, or ordinary road-photo deployment.

If the eventual frozen challenger passes, only the current-map recognition
claim changes. If it fails, this two-channel branch closes and B1 remains the
terminal trained result for this carrier.

## Frozen data and split

- 37 grayscale maps at `1524 x 500` pixels;
- adjudicated manifest SHA-256
  `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad`;
- 249 adjudicated geometries, including 232 crack geometries;
- the same six complete-section LOSO folds as B1;
- one final-epoch model per held-out section;
- no validation-fold selection, early stopping, or held-out threshold choice.

No image, crack geometry, section, or zero-crack map may be removed after this
freeze.

## Input channel 1: raw grayscale

Read the original 8-bit grayscale image. Resize from `1524 x 500` to
`762 x 250` with OpenCV `INTER_AREA`, convert to `float32`, and divide by
`255.0`. No pixel is deleted, whitened, inpainted, masked, cropped, or replaced.

## Input channel 2: fixed static-document cue

For each original image independently:

1. apply OpenCV Otsu binary inversion to obtain ink;
2. call `static_line_mask(ink)` from
   `scripts/ltpp_extract_crack_candidates.py`;
3. resize the returned binary mask to `762 x 250` using `INTER_NEAREST`;
4. map background to `0.0` and mask support to `1.0`;
5. stack it after the raw-grayscale channel.

The frozen source SHA-256 is
`3f55a626a22680190249f51a7a64754afbcf769a0d836d284d551aa16f47aac8`.
Its internal morphology, boundary tracing, periodic-grid rule, Hough settings,
and dilation are used byte-for-byte unchanged for every map and fold.

This procedure never reads adjudicated or primary GeoJSON, section identity,
fold outcomes, model output, or human per-image corrections. Known mask/gold
overlap is allowed only as auxiliary input information. It must not cause raw
pixel deletion, target modification, loss masking, loss reweighting, ROI
exclusion, or post-fit mask adjustment.

## Target and ordinary background

Use the unchanged B1 target construction:

1. rasterize adjudicated crack `LineString` and crack `Polygon` geometry at
   `1524 x 500` through the frozen B0 gold rasterizer;
2. combine line and polygon masks;
3. dilate once with a `3 x 3` all-ones kernel;
4. resize to `762 x 250` using `INTER_NEAREST`;
5. map crack target to `1.0` and every other pixel to `0.0`.

“Ordinary background” means every pixel outside this frozen adjudicated
crack-positive target. Handwriting, grid, boundary, WIM, primary annotations,
or other nuisance categories cannot be used to reweight, mask, exclude,
subdivide, or relabel background.

## Sole learned output

Crack occupancy is the only learned output. There are no semantic-negative,
centerline, endpoint, junction, family, or topology heads.

At full resolution, the occupancy probability is obtained by bilinear resizing
of the `762 x 250` sigmoid probability to `1524 x 500`. The binary occupancy
uses the pre-frozen threshold `0.35`.

All other outputs are deterministic:

- centerline: `skimage.morphology.skeletonize(binary_occupancy)`;
- connected components: 8-connectivity on binary occupancy;
- qualifying component for the zero-crack sentinel: component skeleton length
  at least `45` full-resolution pixels;
- endpoint: skeleton pixel with exactly one 8-neighbour;
- junction: skeleton pixel with at least three 8-neighbours;
- topology quantities: component, endpoint, junction, and branch counts derived
  from that fixed skeleton graph.

No component is removed from the primary recognition output. The 45-pixel rule
is used only to report the secondary zero-crack sentinel and cannot alter the
prediction or primary gate.

## Exact architecture

Use the B1 `TinyUNet` byte-for-byte except for the first convolutional block,
which changes from `Block(1, 8)` to `Block(2, 8)`.

- encoder blocks: channels `2 -> 8 -> 16 -> 32`;
- each block: `3 x 3 Conv, ReLU, 3 x 3 Conv, ReLU`, padding 1;
- downsampling: `2 x 2` max pooling;
- decoder projections: `32 -> 16` and `16 -> 8` by `1 x 1` convolution;
- bilinear upsampling with `align_corners=false`;
- skip concatenation at the 16- and 8-channel levels;
- decoder blocks: `32 -> 16` and `16 -> 8`;
- output: one `1 x 1` convolution, `8 -> 1` logit;
- no batch normalization, dropout, pretrained encoder, or auxiliary head.

The B1 implementation being minimally amended has SHA-256
`435acc2e9c370aca47f5e88b9d65cf5373d319617c139d2ae765e9654bebd01c`.

## Exact training rule

- seed: `20260807`, reset identically for each LOSO fold;
- deterministic PyTorch algorithms enabled;
- CPU threads: 2 in the runner;
- optimizer: Adam, learning rate `1e-3`, weight decay `0.0`;
- epochs: 80 exactly;
- batch size: 2;
- training-map order: Python `random.shuffle` under the frozen seed each epoch;
- loss: `BCEWithLogitsLoss(pos_weight=8.0) + dice_loss`;
- Dice smoothing constant: 1 in numerator and denominator, exactly as B1;
- augmentation: none;
- checkpoint selection: final epoch only;
- reuse of B1 weights: prohibited;
- model variants, restarts, threshold sweeps, architecture swaps, and post-fit
  rule changes: prohibited.

The eventual training producer must be Taobo. Mac is limited to no-fit package
construction, import checks, and deterministic input/target validation. CSD3 is
not a fallback.

## Zero-crack specificity sentinel

The preregistered zero-crack maps are:

`P002`, `P006`, `P007`, `P031`, `P032`, `P035`, and `P036`.

For every such map, evaluate the complete valid `1524 x 500 = 762000` pixel
frame after the same `0.35` threshold.

Primary burden:

`FPA_i = predicted crack occupancy pixels / 762000`.

The frozen maximum is `315 / 762000 = 0.0004133858`. The numerator is
mechanically defined as one 45-pixel minimum crack component multiplied by the
maximum 7-pixel full-resolution support implied by the frozen B1 target
rasterization. The sentinel requires `max_i FPA_i <= 315 / 762000`.

Secondary burden:

`FPComp_i` is the number of 8-connected predicted occupancy components whose
skeleton length is at least 45 full-resolution pixels. The sentinel requires
`max_i FPComp_i = 0`.

The zero-crack sentinel passes only if both conditions pass on all seven maps.
The maximum, not the mean, is used. These limits cannot be changed after any
challenger probability or prediction is produced. `P002` is a known stress
test, not a new blind holdout.

## Existing recognition gate

The original gate remains unchanged:

- pooled centerline F1 at least `0.80`;
- pooled mean matched centerline distance at most `0.10 m`;
- pooled matched endpoint distance at most `0.20 m`;
- improvement over B0 in at least four of six sections;
- no section centerline recall below `0.70`;
- no post-freeze map, geometry, family, or confounder removal.

The zero-crack sentinel is an additional conjunctive requirement, not a
replacement or threshold-selection set.

## Definition of one challenger

One challenger is exactly the complete six-fold LOSO execution defined above:
the two frozen input channels, target construction, TinyUNet architecture,
loss, seed, optimizer, schedule, threshold, final-epoch checkpoint rule,
skeletonization, topology derivation, recognition gate, and zero-crack
sentinel. Any change creates a new challenger and requires a new dated review;
it cannot be executed under this amendment.

## PIDL Experiment Gate

- Mechanism question: does a non-destructive static-document cue improve
  recognition without sacrificing raw crack evidence?
- Claim changed if success: current-map recognition only.
- Claim changed if failure: close this auxiliary-cue branch.
- Cheaper diagnostic first: completed hard-removal preservation audit failed.
- Minimal output asset: one six-fold metrics receipt and one fixed visual panel
  containing `P020`, `P008`, `P002`, and `P009` if training is later authorized.
- Code/producer alignment: no-fit checks on Mac; any authorized fit on Taobo.
- Success criteria: unchanged recognition gate plus the zero-crack sentinel.
- Failure criteria: failure of any recognition or zero-crack requirement.
- Registry destination: `ltpp_geoforecast_crack_recognition_track.md`.
- Current decision: `EXTERNAL_NO_FIT_REVIEW_REQUIRED__NO_TRAINING`.

## Authorization boundary

This document is a freeze candidate, not a fit authorization. External approval
may authorize only implementation and deterministic no-fit validation. A later
explicit authorization is required before any training command.
