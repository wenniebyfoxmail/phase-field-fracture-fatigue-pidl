# 裂缝演化 Neural Operator：架构设计与自检

日期：2026-10-08。归属：S09 Synthetic FEM transition-surrogate qualification。
状态：已获 ChatGPT Pro 外部设计审核 `READY_WITH_CHANGES`，并完成下文第 9 节的文档修订；未实现新模型、未训练，代码审核未完成。
第 9 节为当前采用方案，覆盖前文冲突的初始参数和建议。提交前快照及审核原文保存在 `reviews/20261008_chatgpt_pro/`。关联原型草案为 `S09-E001/experiment.md`；均不赋予旧实验新判定，也不代表 code/run/science PASS。

## 目的、目标、步骤

- 目的：学习载荷条件下裂缝状态的发展，建立可反复使用的状态转移算子；不受现有 PINN 表示限制。
- 首个目标：同一几何、材料、网格族上，输入当前可用状态和已知加载路径，得到非平凡的一步预测及稳定的短滚动。
- 后续目标：独立载荷/初裂纹轨迹泛化、同骨干 PINO 对照、跨网格测试；真实道路另立观测问题。
- 步骤：核对现有资产 → 状态/目标合同 → 小样本记忆测试 → 开发轨迹滚动 → 同骨干物理对照 → 未接触轨迹检验。
- 第一阶段可以放宽精度、样本量、种子数、跨度、物理残差要求；数据身份、输入时序、划分、单位、字段含义仍必须清楚。

## 已知事实与设计判断

本轮已读取共享仓库 source/transition_aware_mesh_operator.py、source/fem_mechanism_operator.py、旧 D1 设计及当前 Hard5 结果文件。共享仓库有无关未提交改动；本轮只新增此设计记录。

本地实读结果：
`local_archive/after_strict_setting_alignment/pidl_result/pino/pf_hard5_loao_gno_v3_a220491_20260826T125803Z/analysis/decision.md`。
该路径相对 parent project root。冻结 aggregate 为 negative / FAIL：U0.12 GNO active log-MAE 0.229827，persistence 0.293264，constrained-linear 0.223188；GNO 的 IoU 更好，但端点载荷误报门槛失败。该结论保持不变。较旧 HARD5_LOAO_CURRENT.md 的“尚未分析”状态已被 case 内 CURRENT_CONTEXT.md 和 decision.md 超越。

推断：已有证据支持继续研究算子，但不支持“网络越复杂越好”或“PINO 必然优于数据驱动”。历史状态、局部化、增量标度、滚动暴露偏差比先增加 Transformer 更值得验证。此推断不是新的实验结果。

## 1. 学习对象与两套明确的数据合同

共同形式：S_next = G_theta(S_recent, prescribed_load_path, geometry, material)。初始条件来自 FEM 的实验是 full-state/oracle surrogate，不能称为从裂缝照片预测。

**A：先跑通的 cycle-to-cycle reduced operator。**

- 从现有 cycle-peak corpus 开始，固定 Hard5、相同加载模板和几何材料；不同语义的 Hard8 不自动混入。
- recent state = 最近 3 个 peak 的 d、疲劳累积量 alpha_bar、log(psi_raw+floor)。f 由已核对的 f(alpha_bar) 推导；若旧数据不满足该关系，保留四通道的旧 imitation baseline，不能静默重写 teacher。
- 加入已知 Umax/加载模板、边界标签、物理坐标和单元面积。固定材料参数无需当作“可泛化输入”。
- 输出下一 peak 的 d、alpha_bar、psi_raw；禁止推理时补入真实未来场。
- 本版本是部分历史条件化的 reduced model，3 个 peak 不被宣称为充分 Markov 状态。它可以先跑，不等待全子步数据。

**B：面向力学残差的 substep operator。**

