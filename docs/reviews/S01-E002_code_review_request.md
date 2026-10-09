# S01-E002 independent code review request

## Requested decision

Return exactly one verdict: `PASS`, `PASS_WITH_NONBLOCKING_NOTES`, or `FAIL`.
This is a read-only review. Do not fit a model or inspect images from locations
75, 220, 577, 956 or 1139.

## Scientific contract

- Experiment: `docs/research/S01/S01-E002/experiment.md`
- Failure audit: `docs/research/S01/S01-E002/failure_audit.md`
- Primary comparison: repaired tiled route minus the frozen S01-E001 full-frame
  proposer on exactly the same fresh images.
- Primary gate: macro-location `R@1FP/image` delta at least +0.10.
- Necessary mechanism gate: oracle candidate macro-recall delta at least +0.20.
- Confirmatory unit: PaveTrack `reid` location.

## Blocking checks

1. Train, validation, consumed/excluded, fresh confirmatory and remaining
   reserve locations are disjoint.
2. The fixed failure audit cannot change S01-E001 and cannot select E002
   settings.
3. Tile origins cover the full image, target assignment follows the frozen
   centre-or-25%-intersection rule, and tile boxes map back to full-image
   coordinates correctly.
4. Cross-tile NMS is deterministic, global per image and cannot reuse one
   proposal to cover multiple targets in the oracle diagnostic.
5. Training receives only train/validation tiles and every image/label is bound
   by content hash.
6. The full-frame comparator and reranker are the exact S01-E001-R008 artifacts
   named in `run_config.json`.
7. Score selection uses validation only. Test evaluation computes only the
   frozen selected score.
8. Confirmatory preparation is impossible before model, validation result,
   score rule, config, data lock and artifact hashes are frozen.
9. The metric uses one global threshold, a one-false-positive-per-image budget,
   IoU at least 0.50 and location-macro averaging over target-bearing locations.
10. Any missing file, split mismatch, content replacement, artifact drift,
    runtime drift or GPU-identity drift fails closed.
11. Passing localisation authorizes only a separate SAM2 experiment; it does
    not establish segmentation, registration, growth or prediction.

## Requested output

```text
verdict:
bound_git_commit_or_bundle:
bound_file_hashes:
blocking_findings:
nonblocking_findings:
test_commands_checked:
reasoning:
```

