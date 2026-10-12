# Analysis: S01-E004

## Scientific question and evidence identity

Does a fixed valid-detection quality head improve macro crack-box recall at
1 FP/image over E003 on identical tiled candidates?

- Run S01-E004-R001, protocol v1, reviewed source 928c519, D-26-09 GPU 1.
- Comparator: E003 epoch 2 geometric-mean score; identical boxes/targets/images.
- Analysis: scripts/pavetrack_quality_cv/analyze.py, independently reviewed with
  source manifest before execution.
- Exact source: retrieved evaluation_validation.json, SHA
  c81771b6fa8a9c5f31f145490941a3d8d44211a8960e7d24cb8953d723d26c54.
- Available: paired scores, boxes/targets/locations, all train features/validity
  labels, means/stds, coefficients, loss/gradient/history and stop decision.
- Missing: fresh confirmation, physical crack metrology, temporal identity,
  mechanics, future prediction and transfer evidence.

## Reading order and figure guide

1. F01_decision.png: all five development locations, paired recall and macro
   delta -0.039789 relative to the frozen +0.05 gate. The descriptive paired
   location interval does not establish independent confirmation.
2. F02_error_montage.png: recovered targets, target-covering boxes below budget
   and high-scoring metric FPs. Red GT, cyan admitted, orange below budget.
3. location_metrics.csv/summary.json: exact metric table and declared verdict;
   montage_cases.json: deterministic case-selection receipt.

Cases replay exact atomic score groups and one-to-one greedy matching. Select
strongest newly recovered targets from images with net TP gain, highest
covering boxes below budget for unmatched targets, and highest metric FPs
(including duplicates); two distinct locations per role, lexicographic ties.
Displayed recoveries are individual examples, not evidence of net benefit;
F01 shows the overall losses. Old/new raw scores use different scales and are
not directly comparable as calibrated probabilities.

## Cross-figure interpretation and gate

The head improved background exclusion but shifted budget toward partial-overlap
and duplicate boxes. Of 302 selected FPs, no/small-overlap counts fell 92 -> 41,
partial-overlap 190 -> 227, duplicates 20 -> 34; operating TPs fell 115 -> 106.
Oracle coverage remained0.683550 because coordinates were unchanged. Loss
convergence and improved background separation do not vote on the recall gate.

Validity/numerical execution passed; retrieval verified. The development gate
failed (-0.039789 < +0.05). The scientific new-location verdict is uncomputed;
no authorization/pixel access occurred. Reject this head as a replacement for
E003 and retain the better E003 checkpoint.

## Allowed/blocked conclusions and storyline impact

Allowed: this eight-feature head worsens the selected development operating
point. Blocked: all quality ranking is futile, lowering the used gate, broad
location generalisation, SAM2, growth, mechanics or deployment validity.

Next action is direct bbox correction with observable context, training-only
associations and frozen E003 scores, as a separate reviewed Experiment.
