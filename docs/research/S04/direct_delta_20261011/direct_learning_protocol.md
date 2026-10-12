---
storyline_id: S04
scope: direct_multivariable_delta_preparation
protocol_revision: proposal-v1-20261011
status: design_concrete__data_admission_pending__training_not_launched
claim_class: C2
evidence_domain: synthetic
---

# 直接学习逐 cycle 多变量 Delta：具体实验方案

> 2026-10-12 方法修订：以下proposal-v1保留为历史设计；当前native/reduced-head选择、
> D0 activation与唯一owner以[g5_method_review_and_d0_card_20261012.md](g5_method_review_and_d0_card_20261012.md)
> 为准。G5当前HOLD，本方法对话不重复D003/D0、不导出Windows scientific payload、不启动NN。

## 问题与对象

冻结原 PINN/PIDL。在同一状态 `(Umax, physical cycle, s4, post-history-commit)`，
预测外部 correction `Delta = declared FEM comparator - PINN`；用 `PINN + predicted Delta`
给出当前 corrected fields。一个 cycle 的**完整空间场**是一份样本，节点/cells 是其空间组成。
研究的是当前场纠正（C2），没有 future horizon；不把当前 cycle 的 FEM label 当部署输入。
网络直接输出空间 correction，不经 POD 系数瓶颈。最终 formal Experiment ID 在数据合同和
独立设计审核后注册；不占用已有实验 ID，也不改变 E013--E016 的 verdict。

初始独立目标为 `d, alpha_bar, psi_raw`。记录 physical `Delta` 同时使用 raw driver 的稳定
变换损失；loss-space Delta 与 physical Delta 各自明确命名。`H` 与 fatigue `alpha_bar` 不同，
只有双方导出同定义、同位置、同 timing 的 H 时才加入；首轮不增加未可用 target。

旧 E015 的 coefficient ridge 负结果保持。直接场学习的输入包括完整 local field、邻域、
过去 PINN state 和全局 summaries，属于修订的信息/表示合同；需要新协议审查。旧结果
不要求“ridge 必须先科学 PASS 才可试 NN”，但 NN 必须与最简单的同输入基线公平比较。

## 数据合同与第一项可执行工作

已有诊断表：264 cycles × 86,408 Q4 cells，三条 Umax，仅支持 processed cycle-summary
对 PINN peak 的描述。**不把这些 rows 直接批准为 strict same-state training labels。**
正式训练前用如下配对流程关闭区别：

| 任务 | 最小输出 | 通过后用途 |
|---|---|---|
| 查旧三条 FEM cycle MAT 的 source timing | 各通道 s4/s5、GP reduction、clipping、source commit 的逐字段表 | 明确 cycle-summary imitation 与 native same-state 分开 |
| 同状态配对 | s4 nodal/GP `d, alpha_bar, raw psi` 与 PINN 同 peak checkpoint，统一 Q4 evaluator | strict same-state target admission |
| PINN U0.115 counterpart | 从已有匹配 checkpoint 做只读 export；不存在则记 missing，不启动训练补轨迹 | 新 development Umax 轴 |
| C0 身份/初始化 | 初始字段和首个 history window 的 missing mask | C0 用于初始化，不当作普通 cycle target |
| teacher/comparator role | 按 channel/regime 资格或 processed-imitation-only 声明 | 限定可支持的 scientific claim |

这些是新的配对准备任务，不需要等待 U0.1175 完成才能进行 development 诊断；但本轮范围
仅现有本地 archive，未发远程 export 请求或执行 GPU/FEM。

完整 trajectories 分组：U0.11/0.115/0.12/0.13 作 development，U0.115 paired audit 未过则
不进入训练。U0.125 exposure unknown 继续关闭。U0.1175 confirmation scientific payload
保持封存；外部 owner 完成 acquisition/integrity qualification 后，再按冻结规则配对其 PINN
输出。此处缺少 confirmation PINN counterpart receipt，因此 confirmation 目前也未 ready。

训练与主评价用双方 first-event **之前的共同 matched s4 states**；own-event/censor 单列。
旧诊断的 pre-FEM-event 261 cycles 还不是已审计的 common-pre-event 集，因为本包缺少逐轨迹
PINN event-admission 表。不得用 nominal cycle 强行对齐 event；不得用 FEM event 归一化输入。

