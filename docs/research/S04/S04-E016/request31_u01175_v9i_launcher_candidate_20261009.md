# Request 31 U0.1175 v9i launcher candidate

Date: 2026-10-09
Class: C0 launcher capability only
Status: `PASS_REQUEST31_V9I_LAUNCHER`
Scientific payload/result: none

## Frozen candidate

- Windows derived: `C:\q4runs\request31_u01175_derived_snapshot_20261009_v9i`
- Windows review: `C:\q4runs\request31_u01175_launcher_review_20261009_v9i`
- manifest SHA256: `b9c92ade6c192b3f6be909ca24a7cf788e8b530ccf6b354e4f4ee8a9de8012c5`
- diff-contract SHA256: `e39c4081de0ad6b2daa20f3286a5b5154a30e14821b5288cdd50c3e21edd3bc4`
- canonical parent commit: `862992a60edc7f59335365beacb5c71fc8592a7a`
- Mac evidence: `local_archive/experiments/S04-E016/request31_u01175_v9i_launcher_review_20261009/`
- retrieved files: 112; manifest mismatches: 0

## Decisive evidence

- MATLAB implementation 11/11; authorization 10/10; inherited spawn 13/13;
  detachment/identity/cleanup 11/11; release behavior 7/7.
- Positive cleanup fixture froze one task-owned root and all three observed
  descendants. Root and every descendant exited; every explicitly stopped PID
  belonged to that owned tree; the unrelated sidecar stayed alive and was then
  removed by fixture cleanup. MATLAB=0 and `solver_called=false`.
- Machine-readable Mac timeline is bound to the manifest, run ID and probe
  nonce. A returned with exit 0 at `2026-10-09T11:17:47.712353Z`; B started at
  `2026-10-09T11:17:47.720583Z` and exited 0, so `A_return < B_start=true`.
- The gated cross-SSH probe passed exact creator/worker identity, atomic
  preflight consumption, release token, worker-owned exact R2025b engine and
  terminal receipt. The batch only paused for 20 seconds; final MATLAB=0,
  production output absent and scientific payload false.

Failed staging revisions v9 through v9h are not candidates and created no
scientific output. v9f's earlier PASS did not cover the subsequently requested
positive cleanup and raw Mac timeline evidence, so v9i supersedes it.

## Gate

Independent read-only review returned `PASS_REQUEST31_V9I_LAUNCHER`. No
production retry is authorised. A later production request would still require a new real
approval/nonce, fresh full producer preflight and explicit user authorization.

## Production launch

The user subsequently authorised exactly one U0.1175 production launch. Full
preflight passed at `2026-10-09T11:25:16.2134979Z`; nonce
`f55c28d2-fd3c-45b0-83c0-8b4bee1ea90b` was consumed once. Connection A
returned exit 0 at `11:25:30.179Z`; connection B started at `11:25:34.677Z`
and returned exit 0 after releasing the exact worker.

Initial execution evidence: worker 48012 -> MATLAB launcher 21260 -> exact
R2025b engine 13956. Between the first and second health checks,
`production.stdout.log` grew from 18,732 to 48,730 bytes; stderr remained zero,
and the production tree created `fem_archive/`, `provenance/`, `states/`, and
`static/`. At that time the status was `RUNNING_HEALTH_CONFIRMED`.

At `2026-10-09T11:40:14Z`, the same process identities were live and the
`states/` directory contained 51 files through `c0010_s05.mat` (including
`c0010_s04.mat`). The newest state write was at `11:40:09Z`; no worker-exit or
terminal sentinel existed. The retrieved launch evidence is stored at
`local_archive/experiments/S04-E016/request31_u01175_v9i_production_launch_20261009_v1/`.

The run later terminated abnormally at `2026-10-09T13:12:51Z`. The final
persisted state is `c0064_s04.mat`; 320 state files total 4,620,877,610 bytes.
The MATLAB crash dump records the primary R2025b `abort()` at 13:12:50 UTC,
and stdout ends with MATLAB's fatal-error exit. The subsequent worker
`WORKER_POWERSHELL_EXCEPTION` and PowerShell `System.IO.IOException` are
secondary broken-stream symptoms; native stderr is empty and the worker-exit
JSON is zero bytes.
No MATLAB process remained at the read-only audit and C: retained
28,585,717,760 free bytes. The valid terminal classification is therefore
`INFRASTRUCTURE_FAILED_PARTIAL_C64`, not solver non-convergence and not
scientific completion. Contract A/B, event-cycle outcome and scientific
usability remain unresolved. No retry or resume was launched.

An isolated follow-up probe later hung on the first call to the exact native
`dat_output.mexw64`; a pure-MATLAB text-only replacement passed 10,000 calls
and eight contract tests. This strongly implicates the native logger, but does
not prove the production crash line because the abort dump lacks a stack. The
approved remediation is a separately reviewed fresh v10 run with only the
text logger replaced, not a c64 resume.

## Post-failure freeze and decision (2026-10-11)

The raw output was frozen by an external manifest without changing the source
tree. Inventory: 749 files / 6,640,762,683 bytes; tree-manifest SHA256
`f43c79f252ecc8fed6c7254f58c3f80d7c72961b1c53a37f9b5fca02e01fc5ab`.
MATLAB read-only loading passed for the c63 cycle checkpoint and c64 s3 step
checkpoint, including complete solver, history, and event-detector state. The
c64 s4 temporary step checkpoint is corrupt.

The stable step checkpoint is not yet a qualified resume. The v9i Stage 0b
entry is fresh-only, rejects pre-populated checkpoints, and performs recovery
after initialization. A bounded resume-equivalence amendment was considered,
but is not the selected execution route. The c64 partial remains diagnostic
only; the next execution candidate is a fresh c0 v10 trajectory after its
storage, provenance, non-FEM and independent-review gates pass. Contract A/B
acceptance and Delta training remain unauthorised until that trajectory itself
passes the numerical acceptance contract.

Evidence:
`local_archive/experiments/S04-E016/request31_u01175_failure_freeze_20261011_v1/`.
