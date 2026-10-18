# Request 31 U0.1175 v4 launch attempt

Date: 2026-10-09  
Producer: `CITPC12`  
Status: `START_FAILED_NOT_RUNNING`  
Scientific result: none

## Authorisation and preflight

Independent v4 review returned `PASS_REQUEST31_U01175_IMPLEMENTATION`, bound to:

- manifest SHA256:
  `72fbb67d9e052c5b1ee451c80e3ad82224e4a1e31386510e7f588048e55e49ce`;
- run ID: `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`.

Approval was created at `2026-10-09T01:07:50.0540212Z` with launch nonce
`cea18cd5-f30b-4b82-a74b-466efdb9f9ff`; SHA256
`adaad9ba0520d9d80b9ddb6e70a55378dad88c64ea509decc7ff37abc9b0d315`.

Fresh full producer preflight completed at
`2026-10-09T01:08:27.9641925Z` with `PASS_READY_TO_LAUNCH`. It used the same
manifest, run ID and nonce and found no blockers. It rechecked canonical parent
clean/hash, v4 manifest contents, exact production-path `which`, MATLAB R2025b,
state0, both MEX binaries, qualification v5, U0.1175 load path, Contract A/B,
zero MATLAB, absent output root and C: storage. Receipt SHA256:
`eefd0edd41041547bfa7f372819d1f7135c93b4d78ce05a219082d0362039119`.

## Launch attempt

The reviewed v4 launcher was invoked once with `-Production`. It returned:

- recorded state: `RUNNING`;
- PID: `30656`;
- start: `2026-10-09T01:09:03.9824443Z`;
- stdout:
  `C:\q4runs\request31_u01175_implementation_review_20261009_v4\production.stdout.log`;
- stderr:
  `C:\q4runs\request31_u01175_implementation_review_20261009_v4\production.stderr.log`;
- output root:
  `C:\q4runs\request31_u01175_confirmation_20261008_v1`;
- launch receipt SHA256:
  `08ea0ec21f27f44615b5ccd8f2bf2b948673408ad52139a32cdf2b65df2f6c28`.

## Immediate health check

The first non-destructive health check failed:

- recorded PID `30656` was absent;
- MATLAB process count was zero;
- production output root was absent;
- stdout bytes = 0;
- stderr bytes = 0;
- no first output or heartbeat existed;
- no immediate Windows Application error was found.

Therefore the recorded `RUNNING` state was not accepted. Authoritative status is
`START_FAILED_NOT_RUNNING`. Health receipt SHA256:
`862479359a527859f06950b5b03a20a0e95293ff7e0391c3851b0b07d68fff1a`.

The exact cause is not yet established. The evidence is consistent with a
launcher argument/process-lifetime contract failure, but this is a diagnostic
hypothesis, not a confirmed cause.

## Fail-closed action

No second launch was attempted. The pass receipt was moved to
`production_preflight_consumed_start_failed.json`, leaving the launcher's
required `production_preflight_pass.json` absent. This prevents reuse of the
consumed approval/preflight pair. A retry requires a reviewed launcher repair,
a new approval/nonce and a new full preflight.

Complete raw evidence is retained at:

`local_archive/experiments/S04-E016/request31_u01175_implementation_review_20261009_v4/`
