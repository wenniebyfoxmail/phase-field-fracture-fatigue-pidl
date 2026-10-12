---
storyline_id: S04
scope: direct_multivariable_delta_preparation
protocol_revision: proposal-v2-reduced-s4-terminal-20261012
status: g5_hold__matched_projection_and_field_export__method_only
claim_class: C2
evidence_domain: synthetic
---

# 直接学习逐 cycle 多变量 Delta：具体实验方案

> 2026-10-12 dated revision：proposal-v1见Git历史 `f00c743`；本版改为同状态s4的
> reduced-field直接Delta。fresh v10已正常结束且封存完整性通过，G5仍HOLD；U0.115
> 原生PINN acquisition已完成：503个连续checkpoint，raw steps0--502，c1--100的s4/s5齐全；
> model/history加载与有限性通过不等于paired qualification。U0.115的同状态投影、字段导出和
> deployable-input implementation仍待审查。G5/data-lock/D0唯一执行owner为主对话
> `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`；方法对话只修订文档。
> [复核与最小D0卡](g5_method_review_and_d0_card_20261012.md)为当前方法记录。
> [U0.115终态语义继承](u0115_terminal_semantics_method_review_20261012.md)记录最新覆盖与支持边界。

## 问题与对象

冻结原 PINN/PIDL。在同一状态 `(Umax, physical cycle, s4, post-history-commit)`，
预测外部 correction `Delta = declared FEM comparator - PINN`；用 `PINN + predicted Delta`
给出当前 corrected fields。一个 cycle 的**完整空间场**是一份样本，节点/cells 是其空间组成。
研究的是当前场纠正（C2），没有 future horizon；不把当前 cycle 的 FEM label 当部署输入。
网络直接输出空间 correction，不经 POD 系数瓶颈。最终 formal Experiment ID 在数据合同和
独立设计审核后注册；不占用已有实验 ID，也不改变 E013--E016 的 verdict。

首轮主评价通道为同状态s4的reduced `mean d, mean alpha_bar, mean psi_raw`；这里不把三者
称为独立物理状态。若matched `mean f`也获批，则直接预测其Delta的辅助head，单独报告，
不从 `f(mean alpha_bar)`生成它，也不重复计入主评价。记录 physical `Delta` 同时使用 raw driver 的稳定
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
| 同状态配对 | 从各自已锁定native support得到s4 reduced `d, alpha_bar, raw psi`，逐channel声明Q4 cell reduction和mapping | same-state reduced-field target admission；不自动获得native GP资格 |
| PINN U0.115 counterpart | 从已封存raw steps0--502导出c1--100 s4及因果history；核投影/字段/precision，不能宣称与103-cycle FEM完整配对 | 通过paired qualification后才新增development轴 |
| C0 身份/初始化 | 初始字段和首个 history window 的 missing mask | C0 用于初始化，不当作普通 cycle target |
| teacher/comparator role | 按 channel/regime 资格或 processed-imitation-only 声明 | 限定可支持的 scientific claim |

fresh U0.1175 v10已正常结束，terminal integrity通过；这只关闭执行/封存可用性。
主对话继续补同状态与空间表示清单。G5/data lock通过前，D0与NN保持HOLD；本方法对话
不执行资产准备、export、D0、训练或共享Obsidian更新。

development候选为U0.11/0.115/0.12/0.13。已锁定旧PINN exports只覆盖.11/.12/.13；
U0.115已取得原生PINN轨迹，但matched reduced export和projection资格尚未建立，不登记为
已齐的第四配对轴，不因此自动回退重算旧三条。该run的first raw step499=c100/s4；
stop raw step502=c101/s2，三次confirmation按raw steps计，不是三个physical cycles。
own-pre-event s4候选为c1--99；common-pre-event必须另与FEM event/state mask取交集。
PINN histories来自45591节点/90000三角单元，FEM来自86756节点/86408 Q4 cells及每cell4GP；
禁止逐索引相减。centroid sampling不自动等于cell integration，逐channel的projection与reduction
需要锁定。checkpoint history为post-commit，pre-refresh gradient diagnostics不能替代。
U0.125 exposure unknown继续关闭。U0.1175 confirmation scientific payload保持封存；
G5 owner提供data角色与paired lock前，不用于模型或特征选择。terminal integrity通过不能
替代confirmation PINN counterpart或paired semantics资格。

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
- input标准化和 raw `log1p(psi/s_raw)` scale只fit当前inner/outer-training PINN complete
  trajectories；`s_raw`来自这些PINN正raw-driver的area-weighted median，floor1e-12。
  Delta label scaling可以用training labels，但必须冻结并inverse，不能取confirmation统计量。
- Labels：matched FEM-PINN physical Delta；history 可用 `log1p(alpha_bar/0.5)` 的变换误差，
  raw 可用上述 `log1p` 误差，输出评估必须逆变换到 physical fields 并报告实际 Delta。
  该表示变换直接逐点学习，不是预测 POD coefficients。

每 batch 为一份完整 cycle field；内存不足时图按固定 tile 计算并保留 two-hop halo，核心
cells 恰好计分一次。不得把 tiles 当独立 trajectory 或混入 validation fold。

## 物理依赖与输出层

当前输出为**同状态s4的reduced-field correction heads**。`mean f`通过matched reduced
label直接辅助学习。exact active需native joint support：双方同一时刻/同一GP或已锁定
quadrature mapping上的 `d, psi_raw`以及该driver实际需要的其它parents共同可用，才能先
按声明driver定义算product再reduction；是否乘f由该定义决定。单独存在native d或raw、
只有nodal damage、或只有reduced parents都不满足这项前提。