- 状态至少包括 nodal u,d、生产器实际使用的断裂历史 H、疲劳累积量及计算疲劳正增量所需的上一时刻 driver；字段名和更新时序逐项对照 solver。若模型不使用 H 则不强加 H。
- 输入从当前状态到下一子步的真实处方加载（含增/卸载分支），不是仅输入最终峰值。参数包括 E、nu、Gc、ell 及疲劳定律参数，先固定后扩展。
- u,d 保持节点表示；历史量保持其原生单元/积分点表示，用 FEM shape functions 和明确的投影连接，不用最近邻栅格化冒充原生状态。
- 先预测下一子步 primitive fields，再按已核对的本构更新计算应变、driver 和历史。需要 staggered 更新时，复现其 pre/post 语义；必要的固定次数内部更新由验证误差决定。
- 数据驱动与 PINO 对照使用相同 B 合同、输出表示和结构约束。A 和 B 之间的差异不能归因于 physics loss。

若已封存的 substep export 足够，直接复用；只有字段/状态确实缺失时才提出补导出。不要因为设计新架构便重跑 FEM。

## 2. 推荐骨干：多尺度、带积分权重的网格算子

数据流：状态/边界/载荷编码 → 局部积分核块 → 粗层全局传播 → 局部跳连融合 → 字段增量解码 → 状态约束 → 下一步反馈。

起始参数是工程假设，不是文献给出的最优值：宽度 96；3 个局部块、2 个粗层块；MLP encoder/decoder；历史长度 3；先 1 步训练，再 3 步，最后诊断 10 步。

空间层采用连续位置核与积分权重，例如

`v_next(x_i) = sigma(W v_i + sum_j w_j K_theta(x_i,x_j,geometry,load) v_j)`。

- w_j 为单元面积或节点 lumped quadrature weight；坐标和半径使用物理单位/ell 标度。
- 邻域使用空间索引或 FEM 邻接，不能建立 N×N dense attention。radius graph 限定物理支持；若截断邻居数，记录截断误差。
- 粗层面积加权聚合用于远场载荷传播，细层 skip 保留裂尖/过程区高频信息。全局 pooled scalar 不应成为场预测的唯一瓶颈。
- MVP 直接沿用现有 local/coarse graph 组件；已有 degree-mean 聚合可以先做 fixed-mesh baseline。只有改成明确积分离散、并通过跨分辨率试验，才能支持分辨率迁移主张。
- 新几何可能有孔洞、缺口、裂面；欧氏近邻不能自动跨空洞/断开边界传递。动态损伤只是核输入，首版不把 d 阈值直接变成删边规则。

选择理由：符合现有非均匀 FEM 网格，保留局部裂尖，同时有低成本远场通道。它不是旧 PINN 外挂修正器；训练后一个共享 theta 服务多个初态/载荷轨迹。

候选对比：FNO 适合规则场但需控制映射误差和谱平滑；DeepONet 适合参数到场的廉价独立对照；GINO 的 mesh↔latent-grid 路线适合作第二阶段，首版暂不叠加 Fourier/Transformer/tokenizer。上述是本项目选型判断，不是普遍性能排名。

## 3. 输出约束及损失

- d_next = clip(d_current + delta_d_raw, d_current, 1)。同时保留 raw proposal，报告投影率和过早饱和率。
- 不用始终严格为正的 sigmoid/softplus 增量强迫每一步增长；停裂必须能输出零增量。clip 的死梯度需在小样本记忆测试中监测，必要时改参数化并记录新版本。
- A 的 alpha_bar 同样只允许非负增量；B 优先使用生产器一致的历史更新。f 不作为无约束的独立自由场。
- B 的 Dirichlet DOFs 通过已知值赋值或边界 lifting 满足。约束投影不等于 equilibrium、正确疲劳机制或物理验证。

数据损失：L_data = L_state + L_increment + 0.1 L_spatial + 0.5 L_rollout。
系数均为初始工程假设，训练集标度归一化后才使用；首个记忆测试可只用前两项。

- state/increment：按单元面积/积分权重统计、按训练集每通道标度归一；用 Huber 控制极端点，不能用 held-out 标度。
- spatial：对 d 的 FEM gradient 或物理距离归一 edge-gradient 误差；只作为局部形态辅助。
- rollout：真实初态起步，随后反馈自己输出，梯度贯穿有限短窗口。验证不用每步真实场重置。
- 同时报告全域和增长区指标，避免“全预测不长”得到小损失。训练可平衡训练轨迹内的增长/停滞窗口；验证保留原分布。
- 首版移除全局 event classifier 对场解码的强制调制；event 从预测场派生。是否重加局部 onset head 是后续消融，不与首版同时堆叠。

