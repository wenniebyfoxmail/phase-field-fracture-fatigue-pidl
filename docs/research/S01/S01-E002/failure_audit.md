# S01-E001 failure audit and repair choice

Date: 2026-10-09

This is an explanatory audit of the already consumed S01-E001 confirmatory
locations. It cannot change that experiment's negative verdict and it cannot be
used for model selection.

## Frozen evidence

- Evaluation file: `evaluation__evaluation_test.json` from S01-E001-R008.
- Targets: 184 crack boxes in 341 images across locations 1059, 2227, 2291 and
  6227.
- Retained proposer candidates: 5,671.
- S01-E001 proposer macro-location `R@1FP/image`: 0.165093.
- S01-E001 two-stage macro-location `R@1FP/image`: 0.157018.

## Failure decomposition

Maximum bipartite matching was computed independently within each image, using
all retained candidates and IoU at least 0.50. This is an oracle candidate-set
ceiling, not an attainable model result.

| Location | Targets | Covered by any candidate | Oracle recall |
|---|---:|---:|---:|
| 1059 | 73 | 3 | 0.041096 |
| 2291 | 16 | 6 | 0.375000 |
| 6227 | 95 | 37 | 0.389474 |
| **Macro** | **184** | **46** | **0.268523** |

Only 46/184 targets had any candidate at IoU at least 0.50. The full candidate
set therefore left 138 targets unreachable by every scoring rule. At the frozen
operating points, 27 targets had a covering proposer candidate above threshold
and 25 had a covering fused-score candidate above threshold. Candidate coverage
is the dominant bottleneck; ranking loss is secondary.

The reranker is not devoid of signal: on the explanatory proposal labels
(`positive` at IoU at least 0.50, `negative` at IoU at most 0.05), its proposal
AUROC was 0.8443 and the frozen fused score AUROC was 0.8772. This does not
rescue S01-E001, but it supports reusing the frozen reranker to suppress the
large false-positive burden of a higher-recall proposer.

## Repair decision

S01-E002 implements one repair: train the proposer on overlapping native-scale
tiles, reconstruct candidates in full-image coordinates, merge cross-tile
duplicates, then apply the already frozen S01-E001 hard-negative reranker.

The choice is bounded by two prior observations: S01-E001 proves that the
full-frame candidate set has an inadequate coverage ceiling, while the earlier
post-pilot 640-pixel tiled diagnostic reached tile-level recall 0.745 but only
0.0033 precision. The repair therefore combines the coverage mechanism from
tiling with the false-positive suppression mechanism from the reranker. It does
not tune either component on the consumed locations.

