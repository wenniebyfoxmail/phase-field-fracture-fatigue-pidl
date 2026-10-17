---
storyline_id: S01
experiment_id: S01-E001
protocol_revision: v11
status: code_review_pending
started_at: 2026-10-08
closed_at:
primary_storyline: S01
related_storylines: []
scientific_verdict:
---

# PaveTrack two-stage crack localisation for reliable SAM2 prompts

## Scientific question

On PaveTrack locations not used for fitting or model selection, does an explicit
hard-negative crop reranker improve crack-box localisation over the same
one-stage proposal detector enough to justify downstream SAM2 evaluation?

## Claim contract

- Claim tier / optional tag: `C2 state-measurement`; `real-road`;
  `current-image crack localisation`.
- Estimand and comparison class: macro-location crack-box recall at one false
  positive per image (`R@1FP/image`, IoU at least 0.50), using one global score
  threshold across the split and then macro-averaging recall across locations
  with crack targets. Compare the frozen two-stage score with the underlying
  proposal score on exactly the same proposals.
- Claim if primary gate passes: explicit hard-negative reranking improves the
  usefulness of crack-box prompts on unseen PaveTrack locations; a separate
  downstream SAM2 experiment is justified.
- Claim if primary gate fails: this two-stage localisation route is negative;
  do not tune SAM2 or add another detector on the viewed holdout.
- Blocked conclusion regardless of outcome: physical crack growth, persistent
  crack identity, metric registration, future prediction, material state,
  fatigue mechanism, or transfer to a different road network.

## Reuse decision

- Searched: repository scripts; the 2026-10-08 local PaveTrack pilot package;
  Ultralytics and SAM2 official implementations; prior LTPP hard-negative work.
- Reused: frozen `reid` split, workbook parser semantics, YOLO box format,
  location-level independence rule, and the official YOLO11n checkpoint.
- New code justification: the existing pilot has no proposal-reranking path,
  no full-image reconstruction metric for tiled crops, and no fixed-budget
  localisation metric tied to SAM2 prompt cost.

## Frozen protocol

- Evidence identity: PaveTrack_PD V3; workbook SHA-256
  `72e3cfe6774a45a7e348b6c30a21b5eae30fb7bc111c4859c26744bdc6061e18`;
  archive size `5,694,108,370` bytes; publisher MD5
  `7fc53a04a6260a26b3ac39f489511adf`; selected image identities in
  `data_lock.json`.
- Comparator: YOLO11n proposal detector trained on the same training locations.
  Its raw confidence ranks the frozen proposal set.
- Necessary validity gates:
  1. every used image is listed in the workbook and has a valid crack/non-crack
     annotation;
  2. no `reid` overlaps train, validation, confirmatory test or reserve;
  3. crop mining and reranker fitting use training locations only;
  4. model selection and any score calibration use validation locations only;
  5. confirmatory pixels and labels are not read by training or selection code;
  6. evaluation reconstructs detections in full-image coordinates and groups by
     `reid`.
- Primary criterion: `macro_location_R@1FP_per_image(two_stage) -
  macro_location_R@1FP_per_image(proposer) >= 0.10` on the frozen confirmatory
  locations. Missing or unreadable confirmatory images make the run
  inadmissible; locations with no crack targets report false-positive burden
  but do not enter the recall macro-average.
- Threshold rationale: one false box prompt per image is a bounded downstream
  SAM2 and human-review cost. A ten-percentage-point absolute recall gain is the
  minimum useful improvement over the simpler detector for adding a second
  learned stage.
- Minimal fatal-regression guards, if any: the two-stage proposal set is
  identical to the comparator proposal set; the reranker may only rescore and
  cannot add boxes. Any test-data access before the final checkpoint and scoring
  rule are fixed invalidates the run.
- Explanatory diagnostics that cannot change the verdict: AP50/AP50-95,
  precision-recall curves, per-location results, error categories, proposal
  recall ceiling, crop AUROC, and runtime.
- Frozen implementation:
  1. prepare binary crack labels from workbook boxes; pothole/patch-only images
     remain explicit negative images;
  2. train one COCO-pretrained `YOLO11n` proposer for at most 50 epochs with
     patience 10, image size 1280, batch 8, seed `20261008`;
  3. infer at confidence 0.001, NMS IoU 0.70, and at most 300 proposals/image;
  4. mine reranker positives from padded crack boxes and proposals with crack
     IoU at least 0.50; mine negatives from proposals with crack IoU at most
     0.05, annotated potholes/patches that do not overlap a crack box, and
     exactly two annotation-free road-background crops/image; ignore proposals
     in the ambiguous IoU interval and fail if two road crops cannot be found;
  5. fine-tune one ImageNet-pretrained `MobileNetV3-small` for 15 epochs,
     batch 64, inverse-frequency sampling, AdamW learning rate `1e-4`, weight
     decay `1e-4`; select the minimum validation-loss checkpoint;
  6. rank the same proposals by either proposer confidence or the frozen score
     `sqrt(proposer_confidence * reranker_crack_probability)`.
  Initial artifacts are frozen before training: YOLO11n SHA-256
  `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`
  and MobileNetV3-small ImageNet state-dict SHA-256
  `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f`.
