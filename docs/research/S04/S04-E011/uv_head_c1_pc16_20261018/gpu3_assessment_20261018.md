# GPU3 unknown CUDA process — read-only identification and capacity

2026-10-18. Direct user authority: inspect PID/purpose/actual resource occupancy,
prepare the smallest resource amendment if capacity permits; do not stop other
processes, read science arrays or start computation. This inspection is a new
read-only action, not a PC16-r1/r2 admission retry. Both stops remain terminal.

GPUServer8/physicalGPU3, NVIDIA RTX4090, exact UUID
GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb. Five NVML observations at
20:28:45–55UTC (21:28:45–55 Europe/London); whole request finished20:28:57UTC.

|Identity / purpose evidence|Observed|
|---|---|
|Only CUDA PID on GPU3|2741803, root UIDs[0,0,0,0]|
|Command|/usr/bin/python /usr/local/bin/uvicorn api:app --host 0.0.0.0 --port 39070|
|Parent|2741780, containerd-shim-runc-v2, namespace moby|
|Container|b88f90b5481d6f08747e588c8f03c93aa8dd00ff1123b8e06bd0a4b7075fae11|
|start_ticks|534715189; ps elapsed about8h24m at inspection|
|cmdline SHA256|a49591b49d77aff5b8f23818f5b03d9bf9f3a1d71fe6b7f34f1bb3130cf54425|
|cgroup SHA256|223dd996e67fe2019f27964c5e7348c142bee134b5ac7ea531fe7f13568996fd|
|Host RSS / threads|1,222,996kB /8|
|Matching UVH/PC16 Python worker|none|

The command establishes a resident Uvicorn ASGI API service. Command AND cgroup
hashes exactly match the previously allowed service; PID/start identity changed.
This is a new instance of the same API command/container, explaining why the
old exact-PID resource card rejected it. It is not sufficient evidence of the
API's particular model, business role or future traffic. /proc exe/cwd and
Docker image/name inspection were denied to drtao; no sudo, environment/log/
application-source inspection, service requests or benchmark was attempted.
Do not infer a human owner from the shared account or root UID.

|Sampled actual occupancy|All five observations|
|---|---:|
|Process NVML framebuffer|724MiB, unchanged|
|Whole GPU used / free|734MiB /23,348MiB, unchanged|
|Whole GPU compute utilization|0%|
|Whole GPU memory utilization|0–2%|
|pmon three rows|process framebuffer724MB; SM/memory fields '-' unavailable|
|Host MemAvailable|411,059,896kB|
|data2 free (df)|626G; mounted|

Per-process SM '-' is NOT measured zero. These short samples show quiet compute
and ample memory at those times; no workload/liveness or service-latency test
was performed. No zero-impact or future-load guarantee follows. Only read-only
OS/NVML/Git metadata was inspected; no payload/model/array access or computation.

## Conditional sharing decision and smallest amendment

Current capacity supports the original one-worker8GiB total CUDA cap plus4GiB
free margin. Retain the pre-existing1GiB service-growth allowance, now anchored
to724MiB: exact-service ceiling1748MiB (reduced from11636MiB). If our worker
uses8192MiB and the service grows another1024MiB, observed free would still be
14,132MiB before other changes, well above4096MiB. This arithmetic is a capacity
check using sampled free memory, not numeric-run feasibility or peak prediction.

Prepare PC16-CARD-r3 with the new exact PID/start tuple and lower ceiling; retain
the existing empty-or-exact_service modes and pin the first mode for all later
admission/runtime samples. New/changed/unreadable service, any unknown CUDA
process, mode transition, service>1748MiB, own cap, low-free or monitor failure
stops our child only. No live re-whitelist and no other-process mutation.
Same GPU3 UUID, five scientific inputs, frozen worker/representation/target,
400-unit split,900/600/840s,8GiB RSS/CUDA and100MiB. No new scientific method.
Current inspection does not satisfy future admission; all checks must be fresh
under a new execution authorization. No automatic reuse of r1/r2 permission.

Raw read-only endpoint:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/gpu3_assessment_20261018T2028Z/`
request.py.txt andresource_observations.json preserve the exact metadata request
and responses. No scientific execution receipts/results or new run root exists.
