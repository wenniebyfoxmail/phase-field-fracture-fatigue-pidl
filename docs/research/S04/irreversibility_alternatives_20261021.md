# PIDL 不可逆约束替代：路线与本地算子准备

> 当前入口（2026-10-22 管理更新）：active D3。合法前态、完整 runner 和原 L2 已补齐；首次启动在前向阶段技术退出，未优化或求解 QP；设备修复 `a706d168` 的独立定向复查已完成，仍等待此前已提出的重启许可。见 [首次启动记录](S04-E037/result_20261022.md)。本次只更新当前验证流程，不启动、重启或停止科学运行。

## 当前执行计划：只跑固定基准，通过即交付

依据安装版 [research-decision-core / 只跑固定基准，通过即交付](/Users/wenxiaofang/.codex/skills/research-decision-core/SKILL.md) 与 [agent_bootstrap](/Users/wenxiaofang/.codex/skills/research-decision-core/references/agent_bootstrap.md) 的 2026-10-22 用户更新。以下规则前瞻性替代本任务中 Agent 自加的重复检查安排；已执行日志、签名复查、原失败和冻结科学协议原样保留。

**唯一固定任务基准：复用已有 S04-E037 r1 单态端到端用例。** 代表性输入为已锁定的真实恢复后 `checkpoint0` / `trained_1NN_0`，下一加载 `c1/s1, U=.03`；共同缓存 u/v、固定 h/f、完整 weights-only L2。对照仍为 P*/G/N 三臂及 G/N 条件场参照，配置、输入哈希、科学阈值和预算仍以 [原协议](S04-E037/protocol.md)、[config](S04-E037/config.json)、[input_lock](S04-E037/input_lock.json) 为准。它是原任务已有的单个代表性用例，不是把 31/34 项旧测试重新命名为基准。

获准执行后，在同一 Taobo 上按既有启动入口运行一次；下面仅登记命令模板，本次不执行。`AL_TASKROOT` 必须指向获准后的全新自有目录，不能复用第一次失败目录；当前候选源仍是 `a706d168f0e89108d8dcb7f45e8a458730c40e59`。

```sh
: "${AL_TASKROOT:?先绑定获准后的全新自有目录}"
AL_SOURCE_COMMIT=a706d168f0e89108d8dcb7f45e8a458730c40e59 \
bash "$AL_TASKROOT/code/docs/research/S04/S04-E037/producer_launch.sh"
```

预期产物：同一保存端点的三臂字段、乘子、目标分量、调用与耗时、参数/约束证书及两组条件参照的真实状态。必须如实执行原 primal、NCP、参数驻点与参考 KKT 判据；某项不达标仍按原判据保留负面或未定结果，不通过重跑、补种子或改阈值使其变为成功。数值阈值通过不外推为联合平衡、轨迹或 FEM 复现。

当前基准结果：首次运行只到初始前向就退出，尚无可分析科学结果；设备失败项已修复，相关 6 项有限性/设备合成检查和已完成组件结果直接复用。真实端到端修复效果尚未再次执行，本管理更新不把它写成通过。

**从当前待办移除的重复环节：**

- 不再把完整微测集合、本地再跑一遍、producer 再跑一遍设为每次代码更新或启动的连续门槛；不另加全量回归、旧历史重跑或 smoke 阶梯。
- 不因正式实验身份、改 commit、路径、哈希或元数据变化自动复审；这些小改只核直接一致性。
- 删除 Agent 在原模板中追加的“计算后必须再找独立 reviewer”安排。保存数组的既定分析和原科学判据仍需执行，它们不是新增审核轮次。
- 固定基准通过即交付对应结论；代码失败只修复并重跑受影响的失败项，复用未受影响的通过结果。科学失败不是自动重启授权，仍受原执行许可、已发生尝试及预算限制。

**保留用户明确要求的独立复查：** 原指令为“继续推进 AL 路线，把合法的共同前态、完整 runner 和验证方案补齐，保留原 L2。独立复查后进行。计算”。因此本次计算前复查有直接用户依据；已有首次复查、撤回可执行性判断及设备修复定向复查记录继续有效地记录各自范围，不抹去遗漏，也不把该指令扩张为每次 commit 或每次元数据变更都复审。当前修复的这一复查已完成，不为本次管理编辑再派审核。

