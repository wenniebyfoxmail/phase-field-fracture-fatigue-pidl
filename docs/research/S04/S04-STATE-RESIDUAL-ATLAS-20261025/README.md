# S04 既有档案的状态—残差图与下一路线卡

**状态：**只读综合，2026-10-25。

**目的：**把现有材料中可比较的 FEM 状态、残差语义和 PIDL 诊断分开，判断下一步应先处理约束/求解、状态闭合，还是局部表示。
**本次未做：**模型加载、训练、FEM 装配或求解、重新评分、资源预检、远程连接或 producer 作业。

这不是完整 PIDL 跨相位成绩表。它只汇总同一原生 Q4 残差语义下已经有完整目标态—直接前态—读回链的记录；缺失格子保持为空。E037 的已接受神经轨迹和 E038 的固定状态优化只作为分开的旁图来源，因为它们没有 E036 同义的空间残差字段和接受语义。

## 结论

现有证据首先指向两个必须保留的事实。

1. 原始 phase raw 力不能当作不可逆约束下的接受残差。八个已接受 F1 状态的 raw phase L2 都约为 7.36e-3 至 7.73e-3，但 nodal-box KKT 和保存的 F1 接受分数均满足原标准。这与 E036 对边界反力的分解一致：大量 raw 力是合法的约束反力。
2. 同一物理状态的数值求解路径会改变是否达到合格端点，甚至会产生不同的合格场。因而“接近某一 FEM 场”不能直接归因为网络容量，也不能把严格、F2 或 oracle 的非主参考端点（无论是否接受）改作主参考。

在这两个前提下，当前最有判别力的下一路线不是再做一次冻结 UV 头微校正，也不是直接扩大为状态条件网络或局部网络扫参。应先设计一个**状态参照的可行损伤—位移平衡分离比较**：从同一个已接受前态、同一个损伤提议和同一个首次固定系数出发，只改变 u/v 是否由离散平衡块闭合，随后显式复核投影后重建的 history/fatigue。它会回答剩余误差首先来自位移平衡闭合，还是仍需要状态输入/局部表示。

这是一张路线卡，不是运行授权。任何代码准备、资源预检或运行都需另行决定。

## 一、可比较的主图：F1 已接受状态

所有下表行来自同一轨迹 S04_E011_FEM_Q4_C120、Umax=0.12、同一 mesh hash、同一 post-commit 时点和同一主 F1 接受政策（u tol 1e-6，joint tol 4e-4）。每行都有目标态、直接已接受前态、原生残差证据和 checkpoint/readback 绑定。

| 状态 | 位移 | free-u L2 | phase raw free L2 | phase box-KKT L2 | 保存 F1 分数 | 解释 |
|---|---:|---:|---:|---:|---:|---|
| c1/s1 | 0.02999988 | 9.865e-7 | 7.728e-3 | 5.556e-6 | 0.9865 | 早期加载，已接受 |
| c1/s2 | 0.05999988 | 9.946e-7 | 7.701e-3 | 1.865e-5 | 0.9946 | 早期加载，已接受 |
| c1/s3 | 0.08999988 | 6.012e-7 | 7.651e-3 | 6.421e-6 | 0.6012 | 早期加载，已接受 |
| c83/s1 | 0.02999988 | 4.248e-9 | 7.376e-3 | 2.208e-5 | 0.0552 | 晚期加载，已接受 |
| c83/s2 | 0.05999988 | 6.756e-9 | 7.370e-3 | 2.162e-5 | 0.0541 | 晚期加载，已接受 |
| c83/s3 | 0.08999988 | 2.943e-8 | 7.360e-3 | 1.953e-5 | 0.0489 | 晚期加载，已接受 |
| c83/s4 | 0.11999988 | 2.981e-8 | 7.371e-3 | 2.841e-5 | 0.0711 | 晚期峰值，已接受 |
| c83/s5 | 0 | 1.155e-17 | 7.377e-3 | 2.396e-5 | 0.0599 | 晚期卸载，已接受 |

“保存 F1 分数”沿用原记录，阈值内即接受；它不是可与 raw phase L2 相互替换的连续误差。表中数值逐行来自 c1 已发布前缀和 c83 完整窗口的 admission 记录，未重算。

可作同载荷早/晚配对的只有 c1/s1↔c83/s1、c1/s2↔c83/s2 和 c1/s3↔c83/s3。c83/s4 与 c83/s5 保留为晚期峰值/卸载锚点；它们没有可比较的 c1 对应项。

### 这张图能说明什么

- 早期 c1 的 free-u residual 靠近原 1e-6 接受线；晚期 c83 的同一量级低约一至两个数量级。这个差异是真实的状态依赖信号。
- raw phase 力在早、晚和卸载态都保持在近似同一量级，box-KKT 却较小并通过接受。因此 raw phase 力更像含边界反力的诊断量，不能被标为“早期比晚期更不收敛”。
- c83/s5 的机械残差近零，提供一个可用的卸载相位参照；但目前没有 c1/s5 对应行，不能由此估计“加载/卸载平均规律”。

