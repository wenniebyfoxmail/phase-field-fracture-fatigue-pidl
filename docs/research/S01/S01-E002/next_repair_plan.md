# Proposed S01-E003: tile-native ranking repair

This is a design proposal, not authorization to train or access another
holdout.

## Problem to solve

S01-E002 increased candidate-set oracle macro recall to 0.613172 but achieved
only 0.183602 recall at one false positive per image. The next experiment should
improve ordering of the frozen tiled candidates, without reopening tile size,
stride, proposer training or the consumed confirmatory locations.

## Smallest intervention

1. Freeze the S01-E002 tiled proposer and its cross-tile NMS.
2. Mine positives and hard negatives from tiled proposals on development
   training locations only.
3. Fine-tune one copy of the existing reranker architecture on this tile-native
   proposal distribution. Do not sweep architectures.
4. Compare the new ranker against the frozen S01-E002 geometric-mean score on
   the existing development validation locations.
5. If the development gate passes, freeze model, score rule and manifests, then
   evaluate once on still-unused reserve locations.

## Draft result definition for review

- Primary estimand: change in location-macro recall at one global false
  positive per image and IoU at least 0.50, relative to the frozen S01-E002
  route on the same candidates.
- Proposed claim gate: at least +0.05 absolute recall. The threshold represents
  one additional recovered target per 20 at unchanged review burden.
- Report, without letting them vote: per-location deltas, oracle-to-budget
  capture ratio, proposal-level average precision, uncertainty interval and
  deterministic error cases.
- Interpretation ladder: `supports` at or above the gate; `mixed` for a positive
  but smaller improvement; `negative` for no improvement or harm; `inadmissible`
  only for validity failure.

## Evidence boundary

Locations 75, 220, 577, 956 and 1139 are consumed. They may support historical
diagnosis only and cannot select training examples, scores, thresholds or stop
rules. A new data lock and independent review are required before execution.