执行边界保持：原六态 h>1 未执行且不裁剪；不扩展数据/状态/算法；原总 ≤2 GPUh、单次启动记录及待重启许可状态不变。共享机器安全与实际启动身份/资源检查保留。本次不改共享 Roadmap。

### 以下为原历史方案与执行记录


日期：2026-10-21；owner：PIDL irreversibility alternatives；探索阶段，active D2。
目标：保留损伤不能愈合，区分有限罚近似、神经表示、优化与历史提交问题；为受控 FEM/PIDL 比较选择替代方法。
本任务从 FYR meeting preparation 分出，不修改已提交报告，也不接管已在推进的 FEM–神经混合路线。

**当前判断：优先准备原网络上的不等式增广拉格朗日（AL），保留 weights-only L2；直接节点/GP 约束求解只作条件诊断参照。** 这是一项候选选择，不是已证实的性能改进。旧 sigmoid-floor 负结果保留，但其状态刷新与全峰值协议使它不能排除其他硬约束。新 kernel 未接入训练；本轮只读来源、核对既有日志和执行纯代数单测。

## 1. 作用域、隔离与复用决定

- 授权：来源核查、方案比较、本地必要实现、轻量静态/合成单测；无训练、新 FEM 求解、holdout、producer、科学重试或其他预算继承。
- 分支 `codex/pidl-irreversibility-alternatives-20261021`；工作树 `worktrees/pidl-irreversibility-alternatives-20261021`；基点为本地已知远端 `origin/main` 的明确提交 `389f618b7a042e0a4e4d11a3ab24a7164f6902cc`，本轮未 fetch。该基点是隔离开发载体，**不是正式历史算例版本**。
- 正式历史源始终是 `e9dc2632457f5f566db95c75b856ad96170fd0e6`。未把新模块接进旧基点的训练流程，未覆盖共享 checkout，未推送。
- D1 范围：用户给出的 FYR §12–13/JSON、指定提交、旧 hardirr 本地代码与日志、S04-E011/E004 代码/协议/结果、已有 Obsidian 重构报告与论文库。未重评分 checkpoint/科学数组。
- 复用决定：**continue** 已有 S04 的约束/残差判断；为纯神经不可逆替代增加独立算子。已有 active-set/QP 求解器不另写一份；已有四态 fixed-u repair 不重做。

| 决策步 | 要回答什么 | 当前状态／转向条件 |
|---|---|---|
| D1 既有工作 | 哪些结果与算子可复用 | 已完成；保留旧负结果与 E004 运行前停止 |
| D2 约束与状态合同 | 不改 L2 时，哪种方法允许活动约束与可解释最优性 | 当前；AL 候选、独立 kernel 与反例单测，不是完整 runner |
| D3 多状态受控比较 | 近似误差、参数驻点、场驻点是否可分开 | 待精确合法输入、集成代码/复核和该次运行授权 |
| D4 连续加载卸载 | 改善是否传到联合场与轨迹，而非单步 loss | 后续方案；D3 不自动授权 D4 |

## 2. 已核对的现状与新发现

### 正式历史目标和状态

`e9dc263:source/fit.py:473–483,637–646`：

\[
L_P(\theta)=\log_{10}(E_{el}+E_d+E_{hist})+10^{-5}\sum_{name\ contains\ weight}W^2.
\]

不包含 bias/激活系数的同义 L2；不把 optimizer 的 weight_decay=0 当作没有这项。`source/compute_energy.py:129–149,221–237` 的正式选项为三点三角形 GP 上的负增量平方，非先均值后取负部。

模型设置位于项目根 `Baseline/PIDL_hard_d1_u0_recovery_5step/Umax_0.12/original_case/raw/run/model_settings.txt`：Umax=.12，seed1，8×400，step0 是 U=0 恢复；每循环因子 [.25,.5,.75,1,0]。物理 cN 峰值文件步 `1+5(N−1)+3`，卸载 `1+5(N−1)+4`。初始 current alpha 被拟合到1但旧 histories 独立保留，不能把这个 current 初猜当作全域不可逆下界。