### 这张图不能说明什么

- 它没有中期、过渡期和完整早期卸载覆盖。c20/c60 的问题发生在 s3 前态准入，不是可标成 c20/s4 或 c60/s4 的求解残差。
- 它不是 PIDL 对 FEM 的跨相位误差曲线。F1 行是已接受 FEM 主参考；它们没有对应的一整条已接受 PIDL 候选轨迹。
- 它不能把 residual 的差异分配为优化、状态语义或网络表达能力的百分比。

后续若从保存的 ru/rd 画空间图，机械残差必须使用同一 free-DOF/BC 掩膜；不能把受约束节点上的反力画成自由机械残差。每行还要保留自身的 d_old、old history、active driver、f_solve 和 f_commit。f_commit 不能替代实际求解时的 f_solve，也不能借用目标态或另一支路的前态。

## 二、PIDL 可叠加的诊断，以及必须保留的空格

| 材料 | 可以安全使用的事实 | 不能做的事 |
|---|---|---|
| D3 c1 评分（最新 2026-10-25） | c1/s1 的 P1、P2 在等工作 2000 更新后终态 J 都是 9.26481e-4；其 fresh free-u 为 2.70184e-3、phase box-KKT 为 6.64920e-2，未接受或提交 | 十个优化块不是十个物理相位；不能将它们画成跨相位轨迹 |
| D3 c1 评分的完成记录 | 14 个回收文件经大小/SHA 核验，任务 exit 0，但 verified accepted endpoint pairs 为 0 | 不能把“评分完成”改写成“已有有效 PIDL 端点” |
| E037 R001 原始神经臂 | 有 c1--c3、15 个已接受神经状态及其自身的聚合指标 | 使用独立 45,591-node/90,000-GP 网格与神经求解语义，没有 E036 同义 ru/rd；不能同轴排名或逐点比较 |
| P0 的 12 个存档场 | 已有 u/v/d 可作场差或可视化材料 | 没有原 solver 残差、完整前态链和时序字段，不能补到主残差表 |
| E034 的 F8/F802 | 冻结 c20/s4、UV 头、半径和零 slack 配方没有产生接受点 | 不能外推为全网络、状态表示或损伤表示无解 |

因此本文件的正式名称是**“F1 跨相位状态—残差与已到达 PIDL 候选诊断”**，而不是“完整 PIDL 跨相位图”。

## 三、已有机制证据的归位

| 问题 | 已有直接证据 | 当前判断 |
|---|---|---|
| 约束与求解 | c1/s2 等状态的 raw phase 力主要是边界反力；c1/s4 的 F2 约束求解在同前态下通过，而主 F1/strict 的原算法可失败 | 有直接机制证据；应首先隔离 |
| 参考/数值端点选择 | c1/s2 节点 oracle 通过普通残差却没有靠近主 F1 场 | 参考场距离不能单独定义“网络误差” |
| 状态语义与时序 | c1/s1 P1/P2 的有限比较没有形成接受端点；已有晚期疲劳时点差异也未形成接受改进 | 尚未判定；必须在匹配前态下测试 |
| 局部表示 | 晚期局部损伤误差存在集中现象；E040 的 q-local 与 global 可行轨迹出现不同损伤场 | 可能重要，但尚无同状态物理/FEM 对照，不能优先归因 |
| 参数正则和数值步长 | E038 在两个局部卸载态显示 RPROP 上限可消除无 L2 参数爆涨 | 是数值稳定性证据，不是全轨迹物理收敛证据 |

E037 的原始对照臂完成了自己的 15 子步神经路径，但三个新方法记录的失败层级不同：最早的 AL 启动在首次前向前因 CPU/CUDA 混用退出；R1 在第一物理子步的能量定义域检查停止；R2 留下一份有限却未接受的 c1/s1 试探场。它们不能被合并成“不可逆约束方法失败”的一般结论。相反，E040 已显示状态参照的前向可行损伤映射可以完成固定 15 子步的两条合成路径；q-local 确实被激活，但尚无 FEM/物理一致性或局部表示收益验证，故只作为可行性先例。

## 四、下一条可审阅路线：状态参照的可行损伤—平衡分离比较

### 问题

在已知、匹配的前态下，若损伤先由严格可行的状态参照映射产生，将同一 d 候选投影到离散 u/v 平衡后，哪些误差会在不泄漏 FEM 目标的条件下同时改善？这首先是 equilibrium-projection audit，不预设“u/v 一定是主瓶颈”。

### 最小、可比的状态选择

只选现有 F1 主图中都满足下列条件的两个加载态：

- c1/s2：早期、U=0.05999988、直接前态 c1/s1 已接受；
- c83/s2：晚期、同一 U、直接前态 c83/s1 已接受。

