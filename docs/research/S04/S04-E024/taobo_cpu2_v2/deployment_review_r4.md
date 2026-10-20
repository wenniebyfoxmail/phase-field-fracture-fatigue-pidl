# D013 v2 deployment review r4

Verdict: **PASS**, deployment code only. Scientific execution and remote transport remain unauthorized. Prior r2/r3 receipts remain preserved.

## D3 resolved

owned_group_snapshot first filters the fresh Popen session+PGID, then checks each surviving member cmdline, unique expected cwd, creation time>=bound leader and nonnegative elapsed, immediately re-reading identity. terminate_owned checks survivors and signals the owned group after leader exit, with a second full attribution check before escalation. supervise_child rejects unexpected live workers after a zero parent exit and invokes cleanup for both zero/nonzero exit paths. Failure cleanup no longer depends on leader liveness. Artificial parent-exit0/3 worker-live cases passed.

The exact bounded df -h / /mnt/data2 /mnt/data3 record, mandatory data2 admission, default/false authority closure, first-SSH anchor before metadata, original cumulative budgets, pre-SCP single1GiB capacity admission and unchanged source checks remain present. Shared username alone is never kill authority.

## Verification and limits

Independent rerun:39 pure fixtures passed in 0.729623625s, including parent-exit0 and parent-exit3 with live orphan workers. V2 check-wrapper cumulative wall is4.430669544s. Failed prior fixture output remains preserved. No Torch import, real model/data deserialization, scientific solve, training, SSH/SCP, probe, install or science-source edit occurred. Only local synthetic test processes were created/terminated.

This receipt is bound to the code hashes in deployment_review_r4.json. Regenerated final wire/control/action manifests and current producer compatibility are excluded. Recheck final assembled bytes, storage and all preparation costs before presenting the exact final version for human approval.
