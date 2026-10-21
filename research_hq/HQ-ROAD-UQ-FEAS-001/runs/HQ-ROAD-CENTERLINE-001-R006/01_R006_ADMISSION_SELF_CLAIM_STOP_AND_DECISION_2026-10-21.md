# HQ-ROAD-CENTERLINE-001-R006 — admission self-claim stop

## Decision

- Run execution: **failed during the only R006 admission; scientific worker not started**.
- Run retrieval: **verified**; remote originals remain on `D-26-09` and 19 remote files (52,631 bytes) were copied into `retrieved_2026-10-21/` before the local manifest and recomputation were added.
- Experiment verdict: **inconclusive**. R006 provides no D5 model, uncertainty, centreline-target, or 40-epoch result.
- Research disposition: **stop R006 without retry**. A future run would require new authority and a fresh Run ID.

## Bound identity

- Authority: `HQ-D5-EXPLICIT-PACKAGE-ENTRY-R006-20261021`, delegated by the human-authorised HQ thread `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`.
- Producer: `gpu-server` / `D-26-09` / GPU 0, UUID `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`.
- Reviewed code snapshot: `7d5fd0f3867b94cad7b33406d6c3a74c55e867d6858912547fd3911dc6adcf88`.
- Data lock: `a9a50e087be12ba5711d1cf87e640a97b6f06e155d4ef1e42d5b2a29e4b86934`.
- Scientific fingerprint: `a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a`.
- Clean archive: `hq_road_centerline_001_r006_7d5fd0f3_clean.tar`, 516,608 bytes, SHA-256 `78637a08d96fa1cf69ec6edfb8a3186124a2fe0fa1d8f4b7f0df76a8ab3ac891`.
- Mechanical clock: `2026-10-21T00:54:56.1800215Z`, one 90-second cumulative window. Original package/scientific deadlines remained `01:59:35Z` / `01:49:35Z`.

## What happened

The reviewed package first passed local tests and independent code review. It locked exact package `__file__`, `__spec__.origin`, `SourceFileLoader`, singleton `__path__`, scikit-image `0.25.2`, and the exact `skimage.morphology._skeletonize.py` SHA-256. The cumulative watchdog used the remaining shared-clock milliseconds and owned-child termination.

The first remote extraction wrapper parsed its entry path with an embedded carriage return and stopped before invoking the reviewed entry. This was an operator-side wrapper observation, not an admission or scientific attempt. Within the same already-open 90-second clock, the existing reviewed entry was invoked once; no second clock, archive, admission receipt, or Run ID was created.

The only R006 admission then stopped in 3.067 seconds. Its broad process guard selected the enclosing `cmd.exe` and `powershell.exe` processes running `execute_r006_once.ps1`, because both command lines contained the R006 Run ID. It therefore raised `existing HQ/D5 runner claim detected` against its own owned ancestor chain. The owned admission controller recorded child/controller exit code 2, with no timeout.

The outer mechanical receipt separately serialized its admission `exit_code` as null after `Start-Process`, so it reported the less specific `R006 admission failed:`. This is a secondary receipt defect; the inner owned-controller and admission receipts establish the actual nonzero exit and self-claim error.

## Claim audit

The following evidence agrees:

1. `admission_receipt_remote.json`: `FAIL_ADMISSION`; both selected processes are the enclosing R006 executor; `scientific_execution_started=false`, `training_steps=0`, `optimizer_steps=0`, `road420_access=false`.
2. `admission_wrapper_receipt_remote.json`: `FAIL_ADMISSION_WATCHDOG`, owned child `COMPLETE_NONZERO`, child/controller exit code 2, no timeout, no remaining admission processes.
3. `mechanical_window_receipt.json`: no registration object and no launch object.
4. The scheduled task and canonical output were absent in the post-stop read-only check.
5. Environment, preflight, scientific-worker context/exit, and launch receipts are absent from the retrieved run directory. Thus the explicit package entry was not exercised on the producer.

The run proves only that the R006 admission ownership guard rejects its own outer executor. It does not establish whether the explicit scikit-image entry would succeed in the scheduled scientific context. Road420 and the CRACK500 test role remained sealed.

## Evidence pointers

- `retrieved_2026-10-21/retrieved_sha256_manifest.json`
- `retrieved_2026-10-21/independent_recomputation_2026-10-21.json`
- `retrieved_2026-10-21/HQ-ROAD-CENTERLINE-001-R006/admission_receipt_remote.json`
- `retrieved_2026-10-21/HQ-ROAD-CENTERLINE-001-R006/admission_wrapper_receipt_remote.json`
- `retrieved_2026-10-21/HQ-ROAD-CENTERLINE-001-R006/mechanical_window_receipt.json`

## Future repair boundary

If a new run is authorised, its admission guard should identify only an exact scientific-worker command/approval/output identity, or explicitly exclude the verified owned ancestor chain. The outer watchdog should snapshot a concrete child exit code after process refresh. These are control repairs; R006 is frozen and no R007 is authorised here.
