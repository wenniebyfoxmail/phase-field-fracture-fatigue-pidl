# S04-E011-UVH-C1-PC16-G7-CARD-r1 — exact package and single Run

2026-10-18. New GPU7 Run; old GPU3 r1/r2/r3 terminal records stay unchanged.
Verified latest direct human authorization: source chat
01a0d3dd-b956-7d63-aef4-a3724c414f59, turn
01a150d4-5c85-7890-9131-847e9ed323c6, startedAt1792357457:
“以这个对话的授权为准…补齐缺失模块、修正校验器并完成复审，通过后按原预算在GPU7启动唯一一次检验，不必再次等审批。不要重复计算或重试旧r3”.
This supersedes the earlier preparation-only limit. The user did not recite
later-generated SHAs. Review of this exact package and fresh duplicate/resource
admission must pass first. No scientific code/target change.

|Binding|Exact value|
|---|---|
|Canonical Mac development source|59eddaa8146beeb69df1dd9d603938f5dcb1512f|
|Actual producer CODE snapshot|d788477ba3bcb644665b14ca96dbf5f7107ca89b|
|Bundle ref|refs/codex/pc16-gpu7-59eddaa8146b|
|Bundle bytes/SHA256|180037 / c66b85e4fd80637f09cc06b009daa1b9b3d3bc61509458faad63e83e76a5e058|
|Local bundle|/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/gpu7_d1_20261018/package_59eddaa8/code.bundle|
|Science protocol / fresh Run|PC16-v1 / pf_s04e011_uvh_c1_pc16_g7_r1_20261018|
|GPU|physical7 RTX4090, GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81, logicalcuda:0|
|Root/cwd|/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code|
|Archive/output|/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_pc16_g7_r1_20261018|

Self-contained root commit with NO base prerequisites,44 materialized code/text
files; selected code586795bytes. Local EMPTY repository fetch/checkout, full
fsck, clean status, per-file blob/size/mode, AST and17-file reachable local import closure checks passed. No sparse/
partial/promisor/alternate object store. SOURCE_PROVENANCE.json binds every
file to development source; worker blob8b4471966fd9256e12e186622f107a1b8715a157
matches approved3dfef418 exactly. Numeric feasibility/equivalence untested.

Same science: c1s4/d/hidden/originalUV/388basis/776coordinates/elasticE0,
34HVP fixedPC16, original-z threshold1e-8 and accepted-point restore. Same
five full paths/bytes/SHA256/keys in [inputs_gpu7.json](inputs_gpu7.json); total
20911589bytes. Old head.npz ONLY transform; no baseline reevaluation, new
scientific information, representation/Delta/history change. [Protocol](protocol.md).

## Exact allowed occupancy and budget

First admission chooses empty OR the COMPLETE exact two-service set; pin mode
for all3 samples/runtime. Unknown/incomplete set or mode/identity change stops.
Both root UIDs[0,0,0,0]; exact cmdline/cgroup hashes are in inputs_gpu7.json.

|PID / start_ticks|Observed command|Baseline / ceiling MiB|
|---|---|---:|
|2742304 /534715435|python angle_main.py|494 /1518|
|2742215 /534715397|uvicorn det_main:service, port18093|446 /1470|

Only these exact services plus our own worker, no dynamic whitelist/service
request/benchmark/mutation. Current samples showed23127MiBfree/0%globalutil;
they establish capacity at those times, not empty occupancy or latency safety.
Fresh3 samples1s apart: free>=12288MiB,util<=10%,exactUUID/service identities/
ceilings; hostRAM>=16GiB,data2mounted/free>=5GiB. Runtimefree>=4096MiB,
same frozen services and own total NVML CUDA<=8192MiB/Torchreserved<=8GiB.
Sampled worker-tree RSS8GiB; all generated outputs/rootbundle/logs/cache100MiB.
Same sampled NVML two2s timeouts/interval>=1s and100ms nominal RSS/output checks.

400 shared units:68HVP+16controls+308optimization+8final, no reserve transfer.
Same900s guard envelope, no new optimization after600s/science after840s;
890s guard stop+10s cleanup and1MiB output receipt reserve. Code verification,
input IO, all factor construction/serialization/figures are inside those caps.
Any identity/deployment/input/numeric/resource failure is terminal, no retry,
seed/rank/GPU/source/budget change or old-root reuse; only own child may stop.

## Deployment and unique guard invocation

After exact-package independent review and fresh duplicate/resource admission, create fresh root only if root/output/claim absent,
transfer this sole bundle to root/source.bundle, verify exact size/SHA256.
Use only an EMPTY new Git repo; no old code clone/remote object fetch/repair:

```bash
git init /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code
git -C /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code fetch /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/source.bundle refs/codex/pc16-gpu7-59eddaa8146b
git -C /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code checkout --detach d788477ba3bcb644665b14ca96dbf5f7107ca89b
python3 -B /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code/tools/s04_e011_pc16/verify_code_package.py --code /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code --expected-source d788477ba3bcb644665b14ca96dbf5f7107ca89b
```

Only after exact materialization succeeds, invoke once, detached:

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_pc16/guard_gpu7.py --execute-approved --approval-ref S04-E011-UVH-C1-PC16-G7-CARD-r1 --expected-source d788477ba3bcb644665b14ca96dbf5f7107ca89b > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/guard.log 2>&1 < /dev/null &
```

Guard independently repeats package verification before science-file access.
Record actual full command/PIDs/source/card/human scope/time/dirty/UUID and
ledger/guard/worker/five-input receipts. SSH loss is unknown state, inspect
owned state, never blindly resend. No smoke, extra fixture or baseline job.
Retrieve/freeze/size+hash verify only owned assets; report absent evidence
honestly on failure. If generated, same-run summary/conditioning/accepted/
trace/factors/head/fields/decision.png+guides retain all previous PC16 evidence
and interpretation requirements. No second numerical rescore. MainS04 alone
writes shared Obsidian; no quota reset/purchase or old80% gate.

## Repair evidence and static boundary

The initial local package omitted the runner's mandatory field_computation.py;
its receipt is preserved as an incomplete preparation. This package includes
the unchanged canonical file. AST traversal uses a canonical local-module
catalog that includes omitted paths; it rejects missing reachable local imports
without importing them. A negative selection with field_computation.py omitted
failed explicitly. Existing promisor regex is correct; temporary Git config
remote.origin.promisor=true was detected. Empty-repo root snapshot fsck and
materialization passed. These checks do not validate external Python packages,
numerical feasibility/equivalence, service latency or scientific performance.

Old r3 checkout lacked base blobs despite a matching HEAD; exact prior object
loss history remains unproven. See deployment_gpu7.md and preserved r3 receipt.
The new bundle has no history/base prerequisites and never repairs old r3.
