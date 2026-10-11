# S01-E002 independent read-only code review

Date: 2026-10-11

```text
verdict: PASS_WITH_NONBLOCKING_NOTES
bound_git_commit_or_bundle: b347bc3ff67dc16710a676e0f176e33c119f5911; bundle SHA-256 41284e181dca2d2f246cee6cb833052966c0eb6ebe65dc185626d9fcfa06bbd5
bound_file_hashes: 21/21 entries in code_review_bundle.json recomputed and matched
blocking_findings: none
nonblocking_findings: producer-only CUDA/model integration and the complete staged run remain unexecuted; the default system Python lacks torch, so all producer checks must use the frozen D-26-09 interpreter
test_commands_checked: /Users/wenxiaofang/miniconda3/bin/python3 -m unittest discover -s tests/pavetrack_cv -p 'test_*.py' (32/32); /Users/wenxiaofang/miniconda3/bin/python3 -m unittest discover -s tests/pavetrack_tiled_cv -p 'test_*.py' (12/12); python3 -m compileall -q scripts/pavetrack_tiled_cv; every tiled CLI --help; git diff --check
```

## Blocking-check disposition

1. `validate_data_lock` rejects duplicate or overlapping location partitions,
   the execution entry points call it, and preparation checks the observed
   development or confirmatory locations against the frozen lock.
2. The S01-E001 audit is a separate read-only script and its consumed locations
   do not enter the E002 development or confirmatory partitions.
3. Tile origins include the far image edge, target assignment implements the
   centre-or-25-percent rule with the four-pixel minimum, and reconstructed
   coordinates are clipped to the original image.
4. Cross-tile NMS has deterministic score, box and origin tie-breaking. Oracle
   coverage uses per-image maximum bipartite matching, so one proposal cannot
   cover multiple targets.
5. Training accepts only train and validation tile records and verifies the
   complete set and content hashes of prepared images and labels.
6. The baseline proposer and reranker must match the frozen S01-E001 hashes;
   both checkpoint structures are also validated before evaluation/freezing.
7. Validation evaluates the three declared score rules. Test evaluation reads
   only the selected rule from the hash-bound authorization.
8. `prepare_confirmatory.py` validates the authorization and all frozen artifact
   hashes before importing the workbook reader or resolving any image path.
9. The metric implementation uses one split-wide score threshold, a total
   false-positive budget of one per image, IoU 0.50, and macro averaging over
   target-bearing locations.
10. The code fails closed on protocol, partition, content, artifact, receipt,
    runtime, device and GPU identity mismatches. Producer preflight remains
    required because CUDA integration cannot be established on the Mac.
11. The protocol and runbook authorize only a later, separately frozen SAM2
    experiment after both localisation gates pass; they block segmentation,
    registration, growth, forecasting and mechanics claims here.

## Decision

The exact reviewed bundle is code-ready for one producer Run through the
development and validation freeze stages. Fresh confirmatory pixels remain
blocked until `freeze_for_test.py` issues the hash-bound authorization. This
review does not authorize duplicate runs, changed settings, a different GPU, or
any post-result tuning.
