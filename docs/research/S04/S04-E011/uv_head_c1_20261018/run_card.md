# S04-E011-UVH-C1-CARD-r1 — final approval candidate

2026-10-18 Europe/London. **Preparation only; no run or scientific reads approved.**
User approval of preparation is not execution approval. This card cannot be
approved by an agent/reviewer. Only the human can authorize this exact version.

| Binding | Exact value |
|---|---|
| Owner | 验证位移–damage 耦合机制 / 01a14e3b-f1ff-7360-a084-c1f13b261cc6 |
| Parent / protocol | S04-E011 / S04-E011-UVH-C1-r1, protocol.md and inputs.json |
| Run | pf_s04e011_uvh_c1_r1_20261018 — one new attempt, not a PBD rerun |
| Code source | `52a391fb763b7eeed1ef04fb62666fdeac2c99e1` |
| Local worktree | /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-c1-uv-energy-head-20261018 |
| Producer / account | Taobo `drtao@172.16.100.2`, physical GPU0 only, Python `/usr/bin/python3` |
| Fresh root / exact cwd | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r1_20261018/code |
| Output/archive | /mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r1_20261018 |
| Guard log / claim | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r1_20261018/guard.log and attempt_claim.json |
| Model overwrite / history / rollout | 0 / 0 / 0 |

## Exact requested action

If approved, first refresh normal Codex quota (remaining must be known and>=80%)
and read-only conversation/producer duplicate/resource checks. Prepare a fresh
clean code checkout at the exact code commit above, via local Git bundle/source
transfer; record transfer bytes separately from generated result bytes. No public
push or other-owner checkout modification is part of this card. Recheck checkout
HEAD/cleanliness. Do not copy, repair, rename or regenerate missing scientific
inputs. Then invoke the following guard once, detached; capture shell PID and
guard/worker PIDs, hostname, GPU, command, source/cwd/log/archive and UTC times.

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r1_20261018/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_uv_head/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-CARD-r1 --expected-source 52a391fb763b7eeed1ef04fb62666fdeac2c99e1 > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_r1_20261018/guard.log 2>&1 < /dev/null &
```

Literal approval-ref is a binding/receipt, not proof of human approval by itself.
Do not issue this command unless this card/source/input/budget version has
explicit human approval. Source/inputs/producer/budget changes require a new
card approval. A lost SSH response is unknown state, never permission to retry.

## Four and only four scientific/control input files

Full absolute producer paths, bytes, existing hashes, selected fields and local
archive reference pointers are frozen in [inputs.json](inputs.json). This is the
complete runtime data allowlist, not an example. Total21,049,958bytes:

1. Prepared `c1_peak.npz`,15,183,163bytes, hash `ac63ba67…7fdd`.
   Decode nodes/cells/freeu/u_fem/v_fem/d_fem/ru_fem only. It contains other
   members: whole-file hash reads their bytes but they are not decoded/used.
2. Original `trained_1NN_4.pt`,4,510,165bytes, hash `9c4ebbe4…12d1b`.
   Full weights-only state_dict; hidden weights/activation/damage row frozen.
3. PBD `c1_s4/U_energy/fields.npz`,1,355,797bytes, hash `6f7a52ed…6e6f`.
   Read u/v/d once for identity readout and same-run comparator figure.
4. PBD `c1_s4/U_energy/result.json`,833bytes, hash `939ccbae…dc9`.
   Saved Eel=.005672469584399648 and other U-result metadata.

No remote file existence/size/hash has been freshly checked during preparation;
these bindings come from existing PBD preparation/retrieval receipts. Missing or
changed input stops, without alternative archive search or reread/retry. All
four files receive one full-file runtime hash and one decode/read, inside budget.
No E025 nine-source read, B32/C33 fit/evaluation, L32/E026, c20, fresh FEM run,
checkpoint3, U0.1175/U0.125, confirmation or full-trajectory analysis.

## One computation and budget

Fixed c1s4 FEM damage, inherited Q4/2x2GP/Amor operator, original float64 local
UV boundary and model4 features. One fixed-rcond1e-10 mass-weighted SVD, one
additive retained UV head energy arm. No alternate rank/seed/optimizer. PBD is
read once for identity/comparison, never reoptimized. Actual-network head
reconstruction, unchanged hidden/damage-row checks and field reading are required.

| Resource | Maximum / behavior |
|---|---|
| Objective/gradient budget | 400 TOTAL, including FD/trials/callbacks and all elastic reference/final readouts |
| Optimization | No new optimization evaluation from600s; reserve8 evaluations for final readouts |
| Work / envelope | No new worker scientific evaluation from840s;900s whole guard, including hashing, SVD, fitting, plots/cache/receipts/cleanup |
| CPU / GPU | Numerical threads1; physical GPU0 only;0.25 GPU-hours maximum |
| Host / CUDA memory | Aggregate sampled worker-tree RSS8GiB; Torch CUDA reserved12GiB |
| Newly generated output | 100MiB including candidate, traces, plots, logs, tmp/cache and receipts in both roots; immutable code deployment input counted separately |
| Resource admission | GPU0 no compute process and>=16GiB free; host>=16GiB available; data2 canonical mount and>=5GiB free |

100ms RSS/output sampling cannot guarantee OS hard peaks. Runtime OOM is a
terminal failure. Execution does not silently select another GPU or producer.
Approval grants no process/service mutation except stopping this guard's own
fresh child process group at its declared cap.

First invalid source/path/hash, duplicate, resource failure, nonfinite value,
numerical contract failure, interrupted accepted step, cap, IO failure or unknown
terminal state -> retain receipt and stop; no retry/resume/budget change. The
atomic claim consumes the invocation even on source/resource preflight failure.
SVD rank-zero, derivative inconsistency or realization mismatch is invalid, not a
physical counterexample. Finite optimizer deadline/budget returns the last
confirmed accepted head and labels stationarity unresolved where appropriate.

## Decision and minimum return

Report actual G=(saved_PBD_Eel-actual_head_Eel)/saved_PBD_Eel. Screen G>=1e-4
and absolute reduction>10times observed readout uncertainty. No additional
5%/10% or all-field-win demand. All measured gain sizes, residual/H1/L2 and
hotspot/field costs remain visible even if the screen is missed. Lower resolved
same energy witnesses a practical local optimization opportunity; it does not
establish mechanical closure, whole-network capacity, coupled evolution or
physical truth. No resolved improvement stops this candidate without a new arm.

Return head/conditioning, candidate fields, energy/force/H1/L2/full+retained head
gradient/uncertainty summary, counted trace, guard/worker receipts, one same-run
full-field/signed-difference/energy/residual figure and README_analysis. No new
fits or post-run rescoring. After terminal verification, retrieve only the new
owned output/log/claim receipts and verify transfer; viewing its same-run report
and figure is in scope, but independent scientific array recomputation is not
included. No Obsidian, Roadmap, other-chat message or other-owner document edit.

## Approval wording

“批准按 S04-E011-UVH-C1-CARD-r1、使用52a391fb763b7eeed1ef04fb62666fdeac2c99e1
执行唯一一次c1s4同能量UV头检验，含本卡所列SSH检查、精确源码部署、四文件读取、单次求解及同次报告取回；
遵守400次／900秒／8GiB RSS／12GiB CUDA／100MiB，失败或触限不重试。”

Static review receipt is separate and cannot replace this human approval.
