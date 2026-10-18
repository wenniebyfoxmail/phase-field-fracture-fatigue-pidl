# S04-E011-UVH-C1-PC16-CARD-r1 — approval candidate

2026-10-18. **PREPARED, NOT APPROVED, NOT DEPLOYED, NOT RUN.**
This is a new solver-coordinate diagnostic, not r2 retry/resume. Old r2's
source9a0bf3c7, negative result and consumed authorization remain unchanged.

|Binding|Exact value|
|---|---|
|Owner|验证位移–damage 耦合机制 /01a14e3b-f1ff-7360-a084-c1f13b261cc6|
|Executable source|55c1d266a3418c8dcf7618353699b4699410f3d2|
|Frozen design|52d240880e91124bcdf30ee502922e3ad93c4c2c conditioning_proposal_v1_20261018.md|
|Protocol|S04-E011-UVH-C1-PC16-v1, protocol.md + inputs.json + resource_card.md at executable source|
|Fresh Run ID|pf_s04e011_uvh_c1_pc16_r1_20261018|
|Producer|Taobo drtao@172.16.100.2 / GPUServer8 /usr/bin/python3|
|GPU|Physical3; UUID GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb; worker logicalcuda:0|
|Root|/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r1_20261018|
|Code/cwd|/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r1_20261018/code|
|Archive/output|/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_pc16_r1_20261018|
|Guard log/claim|Root/guard.log and Root/attempt_claim.json|
|Local retrieval destination (future)|/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_uvh_c1_pc16_r1_20261018/authorized_execution/|

The source row identifies executable code and source-controlled protocol/input/
resource contracts. The final card/review record may live in a later documentation
commit; no later executable source is implicitly approved. Independent STATIC
review receipt will identify exact source and card. No numerical-equivalence,
resource-feasibility or execution PASS is claimed by a static review.

## Exact inputs: five files,20,911,589bytes

Future approved worker hashes these entire files once, then decodes only the
listed fields. Whole-file hashing is source access and has NOT occurred during
preparation. PT is weights_only=True; NPZ allow_pickle=False. JSON files are
whole-text parsed, then only whitelisted top-level keys are selected; listed
metric objects include their saved scalar members. No discovery/extra endpoint
arrays, no source copy/generation if an input is missing. Paths below are literal.

1. **state**,15,183,163bytes
   `/mnt/data2/drtao/wennie/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production/inputs/c1_peak.npz`
   SHA256 `ac63ba676376179f0539c156e3fd49f8e74c5eba386f684c71a617bb637b7fdd`.
   Keys `nodes,cells,freeu,u_fem,v_fem,d_fem`; ru_fem is not decoded.
2. **original model**,4,510,165bytes
   `/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep601_U0.12_s04e011_q4_production_ad749c8_current_active_native_q4_gp4_femIrrGP4_hardAlphaRecoverU0_u0.0299999-0.0599999-0.0899999-0.12-0/best_models/trained_1NN_4.pt`
   SHA256 `9c4ebbe4bcf1d4bc6b4997f1072a6a5f68e0c94783d0365b0224a7175ed12d1b`.
   Decode full weights-only original state_dict; hidden/activation/damage rows frozen.
3. **NEW transform capability**,1,204,696bytes
   `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/head.npz`
   SHA256 `deaf3fea860a4563df84f7909afbde49d76430b633bce542b4896ef9526e8d65`.
   Decode **ONLY `transform`**, expected float64(401,388). Do not decode/use
   final `z,uv_weight,uv_bias`; start at original UV z=0, never r2's fitted head.
4. **frozen summary**,2,527bytes
   `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/summary.json`
   SHA256 `ee4062e4e9d990bee7b5c7507301894b53c88f57c833c67ea092cbdbcafaa877`.
   Select `protocol,run_id,original,saved_PBD,head,retained_gradient_l2,
   full_head_gradient_l2,full_head_gradient_inf,numerical_energy_uncertainty,
   stationarity_screen`. Saved comparators only; no PBD/r2 endpoint reevaluation.
