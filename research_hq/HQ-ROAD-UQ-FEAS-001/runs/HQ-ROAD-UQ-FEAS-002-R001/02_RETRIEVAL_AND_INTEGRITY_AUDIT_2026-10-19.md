# Retrieval and integrity audit — HQ-ROAD-UQ-FEAS-002-R001

## Execution integrity

- Scheduled task `HQ-ROAD-UQ-FEAS-002-R001-20261019` ended `Ready` with `LastTaskResult=0`; `scheduled.exitcode.txt` is `0` and stderr is empty.
- The receipt is `succeeded` and matches the authorised identity: host `D-26-09`, GPU `0`, runner snapshot `79132eec…4b65`, data-lock SHA-256 `ff95bd1e…a2a0`, and `road420_access=false`.
- Training completed 40/40 epochs without budget stop. The A-validation-only selection rule chose epoch 37 with mean Dice 0.739295.
- The producer wrote 13 expected files. Remote and retrieved byte sizes and SHA-256 hashes match for all 13.
- Receipt hashes match the retrieved checkpoint (`92cd9374…27e2`) and result (`7ba4e1d4…0b50`). The checkpoint loads strictly into `ResNet18UNet`.

## Evidence inventory

- A validation: 341 rows; A test: 200 rows.
- GAPS384 primary nonempty cohort: 382 rows; empty-reference cohort: 2 rows.
- All numeric Dice/error/uncertainty fields are finite.
- Selection history has exactly 40 entries and independently identifies epoch 37 as the maximum validation Dice.
- Independent recomputation from the retrieved CSVs exactly reproduced full risk, all three first-95 risks, F1, F2, F3 and the final verdict.

Audit evidence is in `retrieved_2026-10-19/independent_recomputation.json`, `remote_sha256_manifest.json` and `SHA256SUMS.txt`. The remote originals remain in `C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001`.

**Integrity decision:** `PASS_COMPLETE_RETRIEVED_AND_RECOMPUTED`.
