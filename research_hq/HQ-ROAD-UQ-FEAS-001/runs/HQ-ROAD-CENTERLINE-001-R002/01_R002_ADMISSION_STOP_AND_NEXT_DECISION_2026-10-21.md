# D5 R002 admission stop and next decision — 2026-10-21

## Decision

`STOPPED_BEFORE_SCIENTIFIC_EXECUTION__R002_CHECK_CONSUMED__NO_RERUN`

The single authorised R002 admission check ran on D-26-09 and returned `FAIL_ADMISSION` in the child receipt and `FAIL_ADMISSION_WATCHDOG` in the outer receipt. No scheduled task was registered, no canonical output or cache directory was created, no matching runner remained, and no launch receipt exists. R002 therefore produced no model, metric or scientific result.

The revised GPU rule did solve the R001 false-positive blocker. The check matched the required GPU UUID, recorded 97,269 MiB free GPU memory and 2,881.796 GiB free disk, and strictly classified all eight reported `[N/A]` rows as live, path-matched desktop processes. No competing Python/CUDA/HQ runner was identified. The route stopped later, while reading the environment probe's child-process exit status.

## Frozen identity and cost

- Experiment: `HQ-ROAD-CENTERLINE-001`
- Run: `HQ-ROAD-CENTERLINE-001-R002`
- Producer: `gpu-server`, hostname `D-26-09`, physical GPU `0`
- Expected and observed GPU UUID: `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`
- Reviewed code snapshot: `b9c8f51638bb1201f2384d228e503ef7f12219173353c8d662f866644b3e0953`
- Data-lock SHA-256: `a88c50b5f76df462cf69e136455c8b04c47c95c101e23af254a85b3b8ec3ce28`
- Scientific-protocol fingerprint: `a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a`
- Staged archive SHA-256: `00e5f7c24756e92cbd2cabc69aa4a761d5e9352d1bef8cd3ad9e688987a8d026`
- R001 cost preserved: three admission checks and approximately 45.544 seconds
- R002 cost: one admission check; child 11.830 seconds and wrapper 12.359 seconds
- Scientific execution: false; training steps 0; optimiser steps 0; Road420 access false

The original package clock remained `2026-10-20T21:59:35Z` to `2026-10-21T01:59:35Z`. The wrapper still recorded 10,475.909 seconds remaining when it stopped, so time and compute capacity were not the blocking condition.

## Claim audit

| Claim | Direct evidence | Audit result | Limit |
|---|---|---|---|
| The revised GPU criterion admitted ordinary desktop clients rather than treating every row as a conflict. | Child receipt records successful GPU queries, exact UUID, 97,269 MiB free, eight raw rows and eight `KNOWN_DESKTOP_BACKGROUND_NA_MEMORY` classifications; its four synthetic classification fixtures have the expected truth values. | **SUPPORTED for this observed machine state.** | This does not prove the classifier covers every future Windows/CUDA process state. |
| No competing scientific runner was identified during admission. | Every raw row is tied to a live CIM process with matching executable name/path and `[N/A]` memory; no Python/HQ runner appears. | **SUPPORTED for the captured query.** | It is a point-in-time observation, not a guarantee about later occupancy. |
| The environment itself was successfully importable. | `environment.stdout.json` is valid JSON and reports Python 3.12.14, torch 2.11.0+cu128, torchvision 0.26.0+cu128, NumPy 2.5.2, SciPy 1.18.1, scikit-image 0.25.2 from the task-local dependency directory, matplotlib 3.11.2, psutil 7.0.0 and CUDA 12.8; `environment.stderr.log` is empty. | **SUPPORTED for import/version reporting.** | It is not the full D5 preflight and does not prove training correctness. |
| The declared failure is most consistent with unreliable child exit-code capture, rather than an import failure. | The environment command produced valid expected stdout and empty stderr, yet the admission record threw `environment probe failed`. The script tests `Start-Process` object's `ExitCode` without persisting the child's exit code independently. The outer watchdog also recorded a null child exit code despite a completed child receipt. | **SUPPORTED AS THE LEADING CONTROL-DIAGNOSIS; exact process status was not preserved.** | Because the actual child exit code was not recorded, this cannot be upgraded to proof that the Python process returned 0. |
| No scientific execution occurred. | Both receipts record `scientific_execution_started=false`, 0 training and optimiser steps, and no Road420 access. A separate read-only check found no task, output, cache, launch receipt or matching process. | **SUPPORTED.** | No inference about the centreline model follows. |
| R002 can decide whether the centreline/distance-field route works. | No preflight, scheduled task, training or evaluation completed. | **NOT SUPPORTED.** | D5 remains scientifically unanswered. |

## Decisive control defect

The admission script launches the environment probe with `Start-Process`, waits for it, and then tests the process object's `ExitCode`. It does the same for the D5 preflight. The captured environment JSON and empty stderr show that the command reached and completed its intended reporting path, while both the inner and outer control layers failed to preserve a numeric child exit code reliably.

The next control package should therefore avoid treating the in-memory `Start-Process` property as the sole authority. A small child wrapper should write the actual `$LASTEXITCODE` to a dedicated sidecar after each Python command. The parent may enforce the timeout, but it should decide pass/fail only after reading a parseable numeric sidecar together with the required stdout/receipt. Missing, malformed or non-zero exit-code sidecars remain hard stops. The same rule must cover the environment probe, preflight and outer admission child. Local tests should exercise exit 0, exit non-zero, missing sidecar, malformed sidecar and timeout before any remote check.

## Next method decision

Do not change the scientific method yet. R002 removed the earlier GPU-classification blocker but stopped before the centreline representation was tested. A source-specific renderer or a new model family would still be a response to launcher mechanics rather than model evidence.

The constructive next action is a separately authorised `HQ-ROAD-CENTERLINE-001-R003` that:

1. inherits the R002 scientific protocol and all data seals unchanged;
2. changes only child exit-code capture and the new Run/task/output/cache/stage identities;
3. receives a newly bounded package clock rather than reusing the expired R001/R002 clock;
4. allows one admission check and, only after a complete positive receipt, one scientific attempt;
5. preserves the dual-source CFD/GAPS decision and keeps Road420 plus CRACK500 test sealed.

If a valid R003 completes and both CFD and GAPS remain near the frozen failure floor, stop the shared-output centreline route and propose the already identified shared crack-evidence field with source-specific renderers. If at least one source shows a material non-degenerate gain without severe collapse on the other, retain the centreline component and then design the UQ comparison. No R003 check, run or method switch is authorised by this document.

## Evidence integrity

- Child receipt SHA-256: `de3ed570479dc919d1150325231f1b2d26dce94220e16a50221f55b98535a657`
- Wrapper receipt SHA-256: `19a3137dc70cefe8456a9e0b63cba6a151aadfeddaa325d891b4156f55f08851`
- Environment stdout SHA-256: `9759858513955a528d0d8441d56076c0cc8d6d7f7a6a86d93e2805d3a4f8b0d2`
- Empty environment stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Post-failure state SHA-256: `8dc8331d5dedb93508756f029a723f0e8c5af2c3efe0a46472e5dee7bfc04226`
- Complete 12-file retrieved-evidence manifest: `R002_EVIDENCE_SHA256_2026-10-21.json`

## Boundary

No second R002 check, scheduled-task registration, training, scientific retry, host/GPU switch, Road420 or CRACK500-test access, data mutation, external message, publication or public push occurred.