## 每个完整 cycle 输入与标签

`X_c = [x,y, area, Umax, load factor, c/100, PINN current fields,
PINN fields at c-1,c-2, lag masks, PINN global summaries]`。

- current fields：d、alpha_bar、f、raw psi 与明确语义的 PINN active proxy；全部来自 PINN。
- 历史：只用当前/过去 cycle。c1/c2 用真实 C0 或 missing masks；禁止未来 padding。
- global summaries：每通道 area mean/std/q90/q99，仅由 PINN 计算；各 arm 相同。
- 邻域：固定几何 Q4 edge graph，同周期 PINN fields；禁止 FEM support/process zone 定位。
- Mapping：本包 1.3927% 面积用了 triangle fallback。formal main comparison domain 固定为
  geometry-only contained cells；fallback 单独报告，先核对其是域不重合还是映射外推。
  图上的 native全域数值与正式 clean comparison-domain score 不混用。
- 标准化和 raw `log1p(psi/s_raw)` scale 仅由 outer-training complete trajectories 决定，
  `s_raw` 为它们正 raw-driver 的 area-weighted median，带固定 1e-12 floor。
- Labels：matched FEM-PINN physical Delta；history 可用 `log1p(alpha_bar/0.5)` 的变换误差，
  raw 可用上述 `log1p` 误差，输出评估必须逆变换到 physical fields 并报告实际 Delta。
  该表示变换直接逐点学习，不是预测 POD coefficients。

每 batch 为一份完整 cycle field；内存不足时图按固定 tile 计算并保留 two-hop halo，核心
cells 恰好计分一次。不得把 tiles 当独立 trajectory 或混入 validation fold。

## 物理依赖与输出层

原生 GP 上：`alpha_bar_GP -> f_GP`；`d_GP, psi_raw_GP -> g(d_GP)*psi_raw_GP`。
是否乘 f 由具体 driver 定义决定，不统一称 active。`H=max(previous H, declared psi)`
是独立 history update，不能从当前 cycle summary 反推。

cell reduction 上：`mean_GP(f(alpha_bar)) != f(mean_GP(alpha_bar))`，
`mean_GP(g(d)*psi) != g(mean_GP(d))*mean_GP(psi)`。本轮测得 FEM 的 f 重建差
约 0.0037--0.0058 area-RMSE median，PINN 对应差约 1e-8，说明双方 reduction 不同。

因此首轮在同状态、同空间 support 上学习 primitive targets。若 native GP targets 可用，
从 corrected primitives 在 GP 上重算派生 f/active，再按合同 reduction；若只有 cell means，
f/active 仅作为单列 archive output fidelity，不强制错误的精确派生等式、不加入独立 primary。
如需 f 额外 cell head，需明确是 unresolved subcell variation 的辅助输出，并作为协议修订。

所有方法同样报告 corrected field bounds、history/damage decreases、edge roughness、support。
保存未投影 predictions；任何后处理必须提前固定并同时报告前后结果，不能靠事后 clipping
获得通过。当前 FEM 本身未获 teacher 资格，因此不会把单个 bounds audit 自动当作物理闭合。

## 最小对照矩阵

| Arm | 输入/输出 | 作用 |
|---|---|---|
| B0 | 原 PINN，Delta=0 | 最基本纠正参照 |
| B1 | 同输入点特征 + 固定邻域均值 + globals + 两个 lags，闭式 ridge，直接预测逐点 Delta | 简单线性 comparator，无 POD coefficients |
| N1 | 同输入、3 hidden layers × 64 units，shared pointwise MLP，3 heads | 测直接非线性场映射 |
| N2 | 相同输入/heads，2 message-passing layers ×64，2-hop graph，参数量与 N1 差 <=5% | 测局部空间信息的价值 |

B1 ridge alpha=`[1e-2,1,1e2]`，只在 whole-trajectory inner folds 选。三项 loss 标准化后
固定等权；trajectory 等权，C1--20/C21--40/C41+ 的非空 strata 等权，每 cycle 再 area weighting。
背景/局部 imbalance 由同一 PINN-only raw q99 mask 的 foreground/background 等权处理，
mask threshold 在该 cycle 的 PINN 上计算，所有 arms 一致，评估不复用该 mask 作 FEM oracle 输入。