它们避免把 c1/s4 缺失、c20/c60 前态准入失败或 strict/F2/oracle 的不同角色混进主比较。

### 设计的两臂

| 臂 | 共用内容 | 唯一改变 |
|---|---|---|
| A：可行全局 PIDL | 相同初始权重、直接前态 d_old/H_old、fatigue 时序、边界、q 参照、采样和停止规则 | u/v 仍由网络输出 |
| B：平衡投影审计臂 | 与 A 的 q、前态、损伤映射和第一次固定系数求解逐项相同 | 给定当前可行 d 后，u/v 由同一 Q4 机械平衡块闭合，而不是由网络头直接给出 |

这里的 B 不是把 FEM 目标场灌入网络，也不是用 oracle/F2 替换主 F1。它只把同一候选状态中的位移平衡作为一个单独机制处理。B 的 free-u residual 降低本身是投影的构造结果，不能单独证明网络 u/v 是主因。

每个状态的审计顺序必须固定为：

1. 从同一已接受前态生成相同的 q 和严格可行 d；逐数组核对 A/B 的 d、d_old、old history 和固定 solve 系数相同。
2. 在不读取 F1/strict/oracle 目标场的条件下，对 B 的固定 d 求 u/v 平衡；A 保留其网络 u/v。
3. 对两臂都从各自当前场和同一旧态独立重建 active/history 与 f_commit，重新计算 phase box-KKT、反力和 field 读数；不提交 history。

这样会明确区分“固定系数下的机械投影”与“投影后的 fresh 状态一致性”。如果投影改变了 active/history 或 fatigue，就必须报告该差异；不能继续声称 A/B 使用相同的 current history/fatigue。

### 固定记录与停止条件

- 每个候选都必须记录目标态、直接前态、d_old、H_old、A/f 的 solve 与 commit 时点、mesh/BC/free-DOF、残差算子版本和所有来源 SHA。
- 原生 free-u、phase raw、nodal-box KKT、边界可行性、history 一致性和反力要分栏保存；不把其中任何一个换成另一个。
- 最终物理接受沿用该状态的主 F1 政策。若另加 field/raw/reaction 目标，必须在新卡中声明为独立评分；F1 只在求解完成后作锁定的评分参考，绝不进入 B 的求解或初猜。不能把 E034 的 c20/s4 保护偷换到 c1/c83。
- 任一状态身份不匹配、候选不有限、不满足损伤可行性或没有通过 fresh 验收，即停止该依赖链；不替换参考、权重、状态或 GPU，也不自动重试。
- 本路线目前没有资源预算或运行授权。旧 E034 预算与剩余资源不是新实验的授权。

### 预先规定的读法

| 观察 | 仅能支持的结论 | 再下一步 |
|---|---|---|
| B 在两态都 fresh 通过，且相对 A 在预先锁定的、求解后才对主 F1 评分的 field/reaction 以及 phase-KKT、history-consistency 读数上同步改善 | 直接网络 u/v 闭合是可干预因素之一；仍不是唯一因果归因 | 再准备受约束 equilibrium-eliminated / hybrid 路线 |
| B 通过物理验收但不稳定地靠近匹配 F1，且不同合格 FEM 端点仍有明显场差 | endpoint selection / 参考条件性未决 | 先设计参考选择与初猜敏感性判别，不归咎 state/damage 表示 |
| B 的 fresh phase-KKT、history 或 fatigue 一致性失败，或 d 身份/可行性不能锁住 | 映射、优化器或状态时序仍未闭合 | 先审计状态包与投影顺序，不做容量扫参 |
| 在 B fresh 通过后，自由机械/box-KKT 之外的预注册 field 或 reaction 误差仍在同一裂纹或边界邻域持续集中 | 局部表示成为可检验假设 | 再比较 BC-safe q-local enrichment |

## 五、证据入口

- [c1 F1 已发布前缀](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/fem_main_c1_published_prefix_20261023/partial_targets.json>)
- [c83 F1 完整窗口](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/fem_main_c83_completed_20261023/targets.json>)
- [最新 D3 c1 正式评分](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/d3_c1_formal_scoring_20261025.json>)
- [FEM 主窗口结局](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/fem_main_outcomes_20261023.md>)
- [E036 差距归因综合](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/gap_attribution_interim_20261024.md>)
- [c1/s2 节点 oracle 对照](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022/analysis/c1s2_nodal_oracle_comparison_20261024.md>)
- [E037 原始对照与原始对偶尝试](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E037/analysis/README_analysis.md>)
- [E037 R2 有限但未接受诊断](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E037/analysis_r2/README_analysis.md>)
- [E038 RPROP 上限对照](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E038/analysis/README_analysis.md>)
- [E040 可行损伤表示结果](</Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/s04-e040-feasible-damage-20261024/docs/research/S04/S04-E040/experiment.md>)
