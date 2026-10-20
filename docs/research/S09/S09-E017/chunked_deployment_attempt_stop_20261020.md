---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
deployment_attempt_id: s09e017-chunkdeploy-20261020T152432
terminal_state: DEPLOYMENT_GUARD_STOPPED
scientific_execution: false
date: 2026-10-20
---

# Content-addressed deployment attempt stop

## Purpose and authority

The user instruction “请重新投放” authorised one execution of the reviewed
content-addressed deployment candidate. The authority bound candidate
`90d0caab...3be25` and plan `0f5179cb...093a`, allowed one connection, one
metadata transfer, at most one missing-chunk transfer, 14,500,000 source bytes
and 1,800 seconds, with no retry or reconnect. It explicitly kept
`execution_authorized=false`.

## Process and observed result

The guard consumed the authority before starting the plan. Within the sole
connection, the plan verified `GPUServer8`, clean checkout
`2002538d9a30c8d4006ccaff5959cd214958fc82` and absence of blocked execution,
authority, admission, output and final-archive paths at precheck.

The recorded 12,572,127-byte legacy partial matched SHA256
`b3d53aad...d9e0`. Chunks 0–22 were reverified and imported atomically:
12,058,624 reusable bytes. The pre-transfer store had no corrupt chunks and
was missing chunks 23–27, totalling 2,300,692 bytes.

The sole missing-chunk `rsync` then returned `unexpected end of file`. The
outer guard stopped after 156.632 seconds with process return code 255 and
`DEPLOYMENT_PLAN_EXIT_NONZERO`. It did not run the post-transfer inspection or
archive assembly. No resolver, admission, runner or training operation was
reachable from this deployment-only plan.

## Bounded conclusion and next decision

This attempt confirms that content addressing recovered 23 exact chunks, but
it does not establish the post-failure state of the remote chunk store. Some
additional complete chunk may or may not have survived the failed rsync; no
reconnect was made to inspect it. There is no deployment-success receipt and no
scientific result.

The authority is consumed and closed. A later attempt would require a new
explicit deployment-only authority. Its first in-plan inspection can safely
rehash the persistent chunk store and transfer only whatever remains; it must
not assume the failed transfer completed, and it still must not enter resolver,
admission or training automatically.
