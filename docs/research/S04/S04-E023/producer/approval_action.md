# E023 v1 — exact two-file transfer and single launch for approval

Prepared locally only. Sender: Mac user `wenxiaofang`. Recipient: `drtao@172.16.100.2` / `GPUServer8`, existing Tunnelblick client, SSH `-F /dev/null -o BatchMode=yes -o ConnectTimeout=15`. No SSH, transfer, producer preflight or training performed. Root absence/resource availability not yet checked; verify only after this final action is approved.

Scientific source is `c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2`, already Code Ready. Deployment script is separate and does not patch or replace the scientific runner. Two outgoing files only:

| File | Bytes | SHA256 |
|---|---:|---|
| E023_c4ceb5d.bundle | 117400 | `82a73c5a6c8aaecb06e2986b47e8f6b3dbf93f51a58f5676e910afe763f28c92` |
| prepare_and_dispatch.sh | 17889 | `dbec3c3ad125f1cd1ffe0283206902b19ac4ef40246a8986929295f02660ff63` |

Local files: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E023/producer_submission_v1`. New destination: `/mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1`. Bundle prerequisite is existing E022 scientific checkout a540888; clone that committed object store without hardlinks, fetch delta, clean-detach exact c4ceb5d. No Mac D vectors, data arrays, predictions or checkpoints are sent.

## Exact transport/start action — not executed

Stop on existing destination, failed precondition or unknown outcome. Inspect read-only before any resend or repeat launch; there is no automatic retry. Both hashes must match before launch. After launch capture PID and independently verify actual status/source/cwd; SSH loss is visibility loss, not a restart instruction.

```bash
ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'umask 077
[ "$(id -un)" = drtao ] || exit 1
[ "$(hostname)" = GPUServer8 ] || exit 1
mountpoint -q /mnt/data2 || exit 1
mkdir /mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1'

scp -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E023/producer_submission_v1/E023_c4ceb5d.bundle /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E023/producer_submission_v1/prepare_and_dispatch.sh drtao@172.16.100.2:/mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1/

ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'cd /mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1 || exit 1
[ "$(sha256sum E023_c4ceb5d.bundle | cut -d " " -f 1)" = 82a73c5a6c8aaecb06e2986b47e8f6b3dbf93f51a58f5676e910afe763f28c92 ] || exit 1
[ "$(sha256sum prepare_and_dispatch.sh | cut -d " " -f 1)" = dbec3c3ad125f1cd1ffe0283206902b19ac4ef40246a8986929295f02660ff63 ] || exit 1
mkdir -p logs || exit 1
nohup bash /mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1/prepare_and_dispatch.sh > /mnt/data2/drtao/wennie/S04-E023-head-rms-c4ceb5d-20261016-v1/logs/dispatcher.log 2>&1 < /dev/null &
printf '"'"'dispatcher_pid=%s\n'"'"' "$!"'
```

## Resources and immutable three-state design

Propose GPU0 sharing only when free VRAM **strictly >8192MiB**, before initial preparation and every row; disk at mounted /mnt/data2 **strictly >8GiB**. Log device UUID, process contexts, disk/GPU telemetry and refuse UUID drift or query failure. This is a point-in-time check, not a reservation. No process kill, GPU substitution, environment install, global changes, wait/requeue, push or different run.

Copy87existing remote files with before/after SHA and refusal of source symlinks/reused destinations:3references+15E017backbone+15E019controls from E019root,27E021controls from E021v2root,27E022controls from E022v1root. Real loaders admit pinned identity before training. Old roots are only read/copied.

Serial c20s4/c60s4/c83s4, own E017backbone and own E022direct comparison plus E021/E019common controls, localized alpha.7 seed7, each10000NEW joint hidden/head updates. Keep E022leak=.01, other layers, coordinate map, physicalwindow/BC, full-field objective, damage/history/fatigue fixed; oldcontrols not retrained. Full paired IDs/commands are production_plan.json.

## Fixed D preflight and actual LR

Before **any** row trains, allthree must pass exact formal runtime Torch2.7.0+cu126/NumPy1.24.4/CUDA12.6/RTX4090/GPUServer8/GPU0/CUBLAS:4096:8, paired native10000LR, reference/backbone/control/map/activation and CUDA cache/zero-output/BC checks. Each state's own original initializer produces284RMS/D values includingbias using CPUfloat64/two threads/1024chunks/full-mass physical BC×window/absUs. Floor1e-6, zero-columnD=1, allDfinite>0; no target residual or trained features determineD. Independent fresh initialization repeats must agree; save formal head_scale and head_gradient_preflight files/hashes perstate. No Mac calibration injection.

Immediately before each row, recompute those files from the same trusted initializer and compare exact bytes/hashes to all-state preflight. The unchanged runner computes its own D internally and validates its buffers every update; no external D argument or source hook is introduced. After each row compare the actual archived scale/gradient files to formal preflight before admitting the row or starting the next. This deliberately distinguishes deployment recomputation checks from a new in-run external-D comparison API.

Actual native CosineAnnealingLR(T_max10000,eta_min1e-5): read LR before optimizer.step; scheduler.step afterward. Firstused.001, lastused1.0000024427270673e-5, postfinal1e-5, no10001. Actual=expected=formalpreflight=ownE022/E02110000vector; no relaxed Mac-native profile. All11row artifacts and separate producer archivecopies strictly checked before nextrow; head rule/pairedE022lock/newSHA fields bound in allfour envelopes.

## Completion and stop boundary

Any source/runtime/resource/reference/map/D/gradient/LR/sampler/finite/BC/budget/archive/strict-decoder failure stops, preserves logs, no automatic retry or repair. Source and UUID checked eachrow. Original aggregator scores final10000only, three valid full UVRMS<=.001 is primary; allrowsvalid but primaryFAIL is execution completion, not scientific success. Preserve separate damage/background/inside/outside comparisons against E022/E021/E019 and inherited baseline; no statewinner stitching. Old primary verdicts/Mac strict exceptions/fullteacherNOT_QUALIFIED remain.

After completion retrieve33row files plus logs/preflights/87-filemanifest/aggregate, verify exact source/LR/D/pairing and actual archives, compare full/damage/background, then update experiment/censor/Roadmap. This approval covers only the two exact files, account, new directory, resource policy and one conditional dispatcher launch described here.