## 4. PINO 对照：同骨干增加可计算的物理项

在 B 合同下，PINO = 同一 G_theta + L_data + lambda_phys L_physics。

- 首个物理项为离散弱平衡 R_u = f_int(u,d)-f_ext，仅对 free DOFs 计算；Dirichlet DOFs 的反力不是残差错误。
- 相场项使用生产器对应离散方程。对于真正 variational box-constrained 模型，可用 projected-gradient residual：d - projection_[d_old,1](d - eta grad_d Pi)。若 teacher 使用 history-field/penalty/staggered 形式，必须按实际形式实现并标注；不能把不等价的能量写成同一个 physics loss。
- 历史更新一致性作为诊断或惩罚，取决于它是否已被硬编码；不要把恒为零的硬更新重复包装成新增物理证据。
- R_u、R_d 无量纲化，并按自由度/积分权重归约；禁止拿不同量纲原始 norm 直接相加。权重从训练集参考量定义，初值 lambda_phys=0.01，数据 warm-up 后渐增至 0.1；仅为可修改的开发假设。
- 先做两臂：data-only 与完整可计算 physics 项；若 PINO 变差，再做 equilibrium-only 消融定位冲突，不预先开展大矩阵。
- 对每一残差先检查正确状态、已知扰动状态、边界 DOFs、梯度方向和导数计算。teacher 本身残差不合格时明确标出 label/physics 冲突；它不妨碍 A 的 imitation smoke，但不能当成已验证 PINO teacher。
- 对照必须保持训练/验证轨迹、骨干、初始权重、预测起点、结构约束相同，报告训练成本；至少给同数据结果，少数据优势另作训练集比例试验。测试时优化若存在则单列，不混入一次前向结果。

## 5. 宽松但有区分力的阶段验收

下列数值为本轮提出的候选开发合同，尚未被冻结或获得独立 review。旧运行已被查看，旧轨迹上的新模型结果一律 development-only。

| 阶段 | 最小任务 | 候选验收 | 允许结论 |
|---|---|---|---|
| P0 接线 | forward/backward、mask、state timing、几何权重 | finite outputs/gradients；零更新可表示；无未来输入 | 程序路径可用 |
| P1 记忆 | 16 个训练窗口，含可分辨增长窗口；1 seed | 固定训练集归一损失相对初始化下降 ≥80%；增长窗口 damage 增量 MAE 低于零增量基线 | 架构能拟合这些窗口 |
| P2 短滚动 | 一个完整开发轨迹；预先按 cycle index 均匀固定起点；3-step autonomous | 主指标：增长目标上的面积加权 damage 增量 MAE / persistence MAE <1；无 NaN/越界 | 有有限开发集预测信号 |
| P3 正式泛化 | 新的未接触完整轨迹、训练集内验证、3 seeds | 开跑前确定相对 persistence 与 constrained-linear 的单一主要 gate | 支持或否定受限泛化 |
| P4 物理对照 | 相同 B 数据、模型、起点的 data-only / PINO | 分别报告场误差与残差；物理收益的正式 gate 在数据能力核实后冻结 | 量化物理项效用 |

P2 增长集合定义为 target 的面积加权 damage 增量超过预先由训练集/导出精度确定的 noise floor；仅用于评分，不给模型、不开 event-relative 起点。若集合为空或 persistence 误差近零，该主指标 not_evaluable，不造有利比值。停滞集合同时报告 false growth 量；它不能被丢弃。

P1/P2 可以容忍模糊裂纹和不准的失效周期，但不能让完全不长的模型混过增长诊断。10-step rollout、裂尖误差、d=0.5 IoU、载荷反力、event timing 先作诊断；若 teacher 与当前表示不能计算则标记 unavailable。

比较的最小顺序：persistence → constrained-linear → 新 GNO-data → 同骨干 PINO。旧 PIDL 使用同初态/载荷/时刻/物理量后才作公平比较；否则明确 secondary，不宣称总体优于 PIDL。

