# UVH c1s4 r2 — prospective shared-GPU resource revision

2026-10-18 Europe/London. User authorized read-only resource inspection and a
revised card/static review, explicitly **no retry yet**. R1's precheck stop and
approval remain exhausted and unchanged. This is a new prospective Run
pf_s04e011_uvh_c1_r2_20261018 under S04-E011, not an R1 resume.

Scientific question, four input identities/selected fields, one fixed-d c1s4
energy-head method, numerical checks and interpretation are inherited unchanged
from ../uv_head_c1_20261018/protocol.md. worker.py is identical to source52a391fb.
Only guard, resource contract, static checker and this new card change. Inputs
retain their original immutable producer paths; no new scientific source.
No arrays, scientific hashes, CUDA runtime or optimizer were accessed in this
revision. The OS/NVML/container metadata inspections are not scientific field
analysis. No source deployment, public push, other process mutation or service
request was made. No Obsidian/other-owner edits or other-chat messages.

## Current observed alternatives, not reserved devices

Taobo physical indices (`drtao@172.16.100.2`, GPUServer8),2026-10-18
09:55:40–09:55:51UTC /10:55:40–10:55:51 Europe/London:

|physical GPU|free MiB|resident GPU memory / processes|observed GPU utilization|
|---|---:|---|---|
|0|21290|434+616+1722MiB, three Docker processes|0% at both endpoint samples|
|3|13460|10612MiB, one Docker uvicorn api:app service|0% at both endpoint samples|
|7|12959|532+2272+8298MiB, three processes|0% at both endpoint samples|

GPU0: PID1344818 det_main:service uvicorn, PID1868449
model_inference_service.main:app uvicorn; PID3920809 is a long-running Docker
python app.py, whose business purpose was not established. GPU7: angle_main.py,
det_main:service and app:app HTTP service. GPU3's single PID3295884 has been
running since2026-09-11; exact command is /usr/bin/python /usr/local/bin/uvicorn
api:app --host0.0.0.0 --port39070. Its business function/response latency is not
measured. Cgroups establish container membership. Read-only docker ps failed
socket permission; no sudo, daemon permission change or container action used.
No inference request or benchmark was sent to these services.

Three pmon observations reported '-' for per-process SM/memory utilization,
which means unavailable, NOT zero. Two whole-GPU0% readings and stable memory
over11seconds are short observations, not proof of no live traffic or no future
VRAM/latency interference. No service restart/exclusive-GPU reservation is implied.

Decision: propose physical GPU3 only, with reduced own memory and explicit
resident identity checks. At the old12GiB job cap, GPU3/7 do not preserve4GiB
headroom; do not switch them under the old r1 card. New8GiB cap plus4GiB minimum
requires12GiB initial free. Current GPU3 free13460MiB leaves5268MiB after a full
8GiB own process. GPU7 has less headroom and more residents, so is not selected.
GPU0 has most memory, but the app.py role is unresolved; no generic GPU0 service
whitelist is invented. New GPU3 selection is explicit, never an automatic fallback.

## r2 exact admission and owned-job stop

Physical GPU3 must map to UUID GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb.
Exactly one resident process is allowed: PID3295884, root UID tuple,
start_ticks213283304, exact cmdline/cgroup hashes from the read-only09:58:07UTC
profile. Current PID alone is insufficient; start time/UID/command/cgroup must
match. A restart, new process or unreadable identity stops. No re-whitelist.

Admission: three samples one second apart, each UUID/known-service-only,
free>=12288MiB, aggregate GPU utilization<=10%, service memory<=11636MiB
(observed10612+1024MiB allowance). Host>=16GiB available and data2>=5GiB remain.
No CUDA context or scientific file is opened by this preflight.

Runtime: only that resident plus this own single worker PID may hold CUDA
memory. Every completed GPU snapshot schedules the next no sooner than1second;
each of two nvidia-smi commands has2second timeout. The sampled checks stop our
child on unknown PID, identity change, service VRAM>11636MiB, actual free<4096MiB,
own NVML process memory>8192MiB, or monitor failure. Torch allocator remains
hard-capped at8GiB; NVML total process memory additionally includes CUDA context
and libraries, so the effective allocator budget can be lower than8GiB. This
headroom is a prospective resource screen, not proof of service latency safety.

Only our fresh child process group may be terminated. Existing service PID is
never signalled, reprioritized, attached, queried by HTTP or altered. Busy/new
service demand may stop our job; never stop the service to save the experiment.
Polling may miss brief peaks; NVML commands can delay RSS/output samples by up
to their bounded command times. No OS hard-peak or zero-interference guarantee.

400 total objective evaluations,600s no-new-optimization,840s work deadline,
900s total,8GiB sampled aggregate hostRSS,100MiB new output all remain.
The CUDA limit is REDUCED from12GiB to8GiB (Torch reserved and sampled total
process).900s guard uses890s trigger plus10s reserve for NVML+child cleanup.
No new scientific evaluation validates8GiB feasibility in advance; OOM/cap stops
without retry. Do not infer fit feasibility from source review or free memory.

No new approval exists. Exact reviewed source/new card and fresh normal quota
(known remaining>=80%) plus thread/producer checks are required before any
deployment or attempt. Original R1 approval cannot authorize this new GPU/run.

## Evidence of inspection

Local preparation-only JSON files:
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/uv_head_c1_preparation_20261018/
resource_inspection_gpu037.json, resource_service_identity_gpu037.json,
gpu3_service_profile.json. These contain OS/NVML observations, not scientific
payloads. They are not runtime inputs to the approved scientific worker; the
small static service profile is frozen in inputs.json as resource metadata.