Manav 2024 §3.2.4/§4.1/Appendix D 解释 L2 用于约束有限积分不能解析的尖锐位移变化与伪低能量解；不是仅有标签过拟合的解释。该论文不证明此系数在我们的疲劳算例最优。本任务保留 L2，和另一项 L2 专题不混合。

### 旧 hardirr：负结果有范围，新状态问题有静态证据

源提交 `41e0bf1c4f1c9de780e0fc54642e110f3d8e459b` 增加 floor 与 Ehist 权重0；`6525a9fe051abbc34cf383a2ff69c08c816f0a48` 改用真正 sigmoid。已比较本地 archive 的 field/model_train/config 与后者逐字节一致。

本地来源根：项目根 `local_archive/taobo_remote_gap_census_20260627/raw_remote/phase-field-pidl-hardirr-6525a9f/`。对应日志 `SENS_tensile/logs/baseline_N100_hardirr_resume_gpu2_20260525_082825.log:417–421` 与 `v4_N100_hardirr_resume_gpu6_20260525_082825.log:519–524`，和 `upload code/docs/sidecar_true_adaptive_sampling_runs.md:89–99` 一致：两臂到c99未记录断裂，疲劳累计量最大值75.481/75.969、Kt10.64/10.73。这里的累计量不是 damage alpha。

这是 seed1 的 N5→N20→N100 恢复链，baseline/v4 都用 hard floor，且 config:453/464 为每步峰值加载。不是当前五子步对照；完整现代 receipt 未找到，未核 checkpoint 张量、断裂判据或饱和率。

**新核对的源码问题：**旧 `field_computation.py:212–220,251–263` 用 `a=h+(1-h)s`；`model_train.py:1262–1263` 接受 a 并设置新 floor，`:1301–1308` 又以前述网络 raw 计算 fatigue 场。于是

\[
a'=a+(1-a)s,\qquad a'-a=(1-h)s(1-s).
\]

除端点等情况，后续评估不是刚优化的场。此为静态代数事实，尚未量化旧轨迹的实际增量，**不能认定它导致旧停滞**。新方法必须缓存同一 accepted field；同一步的能量、driver、保存、历史提交都消费这份场；不在内迭代滚动旧下界。

其他竞争解释：有限 raw 的 sigmoid 不能精确表示 a=h；导数 `(1-h)s(1-s)` 可小，但 RPROP 按符号更新，小梯度幅值本身不是失败证据；旧方法锁住整个初始弥散 profile，需核对其与参考的兼容性；floor 仅按向量长度匹配，长度变化会跳过、同长度重排不会识别，不能宣称全域保证。

### S04 里已有三类不同的直接 damage 问题

以下来源在已核对工作树 `.codex/worktrees/s04-c1-uv-energy-head-20261018`（HEAD `afd50343d2eb8eb971bbbe6ea2077c0d9e2b36f5`）：

| 路线 | 实际目标/域 | 复用与限制 |
|---|---|---|
| E011 PBD Direct-Q4 | 固定u/f，Eel+Ed+Ehist，节点[0,1] | `pidl_block_diagnosis_protocol_20261017.md:55–70` 明确不是硬不可逆；不可将其box残差当去罚KKT |
| E011 constrained damage | 节点 d_old≤d≤1，保留原生GP罚/trial-f | `constrained_damage/e011_damage_solve.m` 有活动集释放和自然残差线搜索；四态 fixed-u repair 成功，之后机械残差仍非零，有时更差 |
| E004 native Q4 QP | 固定u/f，去罚，节点box＋GP `N d≥d_old_GP` | `source/native_q4_damage_qp.py` 的组装/完整KKT证书可复用；旧科学状态 `stopped-before-run; A1-trial-f-rejected` 原样保留 |

E011 `runs/pidl_block_result_20261017.md` 还报告旧 PIDL hist_alpha 超过1（c1/c20 node max≈1.000202/1.000335，部分GP也>1）。这些不是本轮正式T3包重评分，但足以提醒：**先核输入可行性；若 h>1，则 h≤d≤1 无解。禁止默默clip h、替换来源或沿旧预算跑。**

已有 fixed-u repair 的合法下界反力使 raw damage residual 非零；要求其全部归零会错判。网络参数 `Jᵀr` 小也不保证场 r/KKT 小；当前还有 L2 的额外参数梯度。各分量范数接近不证明方向抵消。