算力假设：AdamW lr=3e-4，weight_decay=1e-6，clip=1；batch=1 trajectory window；P1 最多 1,000 updates，P2 首版最多 3,000 updates。未做显存/速度 profile，不能承诺小时数。P1 达标可提前停止；失败先查标度、投影和字段，不直接放大网络或预算。任何训练只在经检查的 Taobo producer，Mac 仅轻量开发/检查。

## 6. 自我验核与失败解释

| 审查问题 | 本轮结论 / 修正 | 尚需证据 |
|---|---|---|
| 是否换名重做旧 GNO？ | 骨干大量复用；新重点是 primitive/history 合同、积分权重、无全局事件瓶颈及公平 PINO 对照 | 消融结果；不预设架构新颖性 |
| 相同裂纹能否有不同未来？ | 能；载荷路径/疲劳历史不可省。3 peak 仅是 reduced approximation | 相近 d 不同 history 的配对，以及去历史消融 |
| 是否学 cycle 序号？ | 首版不输入绝对 cycle；加载分支与处方路径有因果意义 | 路径变化/幅值 holdout |
| NO 是否只是网格 GNN？ | fixed-mesh MVP 可以先是 GNN surrogate；连续核/积分离散提供 operator 路线 | 同一物理场多分辨率输入及输出收敛检验 |
| 非局部传播会抹平裂尖吗？ | 保留 fine skip、gradient loss，诊断过程区宽度 | tip 误差、过程区宽度、局部 support |
| 不可逆能否掩盖错误？ | 能；raw proposal、投影率、false growth 必须保留 | 投影前后场和停滞测试 |
| PINO 会不会变坏？ | 会；不合格 teacher、残差时序错误、权重失衡均可能造成冲突 | 先 residual unit checks，再同骨干比较 |
| 开发集是不是独立测试？ | 不是；尤其 U0.12 已做多轮 post-hoc 分析 | 新未接触轨迹用于确认性结论 |
| 小样本能否宣称概率/分叉预测？ | 不能；首版确定性。分叉多模态时平均场可能失真 | 多独立轨迹后再做 ensemble/mixture 与校准 |
| 能直接面向真实道路吗？ | 不能；真实观测需要 image-to-state 反演和不确定性 | 独立观测协议；另属 S02/S03 |

综合自检：设计适合进入最小原型；状态充分性、跨网格性、PINO 收益仍未验证。概念自检不是独立 review，也不是数值/科学验核完成。

## 7. 实施资产和下一步

复用：source/fem_mechanism_operator.py 的图/统计/约束基线，source/transition_aware_mesh_operator.py 的局部/粗层通路和面积聚合，已有 loader、native-mesh plotter、trajectory split/receipt 机制。新的实现须从干净 worktree 开始，明确旧 checkpoint 不可冒充新模型。

建议模块：state_contract / data_adapter / graph_operator / rollout / fem_residual_adapter / evaluate。首先输出一个 data-capability 表，列每个字段的位置、单位、时间标签、是否推理可用；再绑定实际数据完成 P0/P1 配置。

最小交付：config、run receipt、学习曲线、固定起点 rollout 场图、同表 baselines、decision.md。claim-bearing figure set 配 README_analysis.md。真正执行时建立新的 S09 experiment.md 和 fresh Run ID，不改旧 D1/Hard5 协议。

实验五问：问题是状态条件化算子能否产生非平凡短滚动；成功仅改变可实现性/开发预测判断；更便宜的诊断是资产核对与 16-window 记忆；最小资产为上述比较表/场图/决定；正式结果写入新 S09 Experiment 并链接 Storyline。

初稿时外部规划接口尚未接通。2026-10-08 经用户明确授权 Haofan 账户，已通过 OpenCLI 的 ChatGPT Pro 完成外部规划审核；原文、提交快照和采纳表见 `reviews/20261008_chatgpt_pro/`。该设计审核不替代绑定实际代码、配置和数据的独立审核。

## 8. 本轮文献定位（非系统综述）

模式：discovery。2026-10-08，通过 agent-reach/Exa 与 web 检索。主 query 为 `neural operator phase field fracture history dependent fracture DeepONet physics informed neural operator GINO`；补充 queries 为 PINO 2111.03794、GINO 2309.00583、phase field fracture DeepONet variational operator learning。无年份过滤；保留原始研究，按 arXiv ID/题名去重。只用摘要/可访问页面定位架构先例；未做全文复现或穷尽 novelty audit。

