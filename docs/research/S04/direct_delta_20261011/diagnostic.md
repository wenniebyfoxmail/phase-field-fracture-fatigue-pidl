# 逐 cycle 多变量 Delta：已有数据描述性诊断

Owner: S04 direct-Delta preparation; branch `codex/s04-direct-delta-audit-20261011`;
base `5b1eec29d2bed37d42baab5850ceb9c57ae16249`。This is a preparation scope,
not a newly registered claim-changing Experiment. Date: 2026-10-11.

## 运行前范围

问题：已有逐 cycle 的 FEM/PINN 输出能构造哪些 Delta？差异是否具有空间集中、邻域连续、
逐周期相关结构？这些描述量只指导输入/模型选择，不检验神经网络能否泛化。

复用 E013 外部 data lock（共享 checkout 的 frozen `input_lock.json`），只读三条 Umax
0.11/0.12/0.13 的处理后 FEM 和已导出 PINN peak。逐文件核对原有 lock 的 SHA256、
cycle、raw step 和 common mesh，不读取新 U0.1175、旧 partial、U0.125 或 Windows。

对每个可用 cycle 输出五个 Delta：damage、alpha_bar、fatigue_f、原始 psi_raw、
log10 psi_raw；后者是声明 floor=1e-12 的变换目标，与物理 raw Delta 区分。
计算 area-RMSE、signed mean、正差区域、top-1%-area squared-error concentration、
相邻 cycle Delta correlation/change、graph edge-jump；全网格计算，三条轨迹分别报告。
event row 保留，但严格 pre-FEM-event summary 排除 event。分层只用 fixed cycle bins
C1--20、C21--40、C41+，不以 FEM event 归一化输入。

无拟合、无 primary threshold、无 PASS/FAIL 模型结论。空间/时间相关性不证明可预测性，
同一次共享模型优化的梯度也不在此诊断内。该准备性 descriptive audit 的代码/证据尚未
独立审查；不得称作 Code Ready/Evidence Ready。

停止规则：data lock/hash、grid、shape、cycle 或 finite 校验不通过即停止；只生成一次
描述表和图，最大本地预算 5 min/2 GiB 内存，无训练 loop。图为全部轨迹的 discrepancy
曲线，以及固定 U0.12 的 c1/c20/c60/c82 residual maps；不按结果挑选图片。

复用依据：E013 `analyze_three_umax_residual_sufficiency.py` 的数据 lock、area weighting、
三轨迹身份；FEM dataset builder `prepare_hard5_loao_gno_dataset.py` 的字段/裁剪；
已存 `export_peak_trajectories.py` 的 PINN `5N-1` physical peak mapping。
新增脚本仅生成 direct-Delta 所需描述表，不重跑 POD/ridge，不重复存储大 residual arrays。

初始输出：`local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D001/analysis/`。
视觉核查后发现统一 max 色轴使 history 稀疏差异不可读；D002 仅补充逐 cycle 源索引、
原始最大值，并将显示色限改为所有固定 checkpoints 的最大 area-p99.5 absolute Delta，
每 panel 报告 saturated area。数值表仍用未裁剪全部网格。D001 保留，D002 为最终诊断包：
`local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D002/analysis/`。
coverage table 又发现 1.3927% 面积使用 triangle fallback mapping。D003 增加 contained/fallback
分层误差和 fallback squared-error fraction，辨别差异是否来自外推 mapping；无新拟合或
门限。最终包为 `local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/`。
脚本：`SENS_tensile/audit_direct_delta_cycles.py`。

## 先已核实的数据限制

- 三轨迹 FEM manifest 为 `processed_griphfith_archive_imitation_only`，
  `teacher_qualified=false`，`damage_fixed_point_gate=fail`，`physical_validation=false`。
  当前可研究的是已处理 archive 的差异；不能宣称学习到了 qualified FEM truth。