首轮不加入 gradient surgery；选定 optimizer/loss/seeds 后记录各 head 对 shared encoder 的
gradient norm/cosine（每50 steps）和 per-channel validation error。若出现 reproducible
gradient interference，再立新优化策略对照；不在本矩阵结果之后追加 arm。

## 训练预算与模型选择

这是可审核的 future run card；本轮没有 training authority/launch。

- Producer：Taobo；launch 前核对 live GPU/VRAM、storage、shared-account 协议和 code review。
- Development：最多4个 complete-Umax outer folds，N1/N2 各 seeds `[1,7,19]`，最多24 fits。
- Training：AdamW，lr=1e-3，weight decay=1e-4，max50 epochs；inner validation
  patience8。每个 arm/fold 的 epoch 先由 inner trajectories 选择，outer-heldout 不做 early stop。
- 每 fit 上限10 GPU-min；24 fits <=4 GPU-hours，最终 refit3 seeds <=30 GPU-min；
  总 wall/GPU 上限分别6h/4.5h，超限记 incomplete，不追加 GPU、epoch 或 seeds。
- 输出预算 <=2 GiB；保存 selected checkpoints、逐cycle scored metrics、固定field examples，
  不复制 producer 原始全量 fields。PIDL 原 producer 完全冻结。
- Development 选择：按 paired native data 上的 worst independent-channel ratio 排序；
  ties先N1再N2，三 seeds 全报告不挑最好 seed。最终选 arm 后冻结输入、loss、weights、
  epoch、checkpoint ensemble(mean)、scalers和reference-role，再一次性开confirmation。

## 判据、可达性与停止规则

拟议 bounded claim：selected direct Delta 是否在完整未见 Umax 上，使全部独立目标都比
最佳简单部署基线有实际增益？最简单基线按 development inner validation 从 B0/B1 选定，
confirmation 不能事后切换 comparator。

拟议 primary：对 d、history-transform、raw-transform 各算 stratified support-balanced
area-RMSE 的 candidate/comparator ratio，然后取最大值 W；单一主判据为 W 的
moving-block-bootstrap 97.5% upper `<0.90`（block5，2000 repeats，seed20261011）。
即最差通道也至少改善10%；bootstrap 仅是该有限非平稳轨迹的条件性描述，不当人口置信度。
所有 channel/cycle 表为原始权威值，图不投票。

10%来自旧 residual practical margin，**目前还不是 Ready gate**：必须在新增配对开发数据上
估计 reference uncertainty、baseline variation、oracle/replay ceiling，证明阈值可达后经独立
审核冻结。若不支持10% margin，在看confirmation前改成明确 diagnostic estimand，不能看
结果后放宽。reference role/same-state/完整分组/输入隔离/finite 是必要 validity gates。

开发中 NN 没有超过简单 baseline：保留直接学习负结果，不转 PCGrad 或扩大模型；先看
负结果位于哪一通道、support、state timing、输入信息或训练优化。只有 ridge 失败而 NN
尚未测试不能终止直接非线性路线。confirmation primary miss 后不调weights、不增加arm、
不打开 U0.125。通过至多支持该 reference role 的 synthetic post-hoc field correction。

Secondary：每通道物理单位误差、worst-channel deterioration、FEM support上的evaluation-only
误差、event/censor、local support IoU、bounds/irreversibility/GP派生一致性、成本、gradient trace。
本轮不画 hypervolume：没有固定参考点和未见模型结果，不能用它替代 primary。

## 最小 evidence / 当前状态

正式 experiment.md/data lock、exact-commit independent Code Ready review、每 fit Run receipt、
holdout predictions/metrics、immutable model-selection table、全部 seeds、两张图（per-channel
ratio与固定 heldout field panels）、README_analysis、独立 Evidence review。

当前：descriptive diagnostic completed；direct-learning design written；same-state paired data、
C0/role/新增development counterpart admission pending；训练未启动。下一可执行动作是本地旧
三轨迹的逐字段 timing audit 和 existing PINN checkpoint availability audit；不涉及 fresh v10
Windows 输出/控制目录。