- Li et al., *Physics-Informed Neural Operator for Learning Partial Differential Equations*, arXiv:2111.03794，摘要：数据与 PDE 约束组合学习算子。https://arxiv.org/abs/2111.03794
- Li et al., *Geometry-Informed Neural Operator for Large-Scale 3D PDEs*, NeurIPS 2023 / arXiv:2309.00583，摘要：图与 Fourier 模块连接不规则几何和 latent regular grid；其流体结果不能外推为裂缝性能保证。https://arxiv.org/abs/2309.00583
- Goswami et al., *A physics-informed variational DeepONet for predicting crack path in quasi-brittle materials*, CMAME 2022，检索页摘要/片段：变分能量与数据混合的相场裂纹算子先例；全文直取失败，未作全文验核。https://www.sciencedirect.com/science/article/pii/S004578252200010X
- Kiyani et al., *Predicting Crack Nucleation and Propagation in Brittle Materials Using Deep Operator Networks with Diverse Trunk Architectures*, arXiv:2501.00016v2，摘要：数据驱动、能量约束和 KAN 变体，包含起裂/传播/分叉算例。https://arxiv.org/abs/2501.00016

这些来源说明存在技术先例，不证明本文设计能解决疲劳闭环。可研究的贡献应围绕历史状态、局部发展和闭环/泛化证据，不能写成“首次用 Neural Operator 预测裂缝”。

## 9. 2026-10-08 Pro 审核后采用的设计（优先于前文）

来源：[审核原文](reviews/20261008_chatgpt_pro/review_raw.md)、[采纳决定](reviews/20261008_chatgpt_pro/decision.md)。外部判定为 READY_WITH_CHANGES；以下为本地采纳修订，尚未由 Pro 对修订稿再次审查，不能写成无条件审核 PASS。

### 状态与数据

1. A 的一次转移明确为“已接受峰值 → 卸载/恢复 → 全部再加载子步 → 下一已接受峰值”。固定模板可用经核对的模板标识及幅值表达完整处方，不能用峰值净能量差代替整周期疲劳累计。各字段绑定实际 accepted/commit 时序。
2. 在相同原生支持上才可使用 f(alpha_bar)。非线性与平均不交换：P[f(alpha_bar)] != f(P[alpha_bar])。如果只有单元平均数据，就直接学习这些平均量；不据此判 teacher 错误，不从平均 alpha_bar 静默重建平均 f。需要 f 时保留档案监督的额外输出，或将其诊断标为 unavailable；两者必须在实际数据合同中选定。
3. 默认保持 A 的现有空间支持，优先复用库存。节点 d/原生 GP 历史确实可用时分支编解码并用 FE 映射交换特征；只有均值时不等待重导出，不伪造 GP。
4. 状态充分性反证要匹配全部 recent-state 输入、几何材料与后续加载路径；仅匹配 d 不足。近邻未来差异是告警，须区分缺状态、数值噪声与裂尖敏感性。存在子步档案时抽一个完整周期做疲劳账核对，否则 A 标记 closure_unverified 后继续。
5. P2 整条物理轨迹分组；重启、重导出和重网格副本不构成独立组。窗口的 3 个输入状态和 3 个目标状态不得跨划分。完整开发轨迹不进入梯度训练；已被人查看不妨碍开发使用。untouched test 仍需另留。

### 缩小后的 MVP 与训练

