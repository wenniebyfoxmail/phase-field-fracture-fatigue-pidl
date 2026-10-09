# HQ-PUBLIC-REF-001-R001 retrieval and integrity audit

Date: 2026-10-09. Status: `PASS_RUN_COMPLETE_AND_RETRIEVED` for execution integrity only.

## Identity

- Producer: `gpu-server`; hostname `D-26-09`; GPU `0`; runner PID `55280`.
- Scheduled task `HQ-PUBLIC-REF-001-R001-20261009` completed with task result `0`; `scheduled.exitcode.txt` is `0`; scheduled stderr is empty.
- Runner receipt status: `succeeded`.
- Runner snapshot: `e17179cba87cf2ae134b7e99d82614c6eacd49bd5c54ef17f000468e03a1347e`.
- Data lock: `19f0e55ba20c8758a06f72f3b3300bd25b6821d241b01f690a75777ff3c794d8`.
- Checkpoint SHA-256 in receipt and independently recomputed locally: `50343ededc14acd3990e2fc3db20d5ba0074c0dd169e34e67863954a28a1c106`.
- Total runner time: 9,766.41 seconds, or 2.713 hours, within the frozen budget.

## Frozen procedure and cohort

- Training and validation completed 40/40 epochs. `fit_status.json` records epoch 40, batch start 1260, phase `validated`, and a valid checkpoint.
- Epoch 40 was the selected checkpoint with validation error `0.1581024182118394`.
- Final score rows: 438 exactly: 80 METU internal-test images and 358 BuildCrack external-diagnostic images.
- BuildCrack references: 355 nonempty and 3 empty, exactly as frozen.
- Final evaluation followed the completed fit by about 208 seconds based on artifact timestamps, well below the separate one-hour allowance.

## Retrieval integrity

- Remote output contained 896 files totaling 8,304,786,004 bytes: 438 probability arrays, 443 PNG files, 11 JSON files and 3 PyTorch checkpoint/state files, plus the analysis README.
- Remote archive SHA-256 and local archive SHA-256 both equal `5db41e82c59721a6cebc61fe0bd242c3c8f8e07fd287f298c97d3c97acce8c0a`.
- The remote 896-row file manifest has SHA-256 `b2ad4532fb313c46ca79823f9f2a33e5da3f20ed8954b56e87a974f568a71f18` on both machines.
- Local verification found 896/896 paths present with matching byte counts and SHA-256 values.
- All 438 `.prob.npy` files are two-dimensional, finite and within `[0,1]`.
- All reported score fields used by the decision are finite.
- Independent recomputation from `final_scores.json` exactly reproduced both primary AURCs and their difference.

The remote original output and archive remain in place. The retrieved 8.30 GB result is stored under `retrieved_2026-10-09/HQ-PUBLIC-REF-001-R001/` and is intentionally git-ignored. The tracked `remote_sha256_manifest.csv` and `RETRIEVAL_RECEIPT.json` anchor its content identity.

This audit establishes execution identity, completeness and numerical reproducibility of the reported finite-cohort summaries. It does not establish the scientific usefulness of the model or uncertainty ranking; that judgment is made separately.