- Stop rule: one seed (`20261008`), one proposer and one MobileNetV3-small crop
  reranker. Stop after the primary comparison. Do not add detector families,
  tune on confirmatory locations, or invoke SAM2 if the primary gate fails.
- Minimum required evidence: data audit; exact Run receipt; validation-only
  selection record; confirmatory per-image detections and targets; per-location
  primary table; error montage; analysis README; independent code and evidence
  reviews.

### Conditional fields

- State capability / teacher or reference qualification: workbook polygons and
  bounding boxes are treated as image-level annotation reference only. They are
  not a physical crack state or registered trajectory.
- Holdout unit / leakage firewall / independence axis: `reid` location. The
  confirmatory locations are `6227`, `1059`, `2291`, and `2227`. Locations `10`
  and `1889` were viewed in the earlier pilot and are excluded from confirmation.
- Uncertainty or deployment decision contract: not claimed. The fixed false
  prompt budget is an evaluation cost, not a calibrated deployment policy.

### Frozen outcome map

```text
validity fails                         -> inadmissible
validity passes + primary passes       -> supports
validity passes + primary fails        -> negative
primary cannot be computed/identified  -> inconclusive
```

## Producer and Run readiness

- Authorised producer alias / hostname: `gpu-server` / `D-26-09`, GPU 1 subject
  to a fresh preflight. Taobo was unreachable at the first 2026-10-08 check.
- Commit or immutable snapshot / dirty status: pending code review and commit.
- Runner / config / runtime: pending; official COCO-pretrained YOLO11n proposer,
  ImageNet-pretrained MobileNetV3-small reranker, seed `20261008`.
