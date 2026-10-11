---
storyline_id: S01
experiment_id: S01-E003
protocol_revision: v1
status: draft
primary_storyline: S01
scientific_verdict: pending
---

# Tile-native hard-negative ranking repair

## Question and claim

Can one tile-native hard-negative ranker convert the already qualified tiled
candidate coverage into at least +0.05 absolute location-macro crack-box recall
at 1 global false positive per image, compared with the frozen S01-E002 score?
Claim: C2 current-image state measurement, real-road, fixed held-out locations.
The comparator and candidate have identical proposer, boxes, NMS and images.
No registration, physical growth, forecasting, mechanics or field deployment
claim is tested.

## Frozen intervention

Reuse S01-E002-R002 best tiled proposer, original 640-pixel tiles/480 stride,
IoU 0.50 cross-tile NMS and cap 600. Freeze the S01-E001-R008 MobileNetV3-small
ranker as comparator and initialization. Generate tiled proposals for training
images only; reuse the hash-bound E002 validation candidate rows without
regenerating candidates. For training retain up to 10 IoU>=0.50 proposal crops
per image, all GT crops, and up to 20 hard negatives ranked by the OLD
geometric-mean score. Negatives require IoU<=0.05 and their padded crops must
not intersect any crack annotation. Ignore ambiguous proposals. Pad every crop
10%, resize to 224, normalize ImageNet; no random crop can erase thin cracks.

Fine-tune all existing ranker parameters for 15 epochs, AdamW lr 1e-5,
weight decay 1e-4, batch 64, inverse-class-frequency weighted sampling with
replacement, seed 20261011. No architecture, seed, fusion or proposer sweep.
At every epoch score all frozen validation proposals. Select highest validation
macro recall at 1 FP/image, then lowest unbalanced loss on clear labeled validation
proposal crops (negative padded crop must not intersect a crack), then earliest epoch. Fixed candidate score is sqrt(proposer
confidence * new crack probability); comparator uses the old probability.

## Information sets and identity

Train and validation locations remain the E002 partitions. All pilot/E001/E002
confirmatory locations are permanently excluded from fitting and selection.
New confirmation is the next five unused reserves: 1174, 1729, 2246, 2260, 2485.
No pixel or target-count selection. Inference is limited to this fixed holdout;
location reid is the independent unit, and images within location are repeated.
The workbook hash and complete partitions are in data_lock.json. No new test
images may be downloaded/read before model, validation and score freeze.

## One primary criterion and result map

Delta = new minus frozen-old location-macro recall at 1 FP/image, one global
ranked operating point, IoU>=0.50. Zero-target locations contribute FP budget
but are excluded from recall mean. The same candidate set makes oracle coverage
identical, so oracle coverage is a diagnostic, not a second pass criterion.
Threshold +0.05 is a practical target: +5 percentage points in mean location
recall at fixed false-positive burden. It is not a claim about pooled target
counts or statistical significance.

Validity pass and delta>=+0.05: supports the bounded ranking-repair claim.
0<delta<+0.05: negative for the declared margin, with partial improvement recorded.
Delta<=0: negative, no useful ranking improvement. Validity fail: inadmissible.
No target-bearing location or unavailable metric: inconclusive.
A mixed label is not used to rescue a failed single claim.

Report paired location deltas, exact TP/FP, oracle-to-budget capture, deterministic
error examples, and a descriptive 10,000-resample location bootstrap interval
(seed 20261011). This small fixed holdout does not establish population validity.

## Development gate and stop rule

Require validation delta>=+0.05 before issuing test authorization. Otherwise
close as a development negative without consuming fresh confirmation. Stop after
one model and one authorized confirmation; no retry of scientific training,
post-test score selection, new threshold, extra arm or SAM2. A failed launch
before training may receive a new Run ID after read-only process/output audit.
Non-finite model/loss stops the run rather than silently continuing.

## Minimum evidence and validity

Independent exact-commit code/protocol review; frozen model/source hashes;
train crop manifests with source/image/split/content identity; full training
history; epoch selection and validation rows; recomputed metrics; authorization
before download; archive size/CRC/hash manifest; fresh-test image manifest;
paired old/new scores on identical boxes; primary visualization exposing location
variation; deterministic error montage; README_analysis; independent evidence
review and S01 claim-impact entry. Runtime/GPU/model mismatch, split overlap,
missing images, changed candidates or broken authorization invalidate evidence.

## Execution authority

User authorized review then execution. Producer gpu-server/D-26-09 GPU 1 only,
after fresh read-only PID/GPU checks. Exact CLI stages and immutable source are
bound to the independent review. Raw assets under local_archive/experiments/
S01-E003 or C:\Users\xw436\pavetrack_runs\S01-E003-R001.
