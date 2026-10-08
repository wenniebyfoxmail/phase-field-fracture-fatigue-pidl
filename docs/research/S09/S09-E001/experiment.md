---
storyline_id: S09
experiment_id: S09-E001
protocol_revision: v0.2-data-bound-prototype
status: analysis
primary_storyline: S09
scientific_verdict: inconclusive
---

# 简化网格算子的三峰值条件化原型

## Scientific question

同一几何、材料与加载模板下，显式近期历史、原生空间支持、raw增量监督和短自主滚动能否产生位置与幅度可辨的裂缝增长？2026-10-08 已执行 P1；现有结果不满足小窗口拟合目标，P2 未启动。

## Claim changed by success or failure

P1 成功仅支持小窗口可拟合；P2 成功仅支持有限开发预测信号。失败定位状态/梯度/标度问题，不修改旧 Hard5 FAIL，不支持真实道路或跨网格结论。

## Reuse decision

沿用现有 mesh_operator 图组件、统计、native-mesh数据/图像工具；连续积分核、raw监督和明确状态合同按新设计实现。实现前需在干净工作区核实实际复用版本。

## Protocol candidate (not frozen)

当前权威设计为 `../neural_operator_design_20261008.md` 第9节；Pro原文与采纳决定在 `../reviews/20261008_chatgpt_pro/`。

- Data/holdout：现存同模板三峰值档案；完整物理轨迹分组，三输入/三目标不得跨分区。确切manifest、字段、噪声floor与split待绑定。
- Comparator：persistence、constrained-linear；旧PIDL仅在状态可匹配时作secondary。
- Validity：身份、字段单位/空间支持、accepted时序、完整加载路径、无未来输入/训练泄漏。
- Primary gate：P1增长增量MAE/persistence<=0.8；P2三步全域误差R3<=0.95。
- P2 non-degeneracy safeguards：预测累计增长比>=0.25；停滞最大假增长<=0.25G_ref+2tau。tau及G_ref定义见设计，不使用测试集调阈值。
- Stop rule：P1 1000更新、P2另3000更新上限；非法时序、NaN、无可用梯度停下修复。无增长则不可评；无停滞仅growth-only。
- Minimal evidence：receipt、固定起点场图/比较表、学习曲线与decision；不把训练loss当泛化证据。

## Code review

External design review: ChatGPT Pro READY_WITH_CHANGES（2026-10-08）；本地采纳修订已记录。未绑定新代码commit/runner/config/data lock，故 Code Ready 未完成。不得用该设计审核替代代码审核。

## Runs

无。未提交任何producer训练。

## Evidence review / Scientific verdict

无实验结果。inconclusive仅表示本实验还没有数值证据。

## Next action

字段能力与split核实 → tau及窗口库存 → 实现/检查P0 → 冻结协议与代码审核 → 合规producer上的P1。

## 2026-10-08 v0.2 implementation / data-binding amendment

This amendment precedes every producer Run. The reviewed v0.1 design remains in
its submitted snapshot. Current candidate configuration: `configs/s09_e001.json`.
Runner: `SENS_tensile/run_s09_operator.py`; source: `source/s09_{data,operator}.py`.

**Tier/claim:** T0/T1 diagnostic implementation and processed-archive memorization;
not teacher qualification, native mechanics, physical validity or confirmation.
The source package already clipped bounded fields; no further teacher repair is
performed. Actual accepted/post-history timing of these legacy element exports
is unresolved. The supported target is explicitly the stored cycle-peak vector,
not a claimed fully synchronized mechanics state. P1 may proceed in that scope.

- Evidence: `hard5_loao_gno_dataset_v1_20260826`, identity checked against its
  existing manifest and trajectory hashes. Geometry hash is explicit because
  its NPZ also contains old development labels; the loader accesses only
  `centroids`, `areas`, `connectivity`, never its `states` or event metadata.
- Training: complete U0.11 and U0.13; development: U0.12; no untouched test.
  P1 uses 16 deterministic, evenly spread training windows; no event-relative
  origin selection or first-hit inputs. Exact selected origins are emitted by
  the audit runner before training. Statistics use training IDs only.
- Primitive outputs: stored element damage, accumulated history, transformed
  raw driver. Archived `f` is not an output and is not reconstructed from mean
  history. No pointwise-constitutive claim is made about these mean fields.
- Prescribed peak-to-peak sequence is Umax*[0,0.25,0.5,0.75,1], beginning at the
  previous peak. The retained Hard5 cadence is explicit; substep closure is
  unverified. Coordinate features use native specimen coordinates; no unverified
  physical ell value is invented.
- Radius amendment: r=0.02 would yield 25,610,434 edges. r=0.005 gives 1,728,852
  edges (max 25 neighbors) on this solid diffuse-precrack rectangle. Freeze the
  latter physical-coordinate support for the prototype with a 2-million edge
  fail-closed cap, rank-8 kernels, width64, 256 coarse bins, full fine-field skip.
  Boundary feature is native exterior-cell membership derived from topology,
  not a fabricated Dirichlet node map. No mesh-convergence claim.
- tau=1e-7 is a declared diagnostic float32-resolution assumption, NOT measured
  solver noise. Training G_ref=0.00020968584789755282. There are 177 legal training
  origins and zero one-step stagnant windows at this floor. Use 16 growth windows
  without fabricating stagnation. A full stop-growth validation remains absent.
- P1 primary: full-domain area-weighted damage increment MAE / zero-increment
  baseline <=0.8, aggregated as sum errors / sum baseline error over selected
  growth windows. A 20% in-sample margin is a diagnostic engineering target,
  not a scientific tolerance. Other losses do not vote.
- Stop: at first passing checkpoint (assessed every50 updates) or 1000 updates;
  invalid identity, irreversibility, nonfinite loss/gradient cause failure.
  PASS supports only fitting these16 processed windows; FAIL means this frozen
  prototype did not meet its bounded fit target; missing growth => inconclusive.
- P2 is implemented for later use: autonomous3-step at uniform origins c3,c8,...;
  primary/guards from the Pro amendment, selection on development error. P2
  requires a matching passing P1 checkpoint. It is not automatically launched.
- Producer selected: Taobo / GPUServer8. No alternative producer fallback.
  Fresh Run receipts, Linux/host/CUDA/commit/clean-tree checks are mandatory.
- Minimum P1 evidence: immutable code/config and data audit, receipt, training
  history, initial/best/latest metrics, checkpoint, compact decision. No figure
  is required for the tooling/memorization verdict; field evidence is needed
  before any later crack-morphology claim.

Code review remains pending until bound to the exact committed implementation.

## 2026-10-08 P1 execution update (supersedes earlier pending sections)

- Code Ready: independent PASS on exact implementation `f58df2d398b9702030f7789f8a8f39f7e8386b2d`; 7 focused tests passed.
- R001: execution failed before training because import bytecode created an untracked cache in the sparse release. No scientific result.
- R002: same code/config/data, environment-only `PYTHONDONTWRITEBYTECODE=1` fix independently confirmed; fresh Taobo root. Completed 1000 updates, exit 0.
- P1: best increment MAE ratio 0.9979861337183021 at step850, against frozen <=0.8. **FAIL** for bounded fitting target; execution succeeded. No P2 or PINO run.
- Allowed: the graph operator and supervised optimization execute on this mesh within measured memory. Not allowed: learned crack-growth prediction, generalization, physics qualification, or rejection of Neural Operators as a method class.
- Detailed result, evidence review and next diagnostic: `P1_decision_20261008.md`. Previous candidate/pending prose above is historical.
