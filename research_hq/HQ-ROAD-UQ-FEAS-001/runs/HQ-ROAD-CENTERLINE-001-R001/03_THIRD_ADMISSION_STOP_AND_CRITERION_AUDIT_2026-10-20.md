# D5 third-admission stop and criterion audit — 2026-10-20

## Decision

`STOPPED_BEFORE_SCIENTIFIC_EXECUTION__NO_FOURTH_CHECK`

The single additional zero-start admission check was consumed on D-26-09. It produced both required on-disk JSON receipts, but the child receipt returned `FAIL_ADMISSION`; therefore the wrapper returned `FAIL_ADMISSION_WATCHDOG` and the scheduled task was not created. The scientific comparison did not start.

## Frozen identity

- Experiment: `HQ-ROAD-CENTERLINE-001`
- Run: `HQ-ROAD-CENTERLINE-001-R001`
- Producer: `gpu-server`, hostname `D-26-09`, GPU `0`
- Reviewed code snapshot: `cd28472154eb4912a6c0f975943512052ddcedf88f2dc1bdbb36bb54831c64ae`
- Data-lock SHA-256: `563cf2fc1410a5872086f96c9769faeaaf2d4b14e137eba52665e8d3f29c122e`
- Staged archive SHA-256: `f1d03940611c922ea8db432671902f887e3434870a985d5880259caf670b01c9`

## Decisive evidence

The child receipt failed after 2.016 seconds because the admission script rejected every row returned by `nvidia-smi --query-compute-apps` on GPU 0. The rows named `ChatGPT.exe`, `dwm.exe`, `explorer.exe`, `LogonUI.exe`, `ShellExperienceHost.exe`, two `msedgewebview2.exe` processes and `ms-teams.exe`; every row reported GPU memory as `[N/A]`. The reviewed script rejects any non-empty result from that query.

This evidence establishes a conflict with the frozen admission rule. It does not establish that another scientific or training workload occupied GPU 0. The process names and unavailable per-process memory make the rule too coarse to distinguish ordinary desktop GPU clients from a competing producer workload. The free-memory check ran before this rejection and did not trigger, but the failure receipt did not preserve the exact free-memory value.

The authoritative wrapper receipt records check number 3, no timeout, a parseable child failure receipt, zero training and optimizer steps, and no Road420 access. A separate read-only post-failure check found no scheduled task, no canonical output directory and no Python `d5_runner.py` process.

## Integrity

- Child receipt SHA-256: `7eade12c6bdb3a04fd5e1c55d11a9776a7eb69efc6a225234a406dc1f97250fb`
- Wrapper receipt SHA-256: `137ed3e648627ff51ecc654beee3e21a41eabed387bf36a4e4b6d18fcca5dfee`
- Remote approval copy SHA-256: `96417a02cbc09117e82d45ffa8c01972d8a503f504a999197e183d9170edddd0`
- Captured wrapper stdout and stderr logs are empty and hash to SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## What this means for the research route

D5 has no scientific result. It cannot support or reject the centreline/distance-field target, nor can it choose between the current method and a new method route. The result instead falsifies one operational assumption: “any `query-compute-apps` row means GPU conflict” is not usable on this producer in its current desktop state.

A constructive next package should preserve the scientific contract and revise only admission semantics. A new Run ID would require fresh explicit authority. Its frozen GPU-conflict rule should combine the already-required free-memory threshold with positive evidence of a competing CUDA/scientific workload, rather than rejecting named desktop clients with `[N/A]` memory. It should also record the raw GPU query and exact free memory on both pass and fail. No such package or rerun is authorised by this stop record.

## Boundary

No fourth admission check, scheduled-task creation, scientific retry, host/GPU switch, Road420 access, data mutation, external message, publication or public push occurred.