## 3. 三条路线与各自假设

令物理去罚能量 `E0=Eel+Ed`，接受旧场 h 固定。节点空间可行集 K={h≤d≤1}；GP 空间为 {N_gp d≥h_gp, 0≤d≤1}，二者不等价。

| 方法 | 未知量、最优性 | 优点 | 条件与代价 |
|---|---|---|---|
| 投影迭代／PDAS／VI | 节点d或FE系数；活动下界 g≥0，上界 g≤0，自由处g=0 | 能精确保持旧场、释放活动集；可用稀疏矩阵 | 投影一般离开NN像空间；不能简单投影权重。NN中要用约束SQP/原始—对偶线性化。固定u/f的凸块可认证，完整耦合仍非凸 |
| 可行输出参数化 | d=h+(1-h)T(zθ)，原始θ目标驻点 | 每次前向在所声明支持上可行 | sigmoid端点不达；square map精确hold但边界导数0；clip/ReLU有死区/不可微。可行不等于约束最优，有限样点不保证任意空间点 |
| 不等式AL | θ与支持上的非负乘子；参数KKT＋原始可行性/互补性 | 保留原输出/网络，反力由乘子承载，不必只靠巨大二次系数 | 每个支持点储存乘子，多次内外循环、尺度与rho更新；仍非凸且可能零Jacobian，有限预算未必可行；不能仅按AL loss停止 |

**暂选 AL 的理由：**它避开旧 history-dependent sigmoid-floor 的输出重参数化，同时保留架构和 L2，较便于区分约束处理与表示问题。若可行性提高而场KKT不降、参数KKT已小，应转向可达方向/活跃集SQP或混合求解；不是继续盲增 rho。直接节点解作为较大离散空间的诊断，不冒充相同 L2 参数问题的最优解。

平滑非负 T 在有限 z0 达到最小值 T(z0)=0 时必有 T′(z0)=0；因此“处处平滑、精确保持、在保持点非零一阶导数”不能同时获得。可研究非光滑释放/活动集，不能把换一种平滑映射说成消除了该结构取舍。

## 4. 选定 AL 的数学合同

在 E0>0 的已声明归一化下保留

\[
F(\theta)=\log_{10}E_0(\theta)+10^{-5}R_W(\theta),\qquad c_i(\theta)\le0.
\]

节点下界 c=h-dθ，上界 c=dθ−1；若另做同GP支持比较，下界 c=h_GP−N_GP dθ。正积分/质量权 w 固定，乘子密度 μ≥0：

\[
\mathcal L_\rho=F+\sum_iw_i\frac{[\mu_i+\rho c_i]_+^2-\mu_i^2}{2\rho},\qquad
\mu_i^+=[\mu_i+\rho c_i]_+.
\]

**AL 项加在 log 外。** 不把可能为负的完整 Lagrangian 放进log；不是简单把 Ehist 系数置0且无替代。log+L2改变的参数问题保持明确；乘子不能直接当物理能量单位下的节点反力。支持与 w 归一化一旦定义就固定，不能网格变化后仍用同一乘子数组。

最优性分别报告：(a) primal violation/dual sign/complementarity；(b) 同一 F 的参数 Lagrangian 梯度，含L2；(c) physical E0 的场空间投影/KKT残差和自由u残差。节点box可用

\[G_\tau(d)=[d-P_K(d-\tau\nabla_d E_0)]/\tau.\]

固定tau/度量、自由DOF和尺度；不可把本式套在GP一般线性约束上。GP需对应 Aᵀμ 和互补性证书。KKT只是一阶条件，非凸下不是全局最优保证。原始/罚后/log贡献/参数残差各自标清。

## 5. 本轮完成的本地实现和合成检查

`source/irreversibility_constraints.py`：独立 PHR、detached dual update、box投影梯度；检查shape/dtype/device及已检测的非有限中间量/局部导数，rho限定在dtype的保守正常范围（sqrt(tiny)至sqrt(max)/2）。这不是推荐rho范围，也不替代集成后的完整反传/数值精度检查。不是求解器/runner，没有历史提交、mesh、checkpoint或训练依赖。