5. **frozen basis metadata**,11,038bytes
   `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/basis.json`
   SHA256 `f6d6c38ddb75460e7490f96b8a0743659cfad52117fd3455b30580228c5ccda3`.
   Select `rank,columns,rcond,retained_condition,omitted_directions`.

Identities1–2 came from tracked r2 inputs.json;3–5 from the already-stored r2
transfer_manifest.json. No actual source-file read/hash was needed to prepare
this list. Its correctness against the producer still needs future runtime
verification. The added transform read is NOT covered by old r2 approval.

## Same problem, one metric change

Same c1s4/U=.11999988/outer9 fixed FEM damage, original model4/hidden/activation/
damage row, original UV initial coefficients, Q4/2x2GP, elastic objective/E0,
same stored401x388 transform and ALL776 original z coefficients. No new basis
SVD/rank/cutoff, regularization, Delta feedback, damage/history or rollout.

At original z=0 use16 fixed Gaussian sketch HVP,16 projected HVP,2 operator
probe HVP. QR/eigh build a frozen invertible C=I+Q(S^-1/2-I)Q.T, identity on
Q complement. Optimize F(Cy), all776 y coordinates, y0=0. No eigenvalue floor,
jitter/truncation/smaller-k/seed refresh. Actual field/energy/gradient equivalence,
positive curvature and C/inverse checks are enforced prospectively in code.
Stationarity is ORIGINAL z infinity norm<=1e-8; y gtol=0, memory10/maxls20/
ftol1e-14. Restore only last callback-confirmed accepted point or original zero.

## Shared work/time/memory budget and stops

|Allocation|Maximum|
|---|---:|
|34 HVP,2units each|68units|
|Initial/equivalence/FD controls|16units (12 planned)|
|Optimization incl trials/callback rereads|308units|
|Final actual/basis/z-gradient reads|8units (3 planned)|
|Shared total; no reserve reallocation|400units|

One energy or energy+first-gradient=1; standalone-gradient=1; HVP=2 per
direction including its forward/first/second derivative. Any separately issued
energy/gradient is additionally charged. No cached/batched/free-setup discount.
QR/eigh/factor construction, input IO, serialization and plots are INSIDE the
same900s/RSS/CUDA/output envelope, with timing/ledger records. Only wrappers
that charge the ledger invoke the target energy. No separate smoke/probe job.

900s total (guard cutoff890+10cleanup), no new optimizer eval after600s, no new
scientific operation after840s; boundary checks cannot preempt in-flight calls.
8GiB sampled aggregate worker-tree RSS;8GiB Torch reserved AND8GiB own total
CUDA-process NVML;100MiB generated outputs/caches/logs/receipts (1MiB receipt
reserve). At least4096MiB sampled GPU free margin. Max oneGPU/0.25GPU-hours.
8GiB numeric construction/runtime fit remains UNTESTED.

Before launch: relevant-chat/producer duplicate check; unresolved same-item
owner stops. GPU3 index↔UUID verified; exact resident profile below;3 samples1s
apart with free>=12288MiB, whole-GPU util<=10%, service<=11636MiB. Host available
RAM>=16GiB; canonical data2 mounted/free>=5GiB; df includes/,data2,data3.

Allowed sole resident: PID3295884/root, start_ticks213283304, UIDs[0,0,0,0],
cmdline hash a49591b49d77aff5b8f23818f5b03d9bf9f3a1d71fe6b7f34f1bb3130cf54425,
cgroup hash 223dd996e67fe2019f27964c5e7348c142bee134b5ac7ea531fe7f13568996fd,
uvicorn api:app port39070; prior baseline10612MiB, maximum11636MiB. Recheck
identity at admission AND runtime. Restart/change/unreadable/new CUDA process/
service growth/low-free/monitor failure stops, never re-whitelist or mutate
another process. No GPU switch. Two NVML queries each2s timeout;>=1s between
completed snapshots, nominal100ms RSS/output checks can be delayed. Sampled
resource limits do not promise hard peaks or zero service-latency impact.