- 宽度 64；2 层局部积分块、1 层粗层传播、细场 skip；MLP 编解码；不加 Transformer、事件分类瓶颈或完整相场 loss。
- 候选连续核用秩 8 因子化 K=B diag(kappa) A，避免逐边 C×C 核；局部半径初值 2ell，粗层不超过 256 个物理空间聚合单元。实际连通性、边数和显存 profile 决定是否修订这些假设。求积按层处理；面积不是未经解释的网格密度特征。
- 输入三个已接受峰值的 d、alpha_bar、z=log(1+psi_raw/s_psi)，以及完整处方、x/ell 和边界标签。s_psi 与各增量尺度只由训练集确定，设置非零数值下界；固定材料不宣称为泛化输入。
- 三个有符号 raw 增量头；d_next=clip(d+s_d*r_d,d,1)，alpha_next=alpha+s_alpha*max(r_alpha,0)，z_next=max(0,z+s_z*r_z)。全零头严格保持状态。所有滚动历史都反馈预测值；不可逆下界是自身当前完整细场，不能用粗化重建替换。
- 必须对真值起点的一步分支监督 raw 增量；自主滚动主要监督累计状态。raw 监督同样覆盖受截断的 alpha/z 头，以免死梯度只从 d 转移到别的通道。检验负提案/正标签时头部有非零纠正梯度，先查 teacher 是否满足实际施加的约束。
- 初始 loss 为 state + raw_increment + 0.1*gradient_d + 0.5*autonomous；P1 先只用前两项。每个通道的增量标度从训练集中可辨非零增量确定，不被大量零值压塌。
- 一个 seed；P1 默认增长/停滞各 8 个窗口，最多 1,000 updates；P2 另最多 3,000 updates，前 2,000 一步、后 1,000 三步。P1 checkpoint 可作 P2 warm start，但这些窗口必须都属于训练组。保留 AdamW lr=3e-4、weight_decay=1e-6、clip=1。

### 修订后的宽松验收

- P0：finite、零头保持、负提案可纠正的梯度、字段时序和空间支持正确。
- P1：增长窗口 damage 增量 MAE / persistence MAE <=0.8 为主；相对初始化损失下降80%改为日志，不再单独决定通过。
- P2：从固定真实起点自主预测三步。令 ||v||_w=sum(w_i*abs(v_i))/sum(w_i)，G_n=||d_(n+3)-d_n||_w。冻结 tau 后，增长起点集合为 G={n:G_n>tau}。
- 主误差 R3=sum_G ||dhat_(n+3)-d_(n+3)||_w / sum_G G_n <=0.95。分子在全域算，避免忽略错误位置的增长。
- 非退化护栏：sum_G ||dhat_(n+3)-d_n||_w / sum_G G_n >=0.25；停滞窗口最大预测增长 <=0.25*G_ref+2*tau，G_ref 为训练集中有效三步 G_n 的中位数。三个条件同时满足才记 P2 development pass。
- tau 由导出精度/训练期静态数值噪声冻结，与 G_n 同单位；实际数据审计尚未完成，当前不虚构数值。无增长样本则 not_evaluable；无停滞样本仅报告 growth-only prototype，不能宣称完整 P2 护栏已通过。若 G_ref 不可定义则先解决库存/噪声问题。
- 5%/25%门槛均为 Pro 提出的工程假设；不是论文标准、保证或旧实验新门槛。线性外推仍完整报告，暂不要求 P2 必须胜过它。10-step、裂尖、IoU、失效周期作诊断。

### PINO 最小对照与延期项

- B 的第一对照改为 data-only versus equilibrium-only，同一节点 u,d 输出、历史更新、边界约束和输入合同。仅称 equilibrium-regularized operator，不宣称完整 AT1-fatigue PINO。
- 共同 data warm-up 500 updates；复制权重和优化器状态后每臂 1,500 updates，相同 seed、窗口顺序、起点及按开发场误差选 checkpoint。物理臂自由 DOFs 上的无量纲 R_u 权重从 0.01 到 0.1；报告实际计算成本。
- 首版一次前向即可，不复刻 staggered 迭代次数。若以后增加内部迭代，trial history 每次从不可变 accepted old state 重建，不累计内部试算；相同 trial 重算不增加疲劳。
- R_d 延后至 AT1 系数、能量分裂、原生支持、penalty/history 时序核对之后。组装残差已经包含积分，不能再任意乘面积。构造相场残差时区分生产器固定 H,f 的偏导与对最终 residual loss 求网络参数梯度；投影步长固定，不能靠缩小 eta 制造小残差。
- 顺序消融：1 vs 3 peak / 去历史；raw 监督有无；一步 vs 三步训练；degree-mean vs 求积权重。重采样一致性只检验离散敏感性，不等于新网格物理解泛化。

当前完成范围：审核取得、文档修订、采纳记录。下一步是绑定实际数据能力、冻结 tau 与 split、实现 P0/P1；未执行训练，也未将文档修订当成模型效果。
