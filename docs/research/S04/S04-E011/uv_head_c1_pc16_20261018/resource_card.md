# PC16 resource contract — inherited GPU3 service policy

2026-10-18. PREPARED ONLY. No current resource/SSH check performed.
Binding JSON: inputs.json/resource_policy and budget, enforced by guard.py.

Producer Taobo drtao@172.16.100.2 / GPUServer8 /usr/bin/python3. PhysicalGPU3
ONLY, UUID GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb. CUDA_VISIBLE_DEVICES must
be this FULL UUID, worker uses logicalcuda:0. No GPU0/7 or producer fallback.

Exactly one existing CUDA service is allowed alongside our worker:
root PID3295884, start_ticks213283304, UIDs[0,0,0,0], command description
/usr/bin/python /usr/local/bin/uvicorn api:app --host0.0.0.0 --port39070.
cmdline SHA256 a49591b49d77aff5b8f23818f5b03d9bf9f3a1d71fe6b7f34f1bb3130cf54425;
cgroup SHA256 223dd996e67fe2019f27964c5e7348c142bee134b5ac7ea531fe7f13568996fd.
Baseline10612MiB; ceiling11636MiB. PID alone is insufficient. Identity change,
restart, inaccessible identity, absent resident, any extra CUDA process, or
monitor failure stops; no re-whitelisting/service request/benchmark/mutation.

Future execution admission: check relevant chats and all matching Python workers
for UVH/PC16 before deploying/launching; unresolved ownership stops. Guard also
scans actual /proc executable identity, avoiding launcher-shell substring false
positives. Atomic attempt_claim.json consumes this card before resource preflight.
Existing claim or output stops without cleanup/reuse. Only one detached guard
and its own child are authorized. Lost SSH reply means unknown state: inspect
claim/process/receipts before doing anything, never submit again.

Three NVML admission snapshots1s apart: index3↔UUID exact, only expected service,
free>=12288MiB, whole GPU utilization<=10%, service<=11636MiB. Host available
RAM>=16GiB. Check df for /,/mnt/data2,/mnt/data3; data2 must be its canonical
mounted filesystem with>=5GiB free. Fresh run root and archive both underdata2.
No writes/large caches on home,/tmp,root; task cache/tmp under the new archive.

Runtime: SAME service identity/ceiling, only resident+our worker; free>=4096MiB;
own total NVML CUDA-process<=8192MiB AND Torch peak reserved<=8GiB. Context and
libraries count toward NVML cap, so effective allocator room can be smaller.
Sampled worker-tree hostRSS<=8GiB; generated files including cache/tmp/logs/root
receipts<=100MiB. Reserve1MiB for final receipt; immutable source excluded.
Shared work400 units: HVP68/controls16/optimization308/final8. No free setup.
No new optimizer evaluation after600s, no new scientific operation after840s;
boundary checks cannot interrupt an in-flight CUDA/library operation.900s total,
guard cutoff890s plus10s cleanup, max0.25GPU-hours for one GPU. QR/eigh/factor
application/serialization remain in the same time/memory/output envelope.

Runtime NVML consists of two commands each2s timeout, next snapshot starts>=1s
after prior completion. Nominal100ms RSS/output checks can be delayed by NVML.
These are sampled limits, not OS-enforced peak guarantees or a zero-impact SLA.
Any resource monitor failure/limit causes only our child process group to stop
(TERM then KILL); existing services are never stopped or reconfigured. New
source/identity/construction/curvature/equivalence/IO/nonfinite/OOM failure is
terminal, no retry/resume/new seed/k/rank/GPU/cap or extra smoke. Optimization
allocation/deadline stops only optimization and uses the reserved final report
allocation while science time remains. A failure in final checks is terminal.

No 80% Codex-quota floor applies. No quota reset or purchase. Static review
cannot verify current service state, numerical equivalence or feasibility8GiB.
