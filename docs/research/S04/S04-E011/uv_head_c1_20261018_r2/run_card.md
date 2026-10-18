# S04-E011-UVH-C1-CARD-r2 — GPU3 shared-service approval candidate

2026-10-18 Europe/London. **PREPARED, NOT APPROVED, NOT RUN.** R1 approval was
used only through the resource precheck stop; it does not authorize this r2.

|Binding|Exact value|
|---|---|
|Owner|验证位移–damage 耦合机制 /01a14e3b-f1ff-7360-a084-c1f13b261cc6|
|Source|`9a0bf3c7f503f1e1b27dba480d2168348459a30a`|
|Protocol / new Run|S04-E011-UVH-C1-r2 /pf_s04e011_uvh_c1_r2_20261018|
|Producer|Taobo drtao@172.16.100.2, GPUServer8, /usr/bin/python3|
|Physical GPU|3 ONLY, UUID GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb; CUDA_VISIBLE_DEVICES uses this full UUID and worker uses logical cuda:0, independent of CUDA ordinal ordering|
|Fresh root / cwd|/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r2_20261018/code|
|Output/archive|/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018|
|Log / one-shot claim|/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r2_20261018/guard.log and attempt_claim.json|

## Scope preserved

Same single c1s4 fixed-FEM-damage UV-head elastic-energy question as r1. Four
scientific/control files, their full producer paths, sizes, hashes and selected
fields are frozen in [inputs.json](inputs.json), total21,049,958bytes:
c1_peak.npz(15,183,163), model4 PT(4,510,165), saved PBD U fields NPZ(1,355,797),
saved PBD U result JSON(833). Runtime hashes whole files once and decodes only
listed fields. No array read/hash, CUDA runtime or fitting in this preparation.
The added service profile is source-controlled OS resource metadata, not a new
scientific input. No new FEM/trajectory, c20, U0.1175/U0.125, confirmation,
E025 nine-source read, B32/C33 rerun or L32/E026. worker.py is unchanged from
reviewed source52a391fb, including actual-network realization and the1e-4
directional screen with separately retained smaller resolved gains.

## Resource changes requiring this new approval

- Select physical GPU3 explicitly; no automatic GPU0/7 fallback.
- Allow ONLY the identified resident PID3295884 (root, start_ticks213283304,
  exact cmdline/cgroup hashes in inputs.json), a long-running Docker uvicorn
  api:app service on port39070. PID alone is insufficient. Restart/change,
  unreadable identity or any other GPU process stops without re-whitelisting.
- Three admission samples1second apart: exact UUID/service set, free>=12288MiB,
  whole-GPU utilization<=10%, service VRAM<=11636MiB. Host>=16GiB available;
  canonical data2>=5GiB free. No service request or benchmark.
- REDUCE own Torch reserved memory12→8GiB. Additional sampled NVML TOTAL own
  CUDA-process cap8GiB includes context/libraries, so effective allocator space
  may be lower. Runtime GPU snapshots require free>=4096MiB, same resident
  identity and memory allowance, and only resident+our worker. Monitor failure,
  unknown PID, extra service demand or own process>8192MiB stops OUR child only.
-900s total remains; guard triggers at890s with10s reserve. Two NVML commands
  each have2s timeout; next snapshot starts>=1s after the previous completes.
  RSS/output nominal100ms polling can be delayed by these queries; these are
  sampled caps, not OS hard-peak or zero-interference guarantees.

Other caps unchanged:400TOTAL elastic objective evaluations including references,
FD/trials/callback/final reads; no new optimizer evaluation after600s, no new
worker scientific evaluation after840s; sampled host worker-tree RSS8GiB;
generated output100MiB including caches/logs/receipts.1MiB is reserved for final
guard receipt. Max one GPU and0.25GPU-hours. No numeric evidence yet establishes
that the head solve fits8GiB; OOM/limit stops rather than restoring12GiB.

Current GPU3 was observed with13460MiB free,0% whole-GPU activity at two endpoints,
stable10612MiB service memory over11seconds. GPU7 had12959MiB free and three
residents; GPU0 had more free memory but one unresolved app.py role. This is
short-duration capacity evidence, not a guarantee against service traffic,
latency effects or future memory growth. Per-process pmon '-' was unavailable,
not measured0%. [Resource assessment](resource_amendment.md) records full limits.
Do not stop, restart, reprioritize or otherwise mutate existing services.

## Prospective exact action after human approval

Refresh normal Codex quota (known remaining>=80%), current threads and producer
duplicate/resource checks. Prepare a fresh clean Git checkout at exact source
above, without touching any other checkout or public push. Local delta bundle
requires basebf0f21b5; if acquiring a fresh base checkout is needed, use the
GitHub source-of-truth branch codex/hard5-q4-t3-2x2-20261005 and verify exact base,
then import the prepared local code bundle. Do not treat the previously inspected
producer checkout as a verified base. Do not regenerate/copy missing scientific
inputs. A checkout/transfer failure stops; no retry or alternate source.

Invoke once, detached, capturing all process/source/GPU/time/command receipts:

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r2_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_uv_head/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-CARD-r2 --expected-source 9a0bf3c7f503f1e1b27dba480d2168348459a30a > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r2_20261018/guard.log 2>&1 < /dev/null &
```

Approval-ref string cannot substitute for human approval. Any approved guard
invocation atomically consumes its claim before source/resource preflight. First
identity/admission/IO/nonfinite/OOM/monitor/limit failure stops; no retry/resume,
cap increase, extra rank/seed/state/optimizer, GPU switch or service mutation.
Lost SSH response is unknown state, never permission to repeat a command.

Minimum return stays: actual head/conditioning/candidate fields, energy/force/
H1/L2/full+retained gradients/uncertainty, counted trace and terminal receipts,
same-run full-field/difference/energy/residual figure+guides. Retrieve only new
owned outputs/logs/claims and verify transfer; view same-run report/figure, no
independent scientific-array recomputation. No Obsidian/Roadmap or other-owner
document/message edits. Numeric and physical conclusions remain separate.

## New approval wording

“批准按S04-E011-UVH-C1-CARD-r2、源码9a0bf3c7f503f1e1b27dba480d2168348459a30a，
在Taobo物理GPU3与卡内唯一指定常驻服务共用，执行唯一一次新Run，含卡内SSH检查、源码部署、四文件读取、
单次求解及报告取回；遵守400次／900秒／8GiB RSS／8GiB CUDA／100MiB及4GiB余量监测，
失败或触限不重试，不改动其他进程。”
