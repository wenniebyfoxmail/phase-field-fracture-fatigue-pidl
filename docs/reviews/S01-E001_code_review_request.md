# S01-E001 independent code review request

## Requested decision

Return exactly one verdict: `PASS`, `PASS_WITH_NONBLOCKING_NOTES`, or `FAIL`.
No training is authorised unless the verdict is `PASS` or
`PASS_WITH_NONBLOCKING_NOTES` and all blocking findings are absent.

This is a read-only review. Do not edit code, run training, inspect
confirmatory test images, or change the scientific gate.

## Scientific contract

- Experiment: `docs/research/S01/S01-E001/experiment.md`
- Protocol revision: `v7`
- Data identity and split: `docs/research/S01/S01-E001/data_lock.json`
- Primary estimand: macro-location crack-box recall at one false positive per
  image and IoU at least 0.50.
- Primary comparison: frozen two-stage score minus raw proposer score on the
  identical proposal set.
- Pass threshold: absolute delta at least `+0.10` on the confirmatory locations.
- Independence unit: PaveTrack `reid` location.

## Files to review

- `scripts/pavetrack_cv/common.py`
- `scripts/pavetrack_cv/prepare_dataset.py`
- `scripts/pavetrack_cv/train_proposer.py`
- `scripts/pavetrack_cv/mine_crops.py`
- `scripts/pavetrack_cv/train_reranker.py`
- `scripts/pavetrack_cv/evaluate_two_stage.py`
- `scripts/pavetrack_cv/freeze_for_test.py`
- `tests/pavetrack_cv/test_common.py`
- `tests/pavetrack_cv/test_crop_lineage.py`
- `tests/pavetrack_cv/test_data_lock.py`
- `tests/pavetrack_cv/test_test_firewall.py`
- Immutable v7 hash inventory:
  `docs/research/S01/S01-E001/code_review_bundle.json`
- Failed v1-v6 inventories and decisions are retained separately for provenance.

Bind the review to the SHA-256 of each listed file, the workbook SHA-256 in the
data lock, and the exact Git commit or immutable dirty-tree bundle supplied with
the request. A branch name alone is not sufficient.

## Blocking checks

1. Train, validation, confirmatory test, excluded viewed test, and reserve
   location sets are disjoint where required.
2. Dataset preparation filters the workbook before resolving image paths.
3. Development preparation cannot silently read confirmatory test pixels; test
   preparation requires a post-fit authorization bound to the data lock.
4. Hard-negative mining and reranker fitting cannot consume a manifest that
   contains confirmatory test.
5. Validation alone selects the reranker checkpoint; the fused scoring rule and
   model hashes are fixed in `freeze_for_test.py` before test access.
6. Raw and two-stage arms contain exactly the same boxes and differ only in
   score.
7. Full-image coordinates are preserved through cropping and evaluation.
8. Greedy matching prevents one target from being counted twice.
9. `R@1FP/image` uses one global threshold and a realizable ranked prefix:
   detections below a threshold cannot be recovered after the false-positive
   budget is exceeded.
10. Macro averaging includes only locations with crack targets; target-free
    locations still report false-positive burden.
11. Any missing selected image, workbook mismatch, split overlap, or premature
    test access fails closed.
12. No diagnostic can change the frozen primary verdict.
13. Equal-score proposals have an input-order-independent deterministic order.
14. Pothole/patch negatives do not overlap any annotated crack box, and every
    image contributes exactly two annotation-free road-background crops or the
    miner fails.
15. Proposer fitting, crop mining, reranker fitting, validation evaluation and
    confirmatory authorization form one verifiable data/model hash chain.
16. A hand-built ZIP or synthetic JSON chain cannot authorize confirmatory
    access: both checkpoints must load with the expected YOLO and
    MobileNetV3-small schemas, class mappings and reranker lineage.
17. Every prepared image and YOLO label is content-hashed and revalidated
    before fitting, mining or evaluation; same-path replacement fails closed.
18. Hostname, Python executable and version, package versions, CUDA runtime and
    GPU identity match the frozen producer runtime before claim-bearing work.
19. The proposer semantically loads as the exact frozen YOLO11n architecture,
    not merely an arbitrary one-class Ultralytics detector.
20. CUDA logical-device remapping cannot make the verified physical GPU differ
    from the GPU used by Torch; identity is resolved by the Torch-visible UUID.
21. YOLO identity is checked against the instantiated module graph,
    connectivity and tensor shapes, not checkpoint-supplied YAML alone.
22. Shape-preserving behavioral changes (including stride, padding, dilation,
    groups, operator settings, hooks or an instance forward override) change
    the instantiated-graph identity and fail closed.

## Requested review output

```text
verdict:
bound_git_commit_or_bundle:
bound_file_hashes:
blocking_findings:
nonblocking_findings:
test_commands_checked:
reasoning:
```