- Output / archive / log / retrieval route: fresh
  `C:\Users\xw436\pavetrack_runs\S01-E001-R008\`; retrieve compact receipts,
  metrics, tables and figures to the local experiment evidence folder.
- Ownership and process-safety constraints: use only GPU 1 after checking it is
  free; record Windows PID, command, cwd, GPU and log; do not interrupt GPU 0.

## Amendments

- `v2`, 2026-10-08, before any training: first independent code review returned
  `FAIL`. Strengthened the confirmatory hash chain, crop/reranker lineage,
  partition checks, deterministic tie ordering, overlapping-distress exclusion,
  and exact road-background count. The scientific question, primary estimand,
  threshold and stop rule did not change.
- `v3`, 2026-10-08, before any training: second independent review also returned
  `FAIL`. Added real model-container and proposer-receipt checks before test
  preparation, record-level crop content hashes, padded-distress overlap checks,
  confirmatory membership validation, and ex-ante initial-weight hashes. The
  scientific contract remains unchanged.
- `v4`, 2026-10-08, before any training: third independent review returned
  `FAIL`. Replaced the ZIP-only model check with semantic YOLO and MobileNet
  loading/schema checks, bound every prepared image and YOLO label by content
  hash, and made the frozen producer runtime fail closed. The scientific
  contract remains unchanged.
- `v5`, 2026-10-08, before any training: fourth independent review returned
  `FAIL`. Froze and now verifies GPU1 by physical name, UUID, PCI bus ID and
  driver; added a canonical YOLO11n architecture fingerprint to the semantic
  proposer gate. The scientific contract remains unchanged.
- `v6`, 2026-10-08, before any training: fifth independent review returned
  `FAIL`. The runtime gate now rejects `CUDA_VISIBLE_DEVICES` remapping and
  resolves the Torch-visible device to physical `nvidia-smi` identity by UUID.
  The proposer gate now fingerprints the instantiated module graph,
  connectivity and parameter/buffer shapes. The scientific contract remains
  unchanged.
- `v7`, 2026-10-09, before any training: sixth independent review returned
  `FAIL`. Extended the instantiated-graph fingerprint to include each module's
  `extra_repr`, public immutable structure attributes, instance-level forward
  override state and hook counts. This covers shape-preserving changes such as
  stride, padding, dilation, groups and operator configuration. The scientific
  contract remains unchanged.
- `v8`, 2026-10-09, after the first observed training loop but before any
  admissible result: R004 exposed a physical-device placement bug. The runtime
  gate correctly identified physical `cuda:1`, but Ultralytics later received
  the string `"1"`, set `CUDA_VISIBLE_DEVICES` after Torch had already
  initialised, and returned `torch.device("cuda:0")`. The training PID was
  observed on physical GPU 0 and was terminated during epoch 5. R004 is
  inadmissible and has no scientific result. V8 passes the already validated
  `torch.device("cuda:1")` object directly to every Ultralytics train/predict
  call and adds a regression test that forbids remapping. The scientific
  question, data, estimand, primary metric, threshold and stop rule do not
  change.
- `v9`, 2026-10-09, after R005 completed fitting but failed before its proposer
  receipt was written: the instantiated-graph validator included Ultralytics
  runtime metadata (`names`, `args`, `pt_path` and the last inference `shape`).
  A fresh one-class graph and the fitted checkpoint had the same 319 modules,
  connectivity, operator configuration and parameter/buffer shapes, but those
  metadata fields made the frozen hash impossible to satisfy. V9 excludes only
  runtime metadata from the graph fingerprint; class names, one-class head,
  architecture, connectivity, tensor shapes and immutable operator attributes
  remain independently checked. R005 remains inadmissible. The scientific
  question, data, estimand, primary metric, threshold and stop rule do not
  change.
- `v10`, 2026-10-09, after the R006 proposer passed all gates but train crop
  mining stopped before writing a manifest: one low-confidence YOLO proposal
  lay fully outside the image and had zero area after clipping. V10 explicitly
  drops only detector proposals with no in-image area in both crop mining and
  evaluation, records the dropped count, and retains partially visible boxes
  after clipping. This keeps the raw and two-stage arms on the identical valid
  proposal set. R006 crop outputs are inadmissible. The scientific question,
  data, estimand, primary metric, threshold and stop rule do not change.
- `v11`, 2026-10-09, after R007 reproduced the crop failure under v10: the
  offending Ultralytics proposal already had equal boundary coordinates
  (`y1 == y2 == 0`). V11 treats equal coordinates as a zero-area proposal to
  drop and count, while strictly reversed or non-finite coordinates still fail
  closed. R007 crop outputs are inadmissible. The scientific question, data,
  estimand, primary metric, threshold and stop rule do not change.

## Code review

- Reviewer task: v11 independent read-only review pending.
- Bound commit / runner / config / data lock / protocol revision: the v11
  immutable file-hash bundle is pending review. V10 passed review, but R007
  showed that an equal-coordinate detector output must enter the zero-area path.
- Verdict: v10 `PASS` is superseded for execution; v11 pending. No further
  producer training is authorised until v11 review passes.
- Blocking finding: confirm that v11 drops only zero-area-after-clipping
  detector proposals, applies the same filter in mining and evaluation, and
  preserves an identical proposal set for both scoring arms.

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S01-E001-R001 | proposer launch; seed 20261008 | failed before Python worker | verified | remote failure receipt |
| S01-E001-R002 | proposer launch; seed 20261008 | failed before Python worker | verified | remote failure receipt |
| S01-E001-R003 | proposer pre-training gate; seed 20261008 | failed: frozen weights absent from staging | verified | remote completion receipt |
| S01-E001-R004 | proposer; seed 20261008 | cancelled/inadmissible: PID observed on physical GPU 0 | partial, logs preserved | remote run root |
| S01-E001-R005 | v8 proposer; seed 20261008 | training completed at epoch 44; failed post-fit graph gate before receipt | verified | inadmissible failure receipt |
| S01-E001-R006 | v9 proposer + crop mining; seed 20261008 | proposer succeeded; crop mining failed on zero-area clipped proposal before manifest | verified | proposer valid; crop stage inadmissible |
| S01-E001-R007 | v10 proposer + crop mining; seed 20261008 | proposer succeeded; crop mining failed on equal-coordinate zero-area proposal before manifest | verified | proposer valid; crop stage inadmissible |
| S01-E001-R008 | v11 proposer + reranker + frozen comparison; seed 20261008 | blocked pending v11 review | pending | pending |

## Evidence review

- Reviewer task: pending.
- Bound Run IDs: pending.
- Bound analysis package: pending.
- Verdict: pending.
- Blocking findings: pending.

## Scientific verdict

Pending.

## Claim impact

No claim change before the frozen run and independent evidence review.

## Next action

Obtain an independent v11 review. If it passes, regenerate and audit the v11
development manifest, then start the fresh R008 run. Earlier proposer evidence
is retained for provenance, but failed crop stages are not reused.
