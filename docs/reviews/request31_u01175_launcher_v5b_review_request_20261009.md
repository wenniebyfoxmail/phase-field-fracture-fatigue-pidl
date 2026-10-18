# Request 31 U0.1175 launcher v5b review request

## Requested verdict

Return one read-only verdict for the exact candidate:

- `PASS_REQUEST31_U01175_LAUNCHER_V5B`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This review cannot create approval/preflight or start production.

## Evidence boundary

Confirmed: the v4 direct `Start-Process matlab.exe` attempt did not leave a
persistent PID, logs, output or heartbeat, whereas both call-operator
validate-only and the v5b asynchronous worker/call-operator harmless MATLAB
probe are observable and complete with zero exit.

Not confirmed: existing evidence cannot uniquely distinguish argument quoting,
MATLAB launcher/stub behaviour and process-lifetime semantics as the v4
sub-cause. v5b therefore repairs the observable process contract rather than
claiming a narrower root cause.

## Candidate identity

- Windows root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v5b`
- review root:
  `C:\q4runs\request31_u01175_launcher_review_20261009_v5b`
- files: 18, excluding manifest
- manifest SHA256:
  `14e96779d0ea83bdc8a7f7e351f988740708feb7d3a5949cbf39c2c4ffb2a219`
- diff-contract SHA256:
  `c2044230c16dc41c09d05328a8c82cca0301e1f3c3a9ff5a2dc71423bdbd5c7f`
- parent commit:
  `862992a60edc7f59335365beacb5c71fc8592a7a`
- run ID:
  `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`

v5b supersedes the unreviewed v5 because v5's preflight writer defaulted to a
different review root than its launcher. v5b fixes only that path and adds an
explicit regression test proving both scripts use the same immutable v5b root.

## Launcher contract

The top-level launcher asynchronously starts a fixed PowerShell worker, never
`matlab.exe` directly. The worker writes exact manifest/run-ID/nonce start,
heartbeat and log artifacts, then synchronously owns MATLAB via
`& $Matlab -batch $batch`, capturing the real exit code.

The launcher cannot emit `RUNNING` until it observes:

- the exact worker-start receipt;
- a live task-owned worker;
- a non-empty heartbeat;
- an actual MATLAB process after a zero-MATLAB preflight.

Early exit or timeout is fail-closed, terminates only the task-owned worker and
child, and writes a failure receipt.

## Tests

- MATLAB implementation regression: **11/11 PASS**
  - receipt `db353e53661cd7a08c87f2ceac0ad2429bf52c0c6782e7360d7c5ed5b22535d5`
  - stdout `2f7486387fe453b9693f5643fc2cf33f6ae8a9bf35b1a7f8e3e3e0ce8ddacc92`
- authorization regression: **10/10 PASS**
  - receipt `16ce7fc38e69a248c8a9c9680d3f75fc3496061fc4a6a87b786074e191c44f30`
  - stdout `8d7d6cb0710bc7e45a5436e12e6060382de4643d0b1be745015c0b76d2d716c5`
- spawn-contract regression: **7/7 PASS**
  - receipt `851a57d7822d7f6482ed4a82d16595ecbdc7ea0065470f66bd400063c35a6fc4`
  - stdout `38789aea42d4c633bcf9c05c60304998361a9622ce258bb89243cab04bc25244`
- all three stderr logs are empty, SHA256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Spawn tests cover successful harmless worker/MATLAB handshake; worker missing;
sentinel missing; MATLAB nonzero exit; handshake timeout; clean post-test
environment; and preflight-writer/launcher review-root equality.

The probe called neither Request31 nor the solver and generated no scientific
payload. Final state: parent clean, MATLAB=0, output absent, approval absent,
preflight absent.

## Raw evidence

`local_archive/experiments/S04-E016/request31_u01175_launcher_review_20261009_v5b/`

Review the raw manifest, diff, candidate source, receipts, logs, worker-start,
heartbeat, worker-exit and sentinel. If passing, bind the verdict to manifest
`14e96779d0ea83bdc8a7f7e351f988740708feb7d3a5949cbf39c2c4ffb2a219`
and the frozen run ID. A PASS still does not itself authorise production.
