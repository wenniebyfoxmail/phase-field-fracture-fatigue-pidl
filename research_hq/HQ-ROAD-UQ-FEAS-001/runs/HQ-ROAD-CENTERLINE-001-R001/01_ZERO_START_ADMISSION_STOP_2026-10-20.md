# D5 zero-start admission stop — 2026-10-20

## Status

`STOPPED_BEFORE_SCIENTIFIC_EXECUTION__ADMISSION_EVIDENCE_MISSING`

The reviewed D5 package did not enter training or model inference. No scheduled task was created and the canonical output directory was not created by this task. Road420 remained sealed.

## Evidence

1. Zero-start check 1 connected to the recorded `gpu-server` alias and returned `ModuleNotFoundError: No module named 'skimage'` from `C:\Users\xw436\pavetrack_env\Scripts\python.exe` before the combined admission JSON could be emitted.
2. The missing dependency was installed without dependencies into the new Run-specific directory `C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020`; the shared environment was not modified. The dependency-path control then passed focused independent read-only re-review.
3. Zero-start check 2 connected and exited with status 0 after 9.1 seconds, but emitted no admission JSON. Its only captured text was the SSH host-key / non-post-quantum warning. Consequently hostname, GPU 0 process state, canonical path vacancy, source filenames and free disk were not evidenced by that check.

The two permitted zero-start checks were consumed, with approximately 43 seconds of cumulative check wall time, within the 120-second cap. The absence of the required second receipt is an admission-control failure, not a scientific result.

## Frozen state and next authority needed

- Reviewed code snapshot: `9c5a7c759f4db6a67595a424302bd65bc72bbffd604887d48b09a57de591480e`.
- Data-lock SHA-256: `563cf2fc1410a5872086f96c9769faeaaf2d4b14e137eba52665e8d3f29c122e`.
- Independent focused verdict: `REVIEW_PASS`.
- Training steps: 0; optimizer steps: 0; scientific attempts: 0.

To resume this same Run ID, the user must explicitly add one bounded zero-start admission check. That check should use a staged `.ps1` file with a required on-disk JSON receipt rather than stdout-only PowerShell. If the receipt passes, the already-authorised unique scientific run can launch without changing its scientific contract; a failed or missing receipt stops again.
