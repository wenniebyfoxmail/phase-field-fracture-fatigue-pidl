---
experiment_id: S09-E017
run_id: S09-E017-R001-factorised-head-p0
status: PRE_ADMISSION_REPAIR_STOPPED
date: 2026-10-20
---

# S09-E017 deployment-repair stop

The user authorised a read-only inspection of the prior deployment residuals,
repair of task-owned staging, and then one unchanged admission and three-arm run.
The inspection found no runner, `pf_` session, admission token, authority,
resolved config, output root or archive root. The remote `code/` checkout was a
clean, connected repository at ancestor `010281be8045301f7e56b938de82969982c89bc9`.

The preserved thin bundle was repaired once over the existing SSH master. Its
remote size became 3,479,816 bytes and SHA256 became
`1dd7bee7fc5c7b434a3eb5487e412f4b561152196673e4722d38b530f5a5ea5d`.
`git bundle verify` passed, and the task checkout advanced cleanly to the
reviewed control commit `2002538d9a30c8d4006ccaff5959cd214958fc82`.

Creating the code archive on `GPUServer8` produced the correct embedded commit
but not the frozen bytes: 14,390,948 bytes and SHA256
`65fca6a92bb32f60337368bdcfeffa9417efe9817052af568b5552b5b43abc1c`.
The same frozen command on the reviewed Mac checkout reproduced the required
14,359,316-byte archive and SHA256
`4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`.
This compression-version difference was not treated as equivalent because the
execution authority binds the exact archive hash.

One transfer of the exact frozen archive was allowed to run for the stated
30-minute hard limit. It reached about 93% but did not complete, and was stopped
with local `rsync` exit 20. The two exact task-owned remote `rsync` server
processes were checked by PID, parent, elapsed time and command before TERM.
The 12,572,127-byte remainder was preserved as
`control/code.tar.gz.partial_frozen_transfer_stopped_20261020` with SHA256
`b3d53aad9797a4c19ee30f18c1f0ca6b721dabae3a82fd9b58463579132bd9e0`;
the live expected `control/code.tar.gz` path is absent.

The newly generated authority passed local schema validation but was never
written remotely and is closed by this staging stop. No resolver, admission or
runner was invoked. There was no scientific asset load by the runner, model
forward, autograd collection, optimiser construction or optimiser step. GPU5
remained at 4 MiB and 0% utilisation with no compute process. The run and
archive roots remained absent.

This is a deployment-transport stop, not a PINO scientific result. The exact
mapping, physics, three arms, `beta=0.25`, 64 updates per arm, data exposure and
holdout boundary were not changed. Any later transfer, admission or execution
requires a new explicit authority and must begin from this preserved state;
there is no automatic resume or launch.

- Machine receipt:
  `final_execution_repair_stop_receipt_20261020.json`
- Prior network-stop receipt remains unchanged:
  `final_execution_dispatch_stop_receipt_20261020.json`