cell reduction 上：`mean_GP(f(alpha_bar)) != f(mean_GP(alpha_bar))`，
`mean_GP(g(d)*psi) != g(mean_GP(d))*mean_GP(psi)`。本轮测得 FEM 的 f 重建差
约 0.0037--0.0058 area-RMSE median，PINN 对应差约 1e-8，说明双方 reduction 不同。

因此首轮不强制reduced f/active的exact-derived等式。mean f的直接辅助head体现reduced
output fidelity，与history同源相关，不能宣称独立物理闭合。active若只有reduced parents，
乘积近似仅作标明的diagnostic；matched exported mean-active若另获资格，可在后续protocol
中作为直接辅助target，首轮不自动增加。native-GP exact-derived路线需要独立锁定全部
parents的joint support、evaluator和reduction；不是本版默认路线。`H`是另一个history量，
missing时保留missing，不能由alpha_bar或一个current raw值补造。

所有方法同样报告 corrected field bounds、history/damage decreases、edge roughness、support。
保存未投影 predictions；任何后处理必须提前固定并同时报告前后结果，不能靠事后 clipping
获得通过。当前 FEM 本身未获 teacher 资格，因此不会把单个 bounds audit 自动当作物理闭合。

## 最小对照矩阵

| Arm | 输入/输出 | 作用 |
|---|---|---|
| B0 | 原 PINN，Delta=0 | 最基本纠正参照 |
| B1 | 同输入点特征 + 固定邻域均值 + globals + 两个 lags，闭式 ridge，直接预测reduced Delta；mean f如admitted作为额外辅助output | G5后的唯一最小D0对照，无 POD coefficients |
| N1 | 同输入、3 hidden layers × 64 units，shared pointwise MLP，3主通道head + matched mean f直接辅助head | 后续NN候选；当前未授权 |
| N2 | 相同输入/heads，2 message-passing layers ×64，2-hop graph，参数量与 N1 差 <=5% | 测局部空间信息的价值 |

B1 ridge alpha=`[1e-2,1,1e2]`，只在 whole-trajectory inner folds选；辅助mean f单列、不与
主通道重复投票。后续NN三主通道loss标准化后固定等权；mean f辅助loss权重必须在它的
独立training run card中提前锁定，不由本版暗含或在结果后调节。trajectory等权，
C1--20/C21--40/C41+的非空strata等权，每cycle再area weighting。
背景/局部 imbalance 由同一 PINN-only raw q99 mask 的 foreground/background 等权处理，
mask threshold 在该 cycle 的 PINN 上计算，所有 arms 一致，评估不复用该 mask 作 FEM oracle 输入。

首轮不加入 gradient surgery；选定 optimizer/loss/seeds 后记录各 head 对 shared encoder 的
gradient norm/cosine（每50 steps）和 per-channel validation error。若出现 reproducible
gradient interference，再立新优化策略对照；不在本矩阵结果之后追加 arm。

## 训练预算与模型选择

以下仅保留NN future设计上限，不能视为G5后的自动执行方案。G5通过后的唯一最小动作
是主对话负责的B0/B1闭式D0，详见独立D0卡；NN需要另一次reviewed run card。

- Producer：Taobo；launch 前核对 live GPU/VRAM、storage、shared-account 协议和 code review。
- Development：获批complete-Umax outer folds；只有U0.115 matched PINN通过后才可能4folds。
  N1/N2各seeds `[1,7,19]`，最多24fits是候选上限，不能据此宣布四轴齐全。
- Training：AdamW，lr=1e-3，weight decay=1e-4，max50 epochs；inner validation
  patience8。每个 arm/fold 的 epoch 先由 inner trajectories 选择，outer-heldout 不做 early stop。
- 每 fit 上限10 GPU-min；24 fits <=4 GPU-hours，最终 refit3 seeds <=30 GPU-min；
  总 wall/GPU 上限分别6h/4.5h，超限记 incomplete，不追加 GPU、epoch 或 seeds。
- 输出预算 <=2 GiB；保存 selected checkpoints、逐cycle scored metrics、固定field examples，
  不复制 producer 原始全量 fields。PIDL 原 producer 完全冻结。
- Development 选择：按已获批same-state reduced data上的worst主评价channel ratio排序；
  ties先N1再N2，三 seeds 全报告不挑最好 seed。最终选 arm 后冻结输入、loss、weights、
  epoch、checkpoint ensemble(mean)、scalers和reference-role，再一次性开confirmation。

## 判据、可达性与停止规则

拟议 bounded claim：selected direct Delta 是否在完整未见 Umax 上，使全部主评价通道都比
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

Secondary：每通道物理单位误差、mean f直接辅助head误差、worst-channel deterioration、
FEM support上的evaluation-only误差、event/censor、local support IoU、bounds/irreversibility、
成本和gradient trace。GP派生一致性仅在native joint support获批后评估，不套用到reduced heads。
本轮不画 hypervolume：没有固定参考点和未见模型结果，不能用它替代 primary。

## 最小 evidence / 当前状态

正式 experiment.md/data lock、exact-commit independent Code Ready review、每 fit Run receipt、
holdout predictions/metrics、immutable model-selection table、全部 seeds、两张图（per-channel
ratio与固定 heldout field panels）、README_analysis、独立 Evidence review。

当前：D003 descriptive evidence保留复用；fresh v10正常结束并封存；U0.115原生PINN已完成
且checkpoint有限性通过，G5仍为HOLD_MATCHED_PROJECTION_AND_FIELD_EXPORT。
同状态support、reduced export、deployable-input implementation与paired data lock待关闭。主对话
`01a1131d-017c-7b03-a95a-ad73ba8fcc9c`已接管G5/data-lock/D0唯一执行owner。
本方法工作树只维护设计记录，等待主对话批准data lock；不执行D0/NN或更新共享Obsidian。
