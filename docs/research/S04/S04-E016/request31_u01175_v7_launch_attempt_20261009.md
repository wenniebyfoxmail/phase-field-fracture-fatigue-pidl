# Request 31 U0.1175 v7 production retry

Date: 2026-10-09  
Producer: `CITPC12`  
Status: `START_FAILED_NOT_RUNNING`  
Scientific result: none

## Review, approval and fresh preflight

Independent v7 review returned `PASS_REQUEST31_U01175_LAUNCHER_V7`, bound to:

- manifest SHA256:
  `8a30ce48dfa4be30ba196a8d54a7177f74d0b79206fe292539eecce9f684f742`;
- run ID: `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`.

A new approval was created at `2026-10-09T02:12:31.9868447Z` with launch nonce
`c6df6489-6e0c-4e66-8829-5a283a3a8967`; SHA256
`16578be7b6b673fa7757d62d39ef1005d7addbee6dfe10065d99ab9be4e15138`.

Fresh full producer preflight completed at
`2026-10-09T02:12:51.7193017Z` with `PASS_READY_TO_LAUNCH`. It rechecked:

- canonical commit `862992a60edc7f59335365beacb5c71fc8592a7a`, clean status and parent manifest;
- every v7 manifest entry and exact production-path evaluator;
- canonical state0, both native MEX binaries, qualification-v5 and exact U0.1175 five-step load values;
- Contract A cycle summaries and Contract B same-state post-history-commit capture;
- v7 worker/exact-engine handshake prerequisite;
- MATLAB count zero, target output absent and C: storage above the frozen gate.

The preflight used the same manifest, run ID and nonce. Receipt SHA256 before
consumption:
`9ad7eec7af3a00e2bca7cd7f0be3097996ff9c23c038d89d1353c9f5cb39131f`.

## Exactly one authorised retry

The v7 launcher was invoked once. It returned a transient `RUNNING` receipt:

- worker PID: `48640`;
- MATLAB launcher PID: `44872`;
- MATLAB engine PID: `49688`;
- engine parent PID: `44872`;
- engine creation time: `2026-10-09T02:13:10.3552820+00:00`;
- exact engine path:
  `C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe`;
- launch nonce: `c6df6489-6e0c-4e66-8829-5a283a3a8967`;
- launch receipt SHA256:
  `175c5ae99dc7b6739c1ceeb16f79c1b7fa502617273c7f5faff59c8aeec89b04`.

The identity handshake therefore worked as reviewed. This was only a launch
handshake, not completion evidence.

## Non-destructive health check

The post-launch health check found:

- worker, launcher and engine PIDs all absent;
- global MATLAB process count zero;
- heartbeat stopped after:
  - `worker_start`;
  - `matlab_call_operator_begin`;
- no `production_worker_exit.json` terminal receipt;
- no handshake-failure receipt;
- production stdout bytes = 0;
- production stderr bytes = 0;
- U0.1175 output root absent.

Therefore the transient launcher response is superseded by authoritative status
`START_FAILED_NOT_RUNNING`. Failure receipt SHA256:
`35063c720099dd1b0906bcd5b695918a677349a876ad8d4ed5311af25fbe863e`.

The evidence proves that exact engine identity alone is insufficient for a
durable production launch. It does not yet isolate the narrower cause of the
abrupt process-tree exit, so this is an execution failure rather than a
scientific negative.

## Fail-closed closure

No second retry was attempted or authorised. The fresh preflight was moved to
`production_preflight_consumed_start_failed_v7.json`, preserving SHA256
`9ad7eec7af3a00e2bca7cd7f0be3097996ff9c23c038d89d1353c9f5cb39131f`;
the required `production_preflight_pass.json` is absent. MATLAB=0 and the
production output root remains absent.

Complete compact evidence is retained at:

`local_archive/experiments/S04-E016/request31_u01175_launcher_review_20261009_v7/`

An accidentally oversized health serialization is quarantined on Windows as
`launch_health_running.invalid_oversized.json` and is not scientific evidence.
