# S01-E001 code review v1 result

- Verdict: `FAIL`
- Reviewed base commit: `dd738f177b5dbcced537a29497b4df3c38608a66`
- Reviewed bundle SHA-256:
  `a91e02f61480e6b432d9066fcf14962cd42d7462753272e4d04c9f2e517af259`
- Workbook SHA-256 matched the data lock.
- All 15 file hashes matched and the original 13 tests passed.
- No training, model instantiation, confirmatory image access or reviewer edit
  occurred.

## Blocking findings

1. Test authorization and model freeze did not form an end-to-end hash chain.
2. Crop mining and reranker inputs were not fully lineage-bound.
3. Pothole/patch crops overlapping crack boxes could receive contradictory
   background labels; seven metadata-level overlaps existed in training.
4. Equal-score detection ordering could change the primary recall.
5. Reserve and excluded partitions were not included in all overlap checks.
6. The frozen requirement for two road-background crops was not enforced.

## Decision

Training was not authorised. Protocol v2 repairs these issues without changing
the scientific question, primary metric, pass threshold or stop rule. The v2
bundle requires a fresh independent review.