- 原 FEM loader 从 cycle summary `d_elem/alpha_bar_elem/f_alpha_elem/psi_elem` 读取，damage
  已裁剪 [0,1]、history 已截非负、f 已裁剪 [0,1]，raw 转 log10。PINN export 是 peak。
  Request31 对 cycle-summary 规定 raw=`mean_GP(max_substep psi)`，状态为 s5 committed。
  旧 E013 的 peak 名称不能单独证明多通道同状态；strict supervised target admission 需要
  独立 raw source timing/reduction audit 或同状态 Contract B。
- C0、fracture-history H、native GP 状态不在此 paired NPZ 内；不能由 alpha_bar 代替 H。
- `mean(f(alpha_bar_GP)) != f(mean(alpha_bar_GP))`；cell mean 的 f 不能直接从 cell mean
  alpha_bar 精确重建。同理 active-driver 的 GP product mean 不能用 mean parents 精确重建。
- U0.115 FEM 复用资格已记录，但此 frozen three-Umax export 没有 U0.115 PINN counterpart。
  FEM 单边完整不构成 paired training trajectory。

## 已执行的结果与决策

D003：12.55秒、11个既有外部文件 hashes 匹配、264个唯一配对cycle、1320个cycle-channel
rows，全部保留原 signed Delta；没有模型拟合。C1--20单列，strict pre-FEM-event 为261个
cycle；该数量不能代替尚未审核的双方common-pre-event数量。

| 描述量：各轨迹 pre-FEM-event 中位数 | U0.11 | U0.12 | U0.13 |
|---|---:|---:|---:|
| damage Delta 的相邻cycle spatial correlation | 0.9971 | 0.9926 | 0.9708 |
| alpha_bar Delta 的相邻cycle spatial correlation | 0.9989 | 0.9971 | 0.9948 |
| raw-log10 Delta 的相邻cycle spatial correlation | 0.8662 | 0.9072 | 0.8852 |
| 最多1%面积中的 history squared-error fraction | 95.19% | 94.43% | 94.79% |
| 最多1%面积中的 raw-linear squared-error fraction | >99.9999999% | >99.9999999% | >99.9999999% |

这些结果支持把**当前完整场+PINN自身历史**作为直接学习输入，而不是先压成99个scalar/POD
coefficient。它们不能证明 PINN 能预测 Delta：相邻相关使用了 FEM label，尤其 raw correlation
可能被固定稀疏峰值主导，不能拿它作为部署时可得的特征。

raw-linear 的幅度极集中，raw-log10 的error energy concentration只有约57--78%，说明loss
尺度会显著改变“学习什么”。方案使用预声明 transform/scaling，并同时报告linear physical
errors；不让一个 raw spike 决定所有通道loss，也不掩盖该spike。

Mapping-contained占98.6073%面积。fallback区域对raw-linear squared error贡献median仅
约1.6e-12--3.8e-12，对damage不足约0.12%；故此描述下的主差异不能简单归因于fallback。
未来still采用geometry-only clean domain，fallback单报，防止局部外推解释混乱。

PINN exported damage范围约[-0.000280,1.01856]，并存在逐cycle下降；它是当前导出field，
不能把这些计数直接称为 committed irreversible-history healing。FEM已经clipped，双方
处理不对称会影响Delta，formal data admission须保留native raw与processed field distinction。

决定：advance至配对数据/输入合同和具体direct-field protocol；shared NN、gradient conflict、
heldout增益均未建立。下一项最小工作是source timing/reduction与新增U0.115 PINN counterpart
availability审计，而不是等待confirmation来选择模型。

## Evidence pointers

最终D003 archive：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/`。
包含 `paired_cycle_index.csv`（264rows，不重复存大arrays）、`cycle_delta_metrics.csv`、
`pre_event_summary.csv`、`trajectory_coverage.csv`、`bounds_history_audit.csv`、
`nonlinear_reduction_audit.csv`、receipt、两张figure。
精简表见本目录 `evidence/`；[direct_learning_protocol.md](direct_learning_protocol.md) 给出下一实验。
旧D001/D002仅保留追溯，不作为最终science protocol。