`tests/test_irreversibility_constraints.py`：12项单测（含多个边界子例），只在CPU对小张量作代数/autograd。曾因历史source/__init__导入布局失败，改为只加载独立模块；独立审查发现极大有限输入溢出，已增加中间量/局部导数拒绝和回归测试。最终12项全部通过。

| 明确的解析反例 | 看见什么 | 说明什么／不能说明什么 |
|---|---|---|
| min 10d＋(10⁶/2)[.5−d]₊² | 精确最小点 .49999 | 优化已正确仍有1e−5愈合；不是项目实测 |
| H=[[2,1],[1,2]], b=[1,−1], box[0,2]² | 无约束解(−1,1)裁剪成(0,1)，约束解为(0,.5) | 一次裁剪只修可行性，不解耦合最优性 |
| h=.2,s=.5，旧floor更新 | .2→.6→.8 | 源码刷新次序有漂移；未量化旧轨迹影响 |
| T=z²/(1+z²), z=0 | 参数导数0但field下降方向存在 | 精确hold参数化仍可假驻点 |
| T3节点增量(−.1,.3,.3) | 三GP增量全正、首节点负 | GP不愈合不推出节点不愈合 |

这些是实现/数学边界检查，不是方法性能实验；没有生成新的科学Run或相场结果图。

## 6. 能区分解释的下一验证设计（草案，未请求或取得运行许可）

**要改变的决策：**AL能否在原网络中表达并求得保持/增长两类活动状态；若失败，是约束求解尚未收敛，还是可达方向/参数化限制？先不宣称解决完整FEM/PIDL差异。

拟选 Umax=.12 已开发状态的早/中/晚三对峰值—卸载（候选 c1/c40/c80，共6态）；正式输入必须核对恢复偏移、pre/post history、积分支持及准入条件。候选不是已获准新数组访问清单。每个条件问题固定相同 u、f、h、mesh、权重/随机种子和起始θ；求解期间不更新或提交history。旧h若超界或支持不明就停止，不能“修一下”后仍称历史原问题。

**为避免把支持变化当方法收益，比较三臂：**P*（共同节点box处理＋原GP二次不可逆罚）、G（共同节点box＋GP不可逆AL）、N（同box＋节点不可逆AL）。P*是新增受控软罚比较臂，和未经改变的历史P0分开；共同box处理须使用相同实现/预算。P0只作已有结果的描述性参照。G−P*用于相同不可逆支持下的近似/求解比较，N−G用于约束支持改变，不能混成“只换罚项”。

在同一状态同一目标下，复用直接离散场QP/VI构造条件参照；每次只用满足自身完整KKT检查的解。保留网络L2；直接场没有等价weights-only正则，故它只给物理场条件差距/可达方向诊断，不能拿差值量化纯网络容量。若要进一步证明表示能力，应另有同网络构造性见证；有限优化失败不构成不可能证明。

预先观察：最大节点与GP愈合、互补性、参数KKT、E0场KKT、活动集释放、损伤增量局部图、梯度与约束方向、总目标/梯度调用及时间；所有臂保留同λ。主要判断以达到预先固定的约束和同目标驻点精度所需成本为准，未达到则按预算截断，loss下降不计成功。阈值需从来源一致性/数值精度和参考残差确定；本轮不制造未校准数值阈值。

结果分流：
- 参数KKT未到：优化仍未解决，不能宣布容量不足。
- 参数KKT到而physical场KKT差：分辨L2影响与J的可达方向；不能直接称AL失败或物理平衡。
- 可行性/互补性改善但对齐场未改善：只承认约束组件收益，不声称FEM复现改善。
- 满足条件且局部场有收益：才准备完整加载/卸载联合求解，检查最终同一场的u平衡、damage KKT、疲劳更新与总成本；固定态结果不给自动预算。

**拟议上限，仅供后续卡实例化：**一台获批GPU producer，≤2 GPU小时；6态×3网络臂，每臂≤200秒且≤2000目标/梯度调用（含所有line-search），每个直接条件参照≤200秒并占同一总wall预算；单次启动，无科学重试/加种子/调rho扫描。rho最多5次预先定义更新，总调用/时间上限优先；出现非有限、历史不合法、状态不匹配、参考未合格即保留失败状态并停止相应比较。无解/未收敛不能用末态裁剪后计成功。资源/环境准入不是启动授权。

