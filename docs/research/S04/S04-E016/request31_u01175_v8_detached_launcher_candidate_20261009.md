# Request 31 U0.1175 v8 detached-launcher candidate

Date: 2026-10-09  
Producer: `CITPC12`  
Status: `READY_FOR_CHATGPT_DETACHED_LAUNCHER_REREVIEW`  
Claim class: C0 launcher capability only  
Scientific result: none

## Diagnosis

The v7 production attempt obtained the reviewed exact R2025b engine handshake,
then the SSH-descendant worker, MATLAB launcher and engine all disappeared when
the initiating command returned. There was no terminal receipt, no MATLAB log
content and no production output.

A controlled no-solve infrastructure probe created a PowerShell worker through
local `Win32_Process.Create`. The creator SSH connection ended; the Session-0
worker remained alive under `WmiPrvSE.exe`, completed its heartbeat window and
wrote a terminal receipt. This supports the OpenSSH process-lifetime hypothesis
for the v7 failure. It does not prove that a long FEM solve will succeed.

## Immutable v8

- derived root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v8`;
- review root:
  `C:\q4runs\request31_u01175_launcher_review_20261009_v8`;
- manifest SHA256:
  `e80c4b835d68ccff941c5eccc95ab5f8a3aea5a40ab2462b8ac7cb3d81bfa74a`;
- diff-contract SHA256:
  `74510f0e9b7fa1a46a33f23881f51e12af94329194711b3e98de460e2a646455`;
- canonical parent commit:
  `862992a60edc7f59335365beacb5c71fc8592a7a`, dirty count `0`.

v8 adds only detached-launcher control and evidence:

1. `ProductionStart` creates a Session-0 worker through
   `Win32_Process.Create` and returns only
   `DETACHED_WORKER_STARTED_AWAITING_CROSS_SESSION_CONFIRMATION`.
2. The worker waits without starting production MATLAB.
3. A separate `ProductionConfirm` validates the creator receipt, writes a
   run/manifest/nonce/PID-bound release, observes the owned exact engine and
   only then may report `RUNNING`.
4. Invalid WMI return, worker identity/session, missing release/terminal
   receipt or wrong engine identity fails closed.

Physics, mesh, state0, MEX, tolerances, update order, event policy and Contract
A/B remain unchanged.

## No-solve results

- MATLAB implementation: 11/11 PASS;
- authorization: 10/10 PASS;
- inherited spawn contract: 13/13 PASS;
- detachment unit tests: 8/8 PASS;
- cross-SSH-session detached MATLAB probe: PASS.

Connection A ended after creating worker PID `26892`, whose parent was
`WmiPrvSE.exe` PID `6952` and session was `0`. Connection B observed:

`worker 26892 -> MATLAB launcher 36376 -> exact engine 34688`

Exact engine path:
`C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe`.

The MATLAB command was a 20-second `pause` probe only. It declared
`run_request31_called=false`, `solver_called=false` and
`scientific_payload_created=false`, then produced a zero terminal exit.

Evidence hashes:

- heartbeat: `d31c4408488093fef7091db81be91c6e39641b8b34c827a32d9fa6f82dadf46b`;
- stdout: `333baeecc36c0dd55b8b76199c86f35ade65cbf2412067b73c471e10d8059651`;
- stderr: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- exit receipt: `45a82717c309346f37562302513d4e4ff5d9d46e9ed5339457c7ad0828753365`.

Final live state: MATLAB=0, output absent, approval absent, production preflight
absent. Production was not started.

Mac evidence:
`local_archive/experiments/S04-E016/request31_u01175_detached_launcher_review_20261009_v8/`.

## Gate

Next step is independent v8 review only. A future production attempt would
still require an explicit review PASS, new approval/nonce, fresh full preflight
and separate human authorization. This candidate does not authorise a retry.

