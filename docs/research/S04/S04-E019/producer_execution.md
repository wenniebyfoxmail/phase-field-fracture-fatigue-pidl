# E019 producer execution — 2026-10-15 BST

Execution: running; retrieval: initial preflight verified; scientific verdict: pending.

The user approved the exact Git bundle, launch script, destination and six-run execution after preflight. Only those two files were transmitted. Their remote SHA256 values match the approved local values: bundle `596046e5997eb7e83e7808c489aacd750046c14fb4f07b1873505cd8e114f013`; script `27f89ee6363e12438f5774db3461352f19e1059170c1ba188ad2b000e53fb4df`. No GitHub push or new external-review message.

## Producer receipt

- Producer: Taobo / GPUServer8 / drtao@172.16.100.2, existing Tunnelblick client VPN.
- Scientific source: ae23871366158c5e9a98fcca9fe2353675d997ec, detached clean checkout; verified Mac Git bundle from prerequisite e67d9701419fbb891ce570edd3530bf68aae5f4e.
- Root/code: `/mnt/data2/drtao/wennie/S04-E019-frozen-ae23871-20261014-v1/code`.
- Dispatcher: PID721064; launch 2026-10-14T23:42:16Z = 2026-10-15 00:42:16 BST. The directory date is the preparation date.
- Command: `nohup bash prepare_and_dispatch.sh > logs/dispatcher.log 2>&1 < /dev/null`, executed from the approved root; PID in `dispatcher.pid`.
- GPU: physical 0, CUDA_VISIBLE_DEVICES=0; before launch 21290 MiB free, utilization 0%. Existing other-user GPU processes were preserved.
- Storage, logs, refs, backbones, caches and outputs under the approved root on /mnt/data2. Per-run archives `/mnt/data2/drtao/pidl_archives/<run_id>`.
- R001 c20s4 unrestricted, R002 c20s4 localized, R003 c60s4 unrestricted, R004 c60s4 localized, R005 c83s4 unrestricted, R006 c83s4 localized; full IDs `<root_basename>-R00N-<state>-<arm>-s7`.
- At 23:43:05Z the dispatcher had passed the full real-data preflight and entered R001, child PID722056. At 23:43:52Z R001 was active (elapsed54s, expected cwd/cmdline, GPU0 utilization95%, used4174MiB); first passive training metric still pending at that snapshot.
- Local initial evidence: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E019/producer_execution_v1/`.

## Real-asset preflight

All three exact reference/checkpoint identities admitted by the reviewed runner. Actual CUDA inference versus archived predictions had maximum absolute difference **0.0** in every state; full RMS reproduced at the frozen tolerance. Anchored geometry constructed successfully.

| State | Inherited full RMS / abs(Us) | Window support mass fraction |
|---|---:|---:|
| c20s4 | .0030791216240435623 | .041237263096604075 |
| c60s4 | .003487814391244284 | .058564679405698004 |
| c83s4 | .0033046863884932513 | .071999618743685 |

The script also passed mount/free-space/GPU checks and exact clean-source admission. Initial wrong-route SSH attempts never authenticated; no prior dispatcher was started. The correct existing Taobo VPN restored access; Cambridge VPN returned to its initially disconnected state.

## Follow-through

Heartbeat e019 checks every 30 minutes, quiet on ordinary progress. Read-only monitoring only; no retry, code/budget/GPU change, or unrelated-process intervention. Retrieve the six complete outputs, logs, preflight and frozen aggregate before numerical conclusions. All arms retain alpha=.7, seed7, 10000 new residual steps, immutable E017 backbone and fixed history/fatigue. Final-step evaluation only.

Compare each state against its exact inherited backbone and matched unrestricted control: full, damage and total-background conditional RMS, plus trajectories and support-inside/outside contributions. Window-exterior preservation is an implementation check; total-background preservation includes the taper and inside-window background and must be measured independently. Primary criterion remains all three localized full RMS<=.001; the separate component finding requires damage improvement and no background regression in all three states. No new scientific result yet.
