# E020 producer execution — 2026-10-15

Execution succeeded; retrieval verified31files/45027883bytes. Producer primary FAIL; strict Mac full replay INADMISSIBLE due reference-rho portability. Independent Evidence review pending.

User explicitly approved the exact two-file package and launch after preflight. Remote SHA256 matched: bundle `43ca4c5c2e5d9eaa7799c6f233b23a169c6ff11862b179b462d3b3313bc43daa`; launcher `087305d69457aa542dfd8e2ca51d7fc6b6bdcbbe3623f036642025ebbd31dd68`. No approved bytes changed.

- Producer: drtao@172.16.100.2, GPUServer8, existing Taobo Tunnelblick client.
- Root: `/mnt/data2/drtao/wennie/S04-E020-delay-671fba2-20261015-v1`.
- Exact source: `671fba2e48f1202bc2dd89f9800bacf1849477a0`; clean detached checkout required by launcher, checked before asset preflight.
- Dispatcher PID1738351, launched `2026-10-15T14:56:00Z` (15:56 BST). Command: `nohup bash prepare_and_dispatch.sh > logs/dispatcher.log 2>&1 < /dev/null`, from root. No earlier run existed at that root.
- GPU0 with CUDA_VISIBLE_DEVICES=0; mount, free-space and free-memory checks passed before source checkout. All task caches, logs and outputs on /mnt/data2.
- Three sequential rows R001 c20s4, R002 c60s4, R003 c83s4; full IDs `<root_basename>-R00N-<state>-localized-s7`.
- Per-row archive `/mnt/data2/drtao/pidl_archives/<run_id>`; logs `<root>/logs/<run_id>.log`; outputs `<root>/runs/<run_id>`.
- alpha=.7, seed7, fresh residual and optimizer, frozen backbone/history/fatigue, 10000 actual updates. LR .001 for updates1–8000 then frozen cosine tail to .00001 at10000. Historical E019 localized controls admitted without retraining.
- Local case: `local_archive/experiments/S04-E020/producer_execution_v1/`; approved package and full command in sibling producer_submission_v1/approval_request.md.

Heartbeat e020 checks every30minutes; ordinary progress silent. Read-only monitoring, no retry/restart, code/budget/GPU change or unrelated-process interference. SSH loss means visibility loss only. After completion retrieve logs, preflight, output, LR vector, checkpoints, receipts and original aggregate; verify integrity and sampling identity, compare full/damage/background against each inherited backbone and E019 localized historical control. Primary all3 final full normalized RMS<=.001; component improvement and background preservation reported separately. Preserve reference-rho portability exception; do not relax strict checks. Execution health is not scientific success. Stop monitor once follow-through completes.

## Initial verification

All three references, inherited backbones and pinned historical E019 localized controls admitted. Exact runtime torch2.7.0+cu126, numpy1.24.4, CUDA12.6, RTX4090/GPUServer8, visibledevice0 and CuBLAS:4096:8 matched. CUDA cached-prediction maximum absolute difference0.0 for c20s4/c60s4/c83s4. Local baseline_preflight.json retrieved and inspected.

R001 began14:57:07Z; at14:58:11Z PID1740102 elapsed63s, expected command and cwd `<root>/code`, GPU0 4174MiB used/93% utilization. Passive first-step metric still pending at this snapshot; no final inference yet. Launch/preflight receipt in local case.

At14:58:50Z the first passive record confirms update1000: actual LRused=.001, next=.001, fullRMS=.003078667469517176, damageRMS=.024231297816820135, backgroundRMS=.0002401909574988718, outside-support delta=0.0. This is execution/protocol evidence, not final performance.

## Partial retrieval 2026-10-15T15:10:50Z

c20 finished15:08:49.647570Z; c60 started15:08:50Z and latest passive update1000 observed; c83 queued. Dispatcher1738351 active. c20 sixfiles14975058bytes retrieved, every remoteSHA256 matches. Frozen validate_schedule_and_pair passes; receipt source/clean status matches and10000actualLRs .001→.00001 verified. Local c20_retrieval_verification.json preserves details. These are partial asset/protocol checks, not full numerical admission or three-state scoring. No E019/candidate final comparison until all3rows complete. Heartbeat e020 remains active; no retry/new run.

## Completion and follow-through

All3candidates reached10000updates; last finished2026-10-15T15:32:15.828265Z. Frozen aggregator completed15:34:07Z,3/3valid,no missing/integrity errors, primaryDELAYED_DECAY_THREE_STATE_UV_SCREEN_FAIL, inherited componentFalse. Remote clean scientific671fba2 verified. Local31files45027883bytes all match remote final SHA256;3actual10000LRvectors and source/runtime/pairedinitial/backbone/geometry/sampler identities verified. Three checkpoints/predictions/receipts,11pointtraces, logs/preflight and originalaggregate present. Existing E019refs/backbones/controls reused by exactlockedidentities.

Independent saved-array full/damage/background candidate metrics agree with producer within1.48e-17(max), historicalcontrol metrics within1e-14. c20full improves.5934%vsE019, c60worsens406.4682%, c83worsens1.6824%; background c20/c83improves but c60worsens1.5024%. Strict Macfullreplay0/3INADMISSIBLE retained; onlybaseline reference_rho mismatch (~9.4e-14–1.79e-13). No tolerance/codepatch used. Decision and exacttables in decision.md; final decisionfigures analysis_render_v2/README_analysis.md in localcase, all3renderedfigures visually checked.

Monitor e020PAUSED after retrieval/analysis. Next low-cost activation/gradient/feature-spectrum diagnostic proposed in next_diagnostic.md. No new experiment, externalreviewsend, GitHubpush or producer intervention. Independent Evidence review remains pending; execution/retrieval completion is not fullscientific qualification.