仍缺：六态合法共同前态证明、具体producer/启动卡、集成runner、rho/内层算法与尺度、独立代码复核绑定及ex-ante精度。故**本轮交付不是可启动卡，也不要求用户现在批准一个字段尚未齐全的运行**。本地准备可继续；任何真实运行均需完整明确方案和新的用户许可。

## 7. 来源与阅读范围

本次是既有定向文献的续读/补充，不是穷尽综述。实际模型与旧结果由上述冻结代码/原始日志/协议支撑，文献只支持方法结构与适用条件。

- Manav et al. (2024), *Phase-field modeling of fracture with physics-informed deep learning*, CMAME 429,117104, DOI [10.1016/j.cma.2024.117104](https://doi.org/10.1016/j.cma.2024.117104)。复用已存published全文及FYR `sources/manav2024_l2_irreversibility_reading_20261021.json`；重点§3.2.4、§4.1、Appendix D，未重做论文算例。
- Gerasimov & De Lorenzis (2019), *On penalization in variational phase-field models of brittle fracture*, DOI [10.1016/j.cma.2019.05.038](https://doi.org/10.1016/j.cma.2019.05.038)；复用已存34页[arXiv v1](https://arxiv.org/abs/1811.05334)，PDF pp.6–8、§2.3、Eqs.(13)–(19)。只支持有限罚逼近及约束结构，不提供本项目疲劳最佳参数。
- [PETSc SNESVINEWTONRSLS 官方说明](https://petsc.org/release/manualpages/SNES/SNESVINEWTONRSLS/)（2026-10-21核查）：节点box的约束反力符号与约化活动集。没有安装或运行PETSc。

- Heister, Wheeler & Wick (2015), *A primal-dual active set method and predictor-corrector mesh adaptivity for computing fracture propagation using a phase-field approach*, CMAME 290,466–495, DOI [10.1016/j.cma.2015.03.009](https://doi.org/10.1016/j.cma.2015.03.009)。取得[作者公开accepted稿](https://www.math.clemson.edu/~heister/preprints/HeWheWi15_CMAME_accepted.pdf)，37页；§3.3 pp.6–7 Eq.(12)/Algorithm3.1；§3.4 p.8 Remark3.2/Algorithm3.2。2015 accepted稿明确纠正早稿：限制最终状态相对旧接受态，不能要求每个Newton增量单调。不能把其FE方法直接用于权重盒约束。
- Wheeler, Wick & Wollner (2014), *An augmented-Lagrangian method for the phase-field approach for pressurized fractures*, CMAME271,69–85, DOI [10.1016/j.cma.2013.12.005](https://doi.org/10.1016/j.cma.2013.12.005)。取得[UT Austin ICES13-25](https://www.oden.utexas.edu/media/reports/2013/1325.pdf)，2013预印本，27PDF页含封面；正文§3 pp.5–8/PDF pp.6–9 Eqs.(5)–(8)/Algorithm1/Remark3.1，正文p.11/PDFp.12 Algorithm2。支持AL机制，不验证神经疲劳或本设计停止规则。

补充检索：2026-10-21 19:08–19:11UTC，query `phase field fracture primal dual active set augmented Lagrangian`；OpenAlex成功；Crossref自由检索空值解析失败，两个精确DOI成功解析；用作者/大学全文核对。新增两份全文由独立设计助手核首页、末页、可读性和关键页（实际模型gpt-6-astra、ultra），主代理整合，未将讨论当实验。PDF原件和定向阅读笔记复用既定Obsidian文献库，研究摘要续写既有重构报告，详细方案以本文为准。


## 2026-10-22 计算执行更新

S04-E037 已完成合法前态、完整 runner 和验证方案；首个独立复查后启动在初始前向因 CPU/CUDA 放置错误退出，未有任何优化或参照求解。修复 a706d168 通过已知问题定向复查，但尚未重启；原六态与首次失败均保留。详情见 [首次启动记录](S04-E037/result_20261022.md)。当前等待单次修复重启许可，不把 Code Ready 或合成检查当科学结果。
