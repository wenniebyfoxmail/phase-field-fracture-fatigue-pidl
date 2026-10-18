# Request 31 U0.1175 v8 detached-launcher review request

Review status requested: `PASS_REQUEST31_U01175_DETACHED_LAUNCHER_V8` or
`MODIFY_AND_REREVIEW`.

This is a C0 launcher-capability review only. Production was not started and no
scientific payload exists.

Review the immutable package:

- manifest SHA256:
  `e80c4b835d68ccff941c5eccc95ab5f8a3aea5a40ab2462b8ac7cb3d81bfa74a`;
- diff-contract SHA256:
  `74510f0e9b7fa1a46a33f23881f51e12af94329194711b3e98de460e2a646455`;
- Mac evidence:
  `local_archive/experiments/S04-E016/request31_u01175_detached_launcher_review_20261009_v8/`;
- full execution note:
  `docs/research/S04/S04-E016/request31_u01175_v8_detached_launcher_candidate_20261009.md`.

Please determine whether:

1. `ProductionStart` cannot self-report `RUNNING`;
2. the WMI/Session-0 worker identity is sufficiently bound;
3. production MATLAB remains blocked until a separate confirmation invocation;
4. failure cleanup is restricted to the task-owned process tree;
5. the 11/11, 10/10, 13/13, 8/8 and cross-SSH-session evidence is sufficient
   for a future fresh approval/preflight gate.

Do not create approval/preflight or run production during review.
