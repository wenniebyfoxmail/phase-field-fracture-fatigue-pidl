# S03-E003 external Code Ready review — round 2

- Date: 2026-10-08
- Bound commit: `c07aa30`
- Bound protocol: v2
- Verdict: `REVISE_CODE`
- Reviewer surface: external ChatGPT web conversation

## Blocking findings

1. The bounded header reader could reject a valid large nodemap because it read
   a byte beyond its intended header window from the whole member.
2. The emitted protocol identity still reported v1.
3. Dictionary semantics and units were not actually qualified.
4. Missing local synchronization evidence could still pass.
5. “Episode” was stronger than the implemented grouping evidence.
6. Candidate horizons remained mutable and admitted a zero horizon.
7. The output firewall was not enforced through every path.
8. Manifest/parser error handling and fixed-reason coverage were incomplete.
9. The output root was not categorically excluded from the immutable raw tree.

## Disposition

No real archive audit had run. Rather than expanding header heuristics, the
protocol was narrowed to v3: exact identity plus central-directory manifest
only. Header semantics, synchronization, chronology, targets, horizons, and
episode claims were removed and now require a later reviewed audit only if the
manifest gate passes.
