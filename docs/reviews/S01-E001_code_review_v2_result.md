# S01-E001 code review v2 result

- Verdict: `FAIL`
- Reviewed base commit: `dd738f177b5dbcced537a29497b4df3c38608a66`
- Reviewed bundle SHA-256:
  `919266709f9bb508ea4baa44557e5a2fac847d1bc22ee7895ae965c5112a1cd1`
- All 16 hashes and the workbook hash matched; all 20 tests passed.
- No training, model instantiation, confirmatory image access or reviewer edit
  occurred.

## Closed from v1

- Equal-score metric ordering became deterministic.
- All frozen location partitions became pairwise checked.
- Exactly two annotation-free road-background crops became fail-closed.

## Remaining blockers

1. A complete forged authorization could still reach test preparation.
2. Proposer receipt was not chained through the downstream artifacts.
3. Crop manifests bound paths but not crop bytes.
4. Distress overlap was checked before, rather than after, padding.
5. Test manifest membership was not rechecked against the data lock.
6. Initial-weight hashes and runtime remained placeholders rather than ex-ante
   frozen values.

## Decision

Training remained unauthorised. Protocol v3 addresses the remaining blockers
without changing the scientific question, primary metric, threshold or stop
rule.

