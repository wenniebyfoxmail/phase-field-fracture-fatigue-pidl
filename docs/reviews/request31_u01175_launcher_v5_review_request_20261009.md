# Request 31 U0.1175 launcher v5 review request

> **SUPERSEDED BEFORE EXTERNAL REVIEW.** Cross-check found that the v5
> preflight writer and launcher used different review roots. No approval,
> preflight or production occurred. Review immutable v5b instead.

## Requested verdict

Review the exact immutable v5 candidate and return one:

- `PASS_REQUEST31_U01175_LAUNCHER_V5`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This is launcher review only. Do not create approval/preflight and do not run
production from the review.

## Root-cause evidence boundary

Confirmed facts:

- v4 validate-only used PowerShell's call operator
  `& $Matlab -batch $batch` and completed successfully;
- the only v4 production attempt used `Start-Process` directly on
  `matlab.exe` and returned PID `30656`;
- the immediate health check found that PID absent, MATLAB count zero,
  stdout/stderr both zero bytes, output root absent and no heartbeat;
- v5 `Start-Process PowerShell-worker -> call-operator MATLAB` harmless probe
  produced a live worker/MATLAB handshake, non-empty heartbeat/stdout/stderr,
  sentinel and zero-exit receipt, then left MATLAB=0 and output absent.

The evidence does **not** uniquely identify argument quoting, MATLAB's Windows
launcher/stub behaviour or process-lifetime semantics as the v4 sub-cause.
The allowed claim is therefore: the direct `Start-Process matlab.exe` contract
was not sufficiently observable/reliable on this host; v5 replaces that
contract with a tested worker boundary.

## Exact identity

- Windows candidate:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v5`
- candidate files: 18, excluding the manifest
- manifest SHA256:
  `2f14fd5ad90a629ae88890b88e251b2653167928e0d20d0819ce6135873453c1`
- diff-contract SHA256:
  `3fa8dd5b0dea5966e2f7f7c658f5553e5bc24152d076096a016100773c71718a`
- review root:
  `C:\q4runs\request31_u01175_launcher_review_20261009_v5`
- parent commit:
  `862992a60edc7f59335365beacb5c71fc8592a7a`
- frozen run ID:
  `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`

Canonical parent is unchanged and clean. The scientific/event implementation
and all v4 authorization gates remain unchanged.

## Minimal v5 delta

`request31_production_worker.ps1` owns MATLAB synchronously through the already
validated call operator. Before MATLAB it writes exact-identity worker-start,
heartbeat, stdout and stderr artifacts; after MATLAB it records the real exit
code and output presence.

The top-level launcher now starts only the PowerShell worker. Before reporting
`RUNNING`, it requires:

- an alive worker with exact manifest/run-ID/nonce start receipt;
- non-empty heartbeat;
- an observable MATLAB process after the zero-MATLAB preflight;
- no early worker exit or handshake timeout.

On handshake failure it terminates only the task-owned worker/child, writes a
failure receipt and never emits `RUNNING`.

## Authoritative tests

MATLAB implementation regression: **11/11 PASS**.

- receipt SHA256:
  `a3f9dbf1295fc043f7ce98d34033ed60f6aa9bb3467ece5cc2bb43b5561cde6c`
- stdout SHA256:
  `20f348640f3e3ecce3f9af7fda9197ee8c4918e8461f24e65d1af50e37ef96b0`
- empty stderr SHA256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Authorization regression: **10/10 PASS**.

- receipt SHA256:
  `aab66d0eec84ed1f2c10067dfed68aa73a23c41f2de3a75f3b7c785aa531854c`
- stdout SHA256:
  `36e322a0817163c90ef4583f269c8a7bb54895e689e6ba271847a660010fc356`
- empty stderr SHA256: same empty-file hash above.

Spawn-contract regression: **6/6 PASS**.

- receipt SHA256:
  `19b4406d62511de9a7e7b7781829e30e155a7ad49bdd90f83f2320295997fa26`
- stdout SHA256:
  `d71e1d796f25299c67b3d1c0c21123b50c275f5c492dad593f549d081edc5a5e`
- empty stderr SHA256: same empty-file hash above.

The six tests cover successful asynchronous worker/call-operator MATLAB probe,
worker-not-started, sentinel missing, MATLAB nonzero exit, handshake timeout,
and post-test environment cleanliness. Probe artifacts:

- worker-start SHA256:
  `ba34f47d9635cc69c63180ba1f5c6f51365156a74b1a33d5483856cf76ba210c`
- worker-exit SHA256:
  `71b5e47f8a75ea3b9a2bb8d9997609dd6bddca416df871267c65d9ee9e487d30`
- heartbeat SHA256:
  `fa1ffcf3f9f98ab78735912e0f807adead3aef44510c08c592ef353d197c3e44`
- stdout SHA256:
  `12d589f8ddd90a0a94012a75af6e11a20b39486f71be043379c3ab6a45a400a8`
- stderr SHA256:
  `f1b83037edcdf324bd81f9ebfde6240d34a278930c8bc64b67e224096d8333e2`
- sentinel SHA256:
  `e55e1785feb0cc52f98b2615f3ce08fcdf02180a678e64f85d66757871fd29b9`

The probe called neither `run_request31` nor the solver and created no
scientific payload. Final state: canonical dirty count 0, MATLAB=0, production
output absent, v5 approval absent and v5 preflight absent.

## Raw evidence

Complete candidate, manifest, diff, receipts, logs, probe artifacts and failure
fixtures are at:

`local_archive/experiments/S04-E016/request31_u01175_launcher_review_20261009_v5/`

## Reviewer questions

1. Does the worker preserve exact manifest/run-ID/nonce identity and synchronously
   hold the actual MATLAB invocation?
2. Is the live handshake sufficient to prevent a short-lived PID from being
   reported as `RUNNING`?
3. Are failure cleanup and receipts fail-closed and limited to task-owned
   processes?
4. Does ProbeOnly remain non-scientific and avoid the production output root?
5. Is any scientific, solver or authorization behaviour changed outside the
   minimal launcher delta?

If passing, bind the verdict to manifest
`2f14fd5ad90a629ae88890b88e251b2653167928e0d20d0819ce6135873453c1`
and the frozen run ID. A PASS does not itself authorise production.