Any source/input/identity/IO/nonfinite/OOM/curvature/rank/inverse/equivalence/
realization/resource failure ends the sole attempt. No retry/resume/extra seed/
k/rank/optimizer/budget/GPU/source/producer. The guard atomically consumes the
claim BEFORE preflight. Lost launch reply is unknown state: inspect claim and
owned PID/receipts, never launch again. Optimization cap/deadline permits only
reserved final reporting before science cutoff; no continued optimization.
No80% quota floor; do not reset or buy credits.

## Deployment and exact single invocation, AFTER separate human approval

Read-only SSH checks, source deployment, these five file accesses, one solve and
owned-report retrieval all require this new card's approval. Preparation did
none. Do not touch an existing producer checkout. Create the exact fresh root
only if absent. Use a Mac-prepared Git delta bundle from reviewed r2 source
9a0bf3c7f503f1e1b27dba480d2168348459a30a to the executable source in this card.
First verify the old r2 code checkout at
`/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r2_20261018/code` is still clean at
that r2 SHA. It is a code prerequisite only; do not reopen old scientific
payloads. Clone its Git source into the fresh code root without modifying it;
materialize only source-controlled Python dependencies/new tool/contract and
gitignore via sparse checkout, import bundle and detach at this exact source.
Check full HEAD and clean status. Missing/changed prerequisite or deployment/
transfer failure stops; no alternate checkout, fetch-source or retry. Keep
bundle/command/source/PID/cwd/GPU/time receipts under the owned fresh root.

Invoke exactly once, detached, using this full UUID rather than ordinal3:

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r1_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_pc16/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-PC16-CARD-r1 --expected-source 55c1d266a3418c8dcf7618353699b4699410f3d2 > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_pc16_r1_20261018/guard.log 2>&1 < /dev/null &
```

The approval-ref flag itself is not authorization. Do not run a help/smoke/
fixture/CPU/numerical pretest or separate HVP job under this approval.

## Evidence and interpretation

Retrieve only this new owned root/output: authorization+preflight+deployment+
launch/terminal/input/guard/worker receipts; work_ledger.jsonl, trace.json,
accepted.json, conditioning.json (checks/timings), pc16_factors.npz, head.npz,
fields.npz, basis.json, summary.json; decision.png+decision.md+README_analysis.md,
logs/caches and transfer size/hash manifest. Freeze and verify retrieval,
report exact completeness and inspect same-run rendered PNG. Do not decode/
rescore scientific outputs in a second numerical job; future analysis needs
its own authority. Do not write Obsidian/Roadmap or other-owner documents here.

Primary remains actual candidate elastic energy versus frozen PBD, G>=1e-4
and gain>10*readout uncertainty. Report smaller resolved gains/regressions/
ambiguity separately, plus component change versus r2 and original-z gradient.
Beating r2 alone is not the PBD criterion. Nonstationarity prevents any optimum/
capacity verdict; no coupling/root-cause/teacher/physical/road conclusion.
The main S04 owner will read this result and maintain the shared milestone.

Approval wording after completed static review:
“批准按S04-E011-UVH-C1-PC16-CARD-r1、源码55c1d266a3418c8dcf7618353699b4699410f3d2，
在Taobo物理GPU3执行唯一一次PC16检验，含卡内SSH检查、部署、五文件读取（r2 head.npz仅transform）、
34HVP构造、单次求解及报告取回；遵守400共享工作单位、900/600/840秒、8GiB RSS/8GiB CUDA、
100MiB及4GiB余量监测，失败不重试、不改动其他进程、不重置或购买额度。”
