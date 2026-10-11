# Analysis: S01-E003

## Scientific question

Can a tile-native hard-negative ranker convert the fixed tiled candidate
coverage into at least +0.05 absolute macro-location recall at 1 FP/image?

## Evidence identity

- Experiment/protocol: S01-E003-v1, reviewed execution commit 05a380e.
- Run: S01-E003-R001; producer D-26-09 GPU 1; one 15-epoch training.
- Comparator: frozen E002 geometric-mean score on identical tiled boxes.
- Analysis: independently approved `scripts/pavetrack_ranker_cv/analyze.py`.
- Source: retrieved evaluation_validation.json, SHA-256
  `65634bceb2725024793eadcd15866091d5a6a54180011e6b567d7b1b9361ba9e`.
- Evidence role: development validation used for epoch selection.
- Available: exact paired scores/boxes/targets, full training history, manifests,
  checkpoint and authorization-stop decision.
- Missing: fresh confirmatory metrics, physical metrology, temporal identity,
  future state, mechanics and transfer evidence.

## Reading order and figure guide

1. F01_decision.png shows all five target-bearing validation locations and the
   macro result. The +0.05 line is the frozen development gate. The bootstrap
   interval is descriptive after checkpoint selection, not independent inference.
2. F02_error_montage.png shows deterministic recovered targets, remaining
   low-ranked covering boxes and selected metric FPs, including duplicates.
3. location_metrics.csv and summary.json provide authoritative recomputed values;
   montage_cases.json preserves the exact selection receipt.

F01 supports a +0.026752 development improvement, below the +0.05 gate. It does
not support a fresh-location claim. F02 supports concrete detection progress and
remaining localisation/ordering errors, without establishing a unique cause.
Red is GT, cyan an admitted detection, orange a covering proposal below budget.
Raw old/new scores have different calibrations; admission uses each model's own
split-wide ranked operating threshold.

## Deterministic displayed-case rule

Replay the exact metric's admitted-prefix one-to-one greedy matching. Select
the strongest newly recovered target from images with net TP gain, the highest
covering candidate below threshold for an unmatched target, and the highest
metric FP (including duplicates). Use two distinct locations per role, with
lexicographic image/box ties. These examples do not represent location averages;
all location averages appear in F01.

## Cross-figure interpretation and gate

Tiling coverage remains unchanged (oracle macro recall 0.683550). Ranker repair
converts more of it into operating recall: capture ratio 0.384401 -> 0.423537,
with 110 -> 115 TPs at 302 FPs. Benefits vary by location and are insufficient
for the frozen development margin. Many high-score FPs contain actual crack
pixels but fail IoU>=0.50; class presence and detection validity differ.

- Validity: passed runtime, partition, source and artifact-lineage checks.
- Execution: succeeded; retrieval: verified.
- Development gate: fails (+0.026752 < +0.05).
- Confirmatory primary verdict: not computed; no authorization or pixel access.
- Disposition: close this intervention at the development stop rule, retain
  checkpoint and partial detection progress, preserve fresh confirmation.

## Allowed and blocked conclusions

Allowed: this checkpoint improves the selected development-set operating point,
with measured gains and losses shown. Blocked: independent location-generalisation,
post-result gate relaxation, broad method failure, SAM2, physical growth,
mechanics, forecasting or deployment validity.

## Storyline impact and next action

S01 has a reusable tiled proposer and a modestly improved ranker. The next
solution should model localisation-valid detection quality on the same train
proposals, then qualify on validation before consuming fresh confirmation.
See ../result_20261012.md for the concrete smallest repair.
