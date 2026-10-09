# S01-E002 producer runbook

No command below is authorised until the exact code-review bundle receives an
independent `PASS` or `PASS_WITH_NONBLOCKING_NOTES` with no blocking finding.
Run on `gpu-server` / `D-26-09`, physical GPU 1 only, after a fresh process and
GPU-identity preflight.

## Stages before confirmatory access

1. Stage the reviewed commit, workbook, already acquired development images,
   official `yolo11n.pt`, the S01-E001 full-frame proposer, and the S01-E001
   reranker. Verify every frozen SHA-256.
2. Run all `tests/pavetrack_cv` and `tests/pavetrack_tiled_cv` tests under the
   frozen producer environment.
3. Prepare the E002 development full-image manifest with
   `prepare_development.py`. The image roots may contain development locations;
   they must not contain the five E002 confirmatory locations.
4. Generate the tiled detector dataset with `prepare_development_tiles.py`.
5. Train exactly one tiled proposer with `train_tiled_proposer.py`.
6. Run `evaluate_development.py --split validation`. This evaluates the frozen
   full-frame baseline and the repaired route on the same validation images and
   selects one of the three predeclared scoring rules.
7. Run `freeze_for_test.py`. Record all hashes and copy the authorization to an
   immutable run directory.

## Confirmatory boundary

Only after stage 7 succeeds may the producer acquire or expose images from
locations 75, 220, 577, 956 and 1139 to the run workspace.

1. Download only the authorized location archives. Verify archive member size
   and CRC before extraction, then record image SHA-256 values.
2. Run `prepare_confirmatory.py`; it validates the authorization chain before
   importing the workbook reader or resolving an image path.
3. Run `evaluate_development.py --split test` with the authorization and the
   frozen validation evaluation. The test path evaluates only the selected
   score; it does not compare the other score candidates.
4. Stop after the primary and candidate-coverage gates. Do not tune tile size,
   stride, NMS, scoring, threshold, architecture or SAM2 on these images.

## Outcome actions

- Both gates pass: archive evidence, obtain independent evidence review, then
  open a separate SAM2 experiment on a later unused reserve subset.
- Either gate fails: archive evidence and close this localisation family as
  negative for the bounded PaveTrack PD claim.
- Any hash, split, runtime, GPU, missing-image or authorization mismatch:
  classify the run as inadmissible and do not interpret metrics.

