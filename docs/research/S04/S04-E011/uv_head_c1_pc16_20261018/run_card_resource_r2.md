# S04-E011-UVH-C1-PC16-CARD-r2 — minimal resource amendment, NOT AUTHORIZED

2026-10-18. **PREPARATION ONLY.** r1 remains terminally stopped at admission;
0HVP/0 science reads. No claim reset, continuation or automatic new execution.

- Source: `0d85de8ae7401277a157fbdc1f5cbd39e14b2f4f`; algorithm worker is
  unchanged from independently reviewed `3dfef418828e53632b3a5c90521ab8989dbf9673`.
- Science: PC16-v1/c1s4, same388-column transform/776 coefficients/initial UV/
  fixed d and hidden layers/target/comparators/stops. The five full input paths,
  bytes, SHA256 and allowed keys are unchanged in [inputs_resource_r2.json](inputs_resource_r2.json).
  r2 head.npz still permits ONLY transform; no fitted-head start or endpoint reevaluation.
- ONLY resource-policy amendment: first of three admission samples chooses
  **empty** (no other CUDA compute process) OR **exact_service** (only frozen
  PID3295884/start_ticks/UID/cmdline/cgroup profile,<=11636MiB). Empty mode does
  not demand a departed service. Pin the mode through remaining samples/runtime;
  any mode/identity change, unknown PID, monitor failure or low margin stops.
  No re-whitelist or other-process mutation. [Exact policy](resource_policy_r2.md)
  and [guard delta](resource_guard_r2.diff); algorithm core is outside this amendment.
- Same physicalGPU3/UUID `GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb` only;
  admission3 samples1s apart, free>=12288MiB/util<=10%; runtimefree>=4096MiB.
  Same host>=16GiB/data2>=5GiB;8GiB RSS and own CUDA NVML/Torch caps;100MiB
  output;900/600/840s, same sampled-monitor and cleanup limits.
- Same400 paid units: HVP68+controls16+optimization308+final8, no reallocation.
- NEW Run: `pf_s04e011_uvh_c1_pc16_r2_20261018`; fresh root
  `/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r2_20261018`, code subdir;
  output `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_pc16_r2_20261018`.
  Own guard.log/attempt_claim.json under new root; never reuse/delete r1 paths.

Future deployment must be the exact NEW source above, clean checkout; the old
source_3dfef418.bundle alone cannot deploy this new guard/contract. Prior card's
scientific scope, duplicate checks, SSH/deployment/five-file read boundaries,
one-shot/no-retry, final outputs/verification and interpretation remain as
specified in [r1 card](run_card.md), with ONLY the resource/identity/run/path/
source/entrypoint rows replaced here. A fresh explicit authorization must name
this new card/source before any further SSH, payload access, deployment or run.

Prospective single invocation AFTER that new authorization:

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r2_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_pc16/guard_resource_r2.py --execute-approved --approval-ref S04-E011-UVH-C1-PC16-CARD-r2 --expected-source 0d85de8ae7401277a157fbdc1f5cbd39e14b2f4f > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r2_20261018/guard.log 2>&1 < /dev/null &
```

Any future preflight/deployment/input/numeric/resource failure ends its sole
attempt. No retry/GPU/card/cap/service change. No current admission, numerical
equivalence or8GiB feasibility claim. This preparation performed no SSH,
science-array access, deployment or execution; no quota reset/purchase.
