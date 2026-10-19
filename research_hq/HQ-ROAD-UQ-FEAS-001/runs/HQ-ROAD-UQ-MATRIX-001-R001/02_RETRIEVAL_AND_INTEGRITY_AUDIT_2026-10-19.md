# Retrieval and integrity audit — HQ-ROAD-UQ-MATRIX-001-R001

- Scheduled task `HQ-ROAD-UQ-MATRIX-001-R001-20261019` ended `Ready` with `LastTaskResult=0`; `scheduled.exitcode.txt` is `0` and stderr is empty.
- The formal receipt is `succeeded` for the authorized run ID, evaluator/protocol snapshot `49271e…e89b8` and data-lock SHA-256 `1a4a80…d51ba`; it records zero training steps and `road420_access=false`.
- All 12 formal remote files were retrieved to `retrieved_2026-10-19/HQ-ROAD-UQ-MATRIX-001-R001/`. File sizes and SHA-256 values exactly match `remote_sha256_manifest.json`. Remote originals remain at `C:\Users\xw436\jobs\HQ-ROAD-UQ-MATRIX-001-R001`.
- The four cell CSVs contain 118/118 CFD rows and 384/384 GAPS rows; GAPS has 382 nonempty and 2 empty references in each model cell. All IDs are unique and all exported numeric values are finite.
- Independent arithmetic reproduced every reported cell mean, risk at 25%, risk reduction and AURC with maximum absolute difference 0. The 5,000-replicate paired bootstrap intervals match exactly.
- Independent comparison to the frozen diagonal CSVs reproduced 118 old/CFD cases within `2.38e-8` and 382 repair/GAPS nonempty cases within `2.81e-6`, both below the frozen `1e-5` comparability limit.

Audit status: `PASS_COMPLETE_RETRIEVED_AND_RECOMPUTED`. The recomputation uses the exported per-image rows and does not perform a second model inference; pixel-level predictions were not exported, so tolerant-overlap arithmetic is verified as aggregate row arithmetic rather than regenerated from masks.

Evidence: `retrieved_2026-10-19/independent_recomputation.json`, `remote_sha256_manifest.json`, `remote_preflight.json`, `task_status.json`, the empty scheduled logs and the 12 formal outputs.
