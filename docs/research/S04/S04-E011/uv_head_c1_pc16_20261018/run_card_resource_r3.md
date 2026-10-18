# S04-E011-UVH-C1-PC16-CARD-r3 — resource-only approval candidate

2026-10-18. **PREPARED, NOT APPROVED OR RUN.** PC16-r1/r2 admission stops and
old UVH negative stay frozen. No claim reset, retry or continuation is implied.

- Exact source: `2a2a7e435dcc779442d584c3ee9f7df565913eae`. worker.py remains
  byte-identical to reviewed3dfef418; GPU monitoring logic remains reviewed0d85de8a.
- Sole resource-profile change: replace departed PID3295884/start213283304 with
  observed root PID2741803/start534715189, UIDs[0,0,0,0]. Same command SHA
  `a49591b49d77aff5b8f23818f5b03d9bf9f3a1d71fe6b7f34f1bb3130cf54425`, cgroup SHA
  `223dd996e67fe2019f27964c5e7348c142bee134b5ac7ea531fe7f13568996fd`.
  Uvicorn api:app/port39070, same Docker container/command, new process instance.
  Service baseline724MiB; ceiling **1748MiB**, preserving the prior1GiB growth
  allowance and reducing the old11636MiB absolute ceiling. [Read-only assessment](gpu3_assessment_20261018.md).
- Same physicalGPU3/UUID `GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb`; no otherGPU.
  First admission selects empty OR exact identified service, then pins mode.
  Three samples1s apart, free>=12288MiB, utilization<=10%; runtimefree>=4096MiB.
  Any extra PID, service restart/identity/mode change, service>1748MiB or monitor
  failure stops OUR child. No automatic re-whitelist or change to another process.
- Same five paths/bytes/hashes/allowed keys in [inputs_resource_r3.json](inputs_resource_r3.json),
  including old head.npz ONLY transform. Same c1s4/d/hidden/388basis/776coordinates/
  originalUV/PC16-v1 target/primary/original-z stopping; no Delta, new input,
  representation or comparator change. No endpoint reevaluation.
- Same shared400 units:68HVP+16controls+308optimization+8final, no transfer;
  34HVP only. Same900/600/840s,8GiB RSS/own NVML AND Torch CUDA caps,100MiB,
  hostavailable>=16GiB and mounted data2free>=5GiB. Same sampled-monitor limits.
- NEW Run `pf_s04e011_uvh_c1_pc16_r3_20261018`; fresh root
  `/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r3_20261018`, code subdir;
  archive `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_pc16_r3_20261018`.
  New own guard.log/attempt_claim.json only; never reuse/delete old roots.

Future execution needs new exact-card/source approval covering fresh duplicate/
SSH/resource checks, exact source deployment, these five input reads,34HVP,
one solve and owned-report retrieval. No such action is authorized by this
preparation. Use NEW source; old bundles alone lack this guard/profile.
Original scientific validity/accepted-point restoration/evidence requirements
remain [PC16-v1](protocol.md), [r1 card](run_card.md), with only run/source/path/
entrypoint/occupancy-profile rows replaced here. No extra scientific test.

Exact single invocation ONLY after that new approval:

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r3_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_pc16/guard_resource_r3.py --execute-approved --approval-ref S04-E011-UVH-C1-PC16-CARD-r3 --expected-source 2a2a7e435dcc779442d584c3ee9f7df565913eae > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r3_20261018/guard.log 2>&1 < /dev/null &
```

Any preflight/deployment/input/numeric/resource failure ends the sole future
attempt; no retry/GPU/card/cap/service change. Lost SSH reply is unknown state,
never permission to relaunch. Short quiet snapshots support current capacity,
not future load or zero latency impact; per-process SM was unavailable and
service application/model is unverified. All future admission must be fresh.
No scientific array read/hash, numerical test, deployment or computation took
place during this resource assessment/preparation. No quota reset or purchase.
