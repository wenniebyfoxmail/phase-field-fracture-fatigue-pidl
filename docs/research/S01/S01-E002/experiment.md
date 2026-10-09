---
storyline_id: S01
experiment_id: S01-E002
protocol_revision: v1
status: code_review_pending
started_at: 2026-10-09
closed_at:
primary_storyline: S01
related_storylines: []
scientific_verdict:
---

# Native-scale tiled repair for PaveTrack crack localisation

## Problem and proposed solution

S01-E001 failed because its full-frame proposer covered only 46/184 targets at
IoU at least 0.50 even when every retained proposal was available. S01-E002
tests the direct repair: preserve native crack pixels with overlapping 640 x 640
tiles, reconstruct and deduplicate candidates in the original image, and reuse
the frozen hard-negative reranker to suppress tile-induced road-texture false
positives.

## Claim contract

- Claim tier: `C2 state-measurement`; current-image crack localisation only.
- Primary comparison: repaired tiled route versus the frozen S01-E001
  full-frame proposer, evaluated on exactly the same fresh images.
- Primary estimand: location-macro crack-box recall at one global false positive
  per image and IoU at least 0.50.
- Pass: repaired recall minus full-frame recall is at least 0.10 and the repaired
  candidate-set oracle macro recall exceeds the full-frame oracle by at least
  0.20.
- If either gate fails: close this localisation family as negative on PaveTrack
  PD and do not invoke SAM2.
- If both gates pass: run a separately frozen SAM2 box-to-mask experiment on a
  later unused reserve subset.
- Blocked regardless of outcome: physical crack growth, persistent crack
  identity, registration, future prediction, mechanism or cross-network
  transfer.

## Frozen information sets

- Training and validation locations are identical to S01-E001.
- S01-E001 confirmatory locations and the previously viewed pilot locations are
  excluded permanently.
- Fresh confirmation uses locations 75, 220, 577, 956 and 1139. They are the
  first five still-unused reserve entries in the pre-existing S01-E001 lock.
  Aggregate workbook annotation counts were inventoried before this freeze, but
  no image pixels were accessed. The result therefore applies to this fixed
  holdout rather than estimating the entire reserve population.
- Test images and labels cannot be acquired or prepared before the tiled model,
  score choice and validation report are hash-bound in a test authorization.

## Frozen repair

1. Generate 640 x 640 tiles at 480-pixel stride. Keep a target in a tile when
   its centre is inside the tile or at least 25% of its area intersects it;
   reject clipped sides below four pixels.
2. Retain every positive training tile and a seeded 1:1 sample of negative
   training tiles. Retain all validation and test tiles.
3. Fit one COCO-initialised YOLO11n for at most 50 epochs with patience 10,
   seed 20261008, 640-pixel input and batch 16.
4. Map tile proposals back to full-image coordinates. Apply deterministic
   cross-tile NMS at IoU 0.50 and retain at most 600 candidates per image.
5. Score the reconstructed candidates with the frozen S01-E001-R008 reranker.
   On validation only, select among raw proposer confidence, the frozen
   geometric-mean fusion and reranker probability. Ties choose the simpler raw
   proposer confidence.
6. Freeze the tiled checkpoint, selected score rule, full-frame baseline
   checkpoint, reranker checkpoint, manifests and validation report before any
   fresh-confirmatory acquisition.

## Stop rule

One seed, one tiled proposer and the already frozen reranker. No tile-size,
stride, NMS, score-grid, architecture or confirmatory threshold search. The
consumed S01-E001 locations may be used only for the fixed failure audit in
`failure_audit.md`.

## Minimum evidence

Code review; development manifest and tile manifest; training receipt;
validation-only score choice; test authorization; confirmatory download
manifest with size, CRC and SHA-256; per-image candidate rows and targets;
full-frame baseline and repaired metrics; candidate-ceiling table; error
montage; analysis README; independent evidence review.

## Current gate

Author self-review found four blocking defects in commit `96f2ccb`; all four
were remediated before execution. The remediated self-review verdict is
`PASS_WITH_NONBLOCKING_NOTES`, with 32 inherited PaveTrack tests and 12
repair-specific tests passing. Because the author performed this review, it
does not satisfy the independent-review gate. Independent read-only review of
the new hash bundle remains required before producer execution or fresh
confirmatory access.
