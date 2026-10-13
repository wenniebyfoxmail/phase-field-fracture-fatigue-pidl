# S01-E006 independent code/protocol/analysis review

Separate read-only e003_independent_review, gpt-5.6-sol / Medium.
Final PASS at exact clean commit `5d973b38d83e0af4343455e0dbdc02326e629b0a`.
Source manifest SHA256 `8221ff3b5dc9ed53dcaa5036910644e3fbc27607c9e34d6cd6d93beaa7d59583`;
30/30 file hashes, 93/93 targeted importlib tests, compilation and static chains
verified. Reviewer performed no fitting, producer contact or fresh pixel access.

Initial exact commit8f76fc6671e211d82761c772fad4e3ce600c2589 was FAIL despite
89 tests passing: pending-state binding, preregistered FP decomposition and
train-score checkpoint replay were missing. All repaired before execution.

Final review verified pending exact fields/runID/model/evaluation/SHA bind;
review and authorization both bind pending SHA, and missing/tampered pending
rejects fresh access. Exact-prefix FP types reproduce all TP/FP/detection counts.
Independent padding.1 pooled576 scorer cache is distinct from padding4 corrector
context; CPU classifier batch512 replays frozen E003 probabilities/geometric
scores, top40 pairs and selector logit features. Training backend difference
from exact GPU validation baseline is disclosed; no model/validation leakage.

Four regression folds exclude their held locations from fitting/scaler/targets,
conditional on the previously all-train E003 encoder; no end-to-end OOF claim.
All 16 source train locations are disjoint from5 reused validation and5 sealed
confirmation locations. Per-fold matched/represented GT counts:
7989/811,8768/883,9734/922,9065/813. Spatial node96x7x7 ->3x3,864+8=872 verified.
Class-balanced location/pair prior, train-only normalization, one L-BFGS
selector fit, deterministic strict pair choice, conflict fallback, parent count/
ID/score preservation, micro target-retention and null-denominator behavior
are coherent. All-original fallback on14,635 validation parents/10,877 pairs
reproduces E003 exactly.

PASS permits one fresh S01-E006-R001 **development** Run: extraction,4 fixed
crossfit ridge heads,1 selector fit,validation,freeze. No sweeps/retries or fresh
confirmation under this PASS. The +.05 recall AND .95 old-target-retention
criterion must pass, followed by independent development-evidence review and
separate hash-bound authorize stage, before fresh access can start.
