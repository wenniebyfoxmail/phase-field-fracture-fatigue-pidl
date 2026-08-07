# LTPP GeoForecast crack recognition v1 preregistration

Status: `FROZEN_AND_B0_EVALUATED`  
Track: `ltpp_geoforecast_crack_recognition_track.md`  
Date: 2026-08-06

## Question and scope

Evaluate recognition of the current scanned distress map only. The target is
adjudicated crack centerline geometry plus crack family. Uncertain geometries
are retained in the packet but excluded from confirmatory crack metrics.
Non-crack distress remains negative/error-audit material. No future survey,
chronology, traffic, climate, FWD, maintenance, spatial forecast, or failed
registration output may tune recognition.

## Frozen rows and split

- 37 source images and their 37 adjudicated GeoJSON states.
- Six complete-section LOSO folds: hold out one of `06-1253`, `06-2041`,
  `06-2647`, `06-8149`, `06-8150`, `06-8201`.
- Random crop-level train/test splits are forbidden. Every crop from a held-out
  map remains held out.
- The Stage 1 input receipt is
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_preflight_v1_20260806/input_receipt.json`.

## Target and rasterization

- `LineString` crack families: transverse, longitudinal, other crack.
- `Polygon` crack families: fatigue/alligator, block, other crack.
- `uncertain` is masked from confirmatory metrics, never silently relabelled.
- Other non-crack distress and water bleeding/pumping are negative audit
  categories, not crack positives.
- Physical frame is `[0,15.24] x [0,5] m`; image is `1524x500`; conversion is
  100 px/m with lower-left physical origin and explicit vertical image-row
  inversion at render time.
- Gold line centreline raster width is 1 px for centreline metrics. A separate
  10 px buffered tolerance (0.10 m) is frozen for matching and buffered-mask
  metrics. Gold polygons use pixel-center occupancy with no morphological
  dilation beyond the declared pixelization.

## Confounder treatment

The source visibly includes printed grid, frame/road boundaries, handwriting,
arrows/dimensions, WIM/patch boxes, hatching/X marks, and other distress.
Handwriting and lane/reference-boundary counts are 199 and 67 in the locked
primary inventory. The other categories are present but not independently
counted in the frozen schema; they must be reported as `present,
not-independently-enumerated` and inspected in the per-map audit. No category
may be dropped after the split is frozen.

## Candidate B0 freeze

B0 is a deterministic document/image-processing baseline using only the
current grayscale map and frozen morphology/line-rejection rules:

1. Otsu threshold to binary ink.
2. Remove connected long vertical/horizontal lines, regular periodic vertical
   grid, two traced broad horizontal boundary bands, image-edge ink, and Hough
   lines with the fixed parameters in the versioned implementation.
3. Close residual ink with a `9x9` square kernel.
4. Skeletonize each residual connected component.
5. Retain a predicted crack component only when skeleton length is at least 45
   px, bounding-box height is at least 50 px, elongation is at least 3.0,
   fill ratio is at most 0.35, vertical/transverse orientation is at least
   1.5 times width, and it does not touch a 4 px image boundary.
6. B0 family output is rule-based: vertical-dominant line components are
   `transverse_crack`, horizontal-dominant components are
   `longitudinal_crack`, and retained area-like components are
   `other_crack`; it may abstain rather than fabricate fatigue/alligator or
   block family labels. Any abstention is counted as a false negative for the
   crack recognition gate.

The B0 implementation, dependency versions, source hash, and exact output
receipt must be recorded before evaluation. B1/B2 are not selected or tuned in
this preregistration; they require a dated amendment if B0 qualification and
sample-size/compute checks justify them.

## Metrics and success rule

Primary: pooled and per-section centreline precision, recall, and F1 at the
frozen 0.10 m physical-distance tolerance.

Secondary: crack-length MAE and signed bias in metres; family-aware precision,
recall, F1; matched endpoint distance; component and branch-count error;
buffered-mask precision/recall/F1/IoU and clDice; false positives by every
confounder category; false negatives by crack family and visible stroke
quality; inference time and parameter count.

Recognition-qualified requires all of:

1. pooled centreline F1 >= 0.80;
2. pooled mean matched centreline distance <= 0.10 m;
3. pooled mean matched endpoint distance <= 0.20 m;
4. improvement over B0 in at least four of six held-out sections;
5. no held-out-section centreline recall < 0.70;
6. every confounder category reported, with no silent removal;
7. no post-freeze map, geometry, or family removal; and
8. SHA-256 receipts for inputs, split, code, environment, and outputs.

If any condition fails, report `RECOGNITION_GATE_FAILED` and dominant error
modes. Thresholds, tolerance, split, target treatment, and architecture may
not be changed after held-out evaluation; a revised route needs a new dated
amendment.

## Human audit and deliverables

For every held-out map, render original, adjudicated gold, prediction, and a
TP/FP/FN error overlay. Keep the original visible. Inspect representative
successes and every large-error case, recording model, source-semantic,
annotation-width, or coordinate/rasterization cause without changing scores.

The final handoff must be exactly one of `BLOCKED_BEFORE_FIT`,
`RECOGNITION_GATE_FAILED`, or `RECOGNITION_QUALIFIED_ON_FROZEN_CARRIER`.
