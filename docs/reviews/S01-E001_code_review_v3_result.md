# S01-E001 independent code review v3

- Verdict: **FAIL**
- Bound protocol: `S01-E001-v3`
- Bound bundle SHA-256: `81b9ca67735bd922ef96f40c9fe0cf159ecb5b2e6a44f36a4a834c1ec652ace3`
- Bound repository base commit: `dd738f177b5dbcced537a29497b4df3c38608a66`
- Hash verification: all 16 bound files and the workbook matched.
- Static tests: 23 passed.
- Safety: no training and no confirmatory-image access were performed.

## Blocking findings

1. A hand-built ZIP containing only `data.pkl`, combined with synthetic JSON
   receipts, could still authorize confirmatory access. ZIP structure was not a
   semantic model check.
2. Prepared image and YOLO-label bytes were not hashed in the manifest, so a
   same-path replacement was not detected downstream.
3. The producer runtime was recorded but not enforced before claim-bearing
   execution.

## Closed findings retained from earlier reviews

Partition disjointness, confirmatory `reid` substitution, crop-byte
replacement, padded-distress overlap, deterministic tie handling, exact two
road-background crops, proposer receipt chaining, and initial-weight hashes
all passed this review.

Training remained blocked. These findings are addressed only in the subsequent
v4 candidate and require a new independent review.
