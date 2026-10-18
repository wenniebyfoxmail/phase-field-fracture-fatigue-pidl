# GPU3 resource amendment r2 — preparation only

2026-10-18. r1's terminal preflight stop remains immutable; it has no scientific
result. This new prospective resource card is NOT approval, reset, retry or
continuation of r1. No SSH, source-array access, deployment or execution occurs
in this preparation. New Runpf_s04e011_uvh_c1_pc16_r2_20261018 requires a new
exact-source/card execution authorization.

Only change: select one of TWO admitted GPU3 occupancy modes at the FIRST
admission snapshot and pin that mode for all later admission/runtime snapshots.

|Mode|Admission|Runtime|
|---|---|---|
|empty|No CUDA compute process on GPU3|Only our worker may appear|
|exact_service|Only previously frozen PID3295884, with exact start_ticks/UID/cmdline/cgroup identity and<=11636MiB|Same exact service plus our worker only|

Empty mode does not require a previously expected service to exist in /proc.
In service mode, missing/exited/restarted/changed/unreadable service still stops.
Mode changes in either direction, even service exit leaving more free memory,
stop. Unknown CUDA PID, NVML failure, UUID mismatch, low margin or any identity
failure stops. No live service discovery/re-whitelist and no process mutation.
The unchanged service tuple, full five-file paths/keys/hashes and all limits
are copied to inputs_resource_r2.json; no science array was opened or hashed.

Same physicalGPU3/full UUID GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb, logical
cuda:0; no GPU/producer expansion. Same three admission snapshots1s apart,
free>=12288MiB/utilization<=10%, runtimefree>=4096MiB, service<=11636MiB,
host available>=16GiB, mounted data2/free>=5GiB. Same own NVML/Torch8GiB,
hostRSS8GiB,100MiB output,900/600/840s and sampled-monitor/cleanup reserves.
Same paid400 work units68HVP+16controls+308optimization+8final, no reallocation.

Same PC16-v1 science, original c1s4/d/hidden/UV initial field,388-column frozen
transform/776 coordinates,34HVP, original-z stopping, comparator and actual
reconstruction. worker.py is byte-for-byte the already reviewed3dfef418 version;
no algorithm-core re-review or new numerical equivalence claim is needed here.
Original r1 guard/contract/card remain untouched; new guard_resource_r2.py uses
new contract/card/run/claim paths and pins the selected occupancy mode.

Existing r1 preflight only establishes the former service was absent, UUID
correct,23,348MiB free and0% utilization at12:31:58UTC. It did not enumerate
GPU3 compute processes after the decisive service failure. Therefore it does
NOT establish current empty-mode admission or current resource availability.
Both modes still require a future newly authorized live check.

No r1 claim/root/output is created, deleted, rewritten or reused. This new
card has its own one-shot claim; any preflight/deployment/identity/input/IO/
numeric/resource failure ends that future attempt without retry, cap change,
GPU switch or service mutation. Lost SSH reply remains unknown state.
