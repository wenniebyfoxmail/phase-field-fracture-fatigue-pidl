# 当前 PIDL–FEM 状态/字段核查与解决路线

日期：2026-10-20，Europe/London。范围是已使用的本地保留资料及其来源，未远程查询运行状态。

**结论：已检查的保留索引和提交链没有发现新增错位；真正需要处理的是不同参考家族、raw/active字段定义、求解用系数与提交后系数、条件重求解与完整演化的区别。**本轮生成143条状态记录、1353条字段记录和263条检查记录：260项索引/身份/提交关系检查通过，另列2项已知语义缺陷和1项条件参考说明。这不是143个独立物理试样，也不是完整原始轨迹的无遗漏证明。

## 交付与核查层级

- [逐状态表](state_map.csv)：包含轨迹家族、Umax、cycle、substep、恢复步偏移下的raw step、原标签、来源、角色、更新时刻及核查层级。
- [逐字段表](field_map.csv)：明确实际文件/组/数组切片、节点/单元/GP支撑、pre/proof/proposed/post时刻、对应字段及来源限定。
- [检查表](checks.csv)、[文件清单](file_inventory.csv)、[结构化摘要](summary.json)、[结论影响表](claim_impact.csv)。
- 原始输出：[audit_v1](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/pidl_fem_state_audit_20261020/audit_v1)。脚本是本目录audit.py；检查代码a12784f4。无模型加载、forward、训练、optimizer、FEM求解、SSH、holdout字段读取。

核查强度分别为：Hard5清单/字段schema/文件存在；配对轨迹实际cycle/step索引及字段状态轴；MCS端点c/q/outer标量与既有接受记录；c20四个锁定MAT的大小/SHA/前态/端点数组身份；c1十次提交的完整链与字段关系。清单级条目不能升级为数值复核。未逐个读取所有原始601步PT或未保留的诊断，不能报告“全轨迹无缺失”。

## 1. 目前实际使用的资料，不止一对文件

| 资料 | 已核查内容 | 合理用途 |
|---|---|---|
| 历史Hard5 exact-peak v2.1、fixed-calendar v3、first-detect导出 | 3+9+6条清单状态和字段schema | 历史基准的原问题分析；不是近期重求解端点 |
| E011 ad749c8 Q4/T3成对轨迹 | 每拓扑8个节点配对峰值、16/14个compact峰值、各4个reduced条目 | 同循环原始求解器比较，保留各自历史 |
| E011 MCS | 11个固定前态条件端点及实际H5 c/q/outer | 条件性求解控制；零history提交，不可拼接成连续修复轨迹 |
| E011 c1 v4/r1 original/repaired | 各5个连续提交，pre/proof/proposed/post逐字段 | c1加载/卸载与提交机制比较；不覆盖f<1疲劳反馈 |
| E011 tight-coupling | 固定c20s4的36个字段/读数记录 | 同态位移优化；机械使用外置FEM d，保存NN d另列 |
| E024 | c20s4/c60s4/c83s4三个receipt/字段头 | 已见状态拟合；10000为参数更新次数 |
| E027–E034 | 同一个c20s4的四MAT锁、前态及8个协议血缘 | 条件状态拟合/修复；不是8次物理演化 |

若后续使用另一个包、另一个加载表、另一初始化或另一源版本，必须新增该包映射，不能复用此处固定公式作猜测。

## 2. 错位、漏配和混用：具体判断

**A. 索引：保留配对通过；98/99是不同角色。**当前五子步、raw0为恢复步的PIDL映射为`j=1+5(c−1)+(s−1)`。八个实际NPZ索引与JSON、FEM周期集合和字段状态轴吻合；raw98=c20s3，raw99=c20s4。E027明确以98作热启动，用FEM c20s3的lower/history约束c20s4，所以这个差异不是错位。旧无恢复步的`5c−2`峰值公式不可用于当前包。447是c90s2，不是c92。

**B. 漏配：c84峰值诊断未保留。**当前成对轨迹的PIDL compact峰值无c84；已有分析把突变定位为`(c83,c85]`是合适的。不能把插值或相邻帧当成实际c84，也不能由缺帧断言模拟没有执行c84。九个calendar、三个exact-peak、六个first-detect及11个MCS条目所指本地文件均存在；这只覆盖列明的保留范围。

**C. raw/active：真实发生过，但已经更正。**E011原reduced比较把FEM未退化raw与PIDL退化active相比，约−99.98%的active差异已由原owner撤回。相同c83的正确native-GP计算记录Q4 active积分差+5.809%、rel-L2 0.476、相关0.887；T3为+33.834%、1.026、0.470。本轮不复算这些物理量，只核查它们的来源和更正关系。原始定义错误不能继续作为机制论据；后续同量比较不因这个旧错误自动作废。原证据：[decision.md](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/decision.md)。

**D. trial/commit：当前c1链没有发现混用，但不同组不能互换。**10次event均提交1次且版本0→5连续。下一步pre的u/d/lower/history/raw与前一步proposed逐数组相同；proof使用原前态；proposed.u/d/raw等于proof，proposed.lower等于新d；提交的history通道2:4与proof.history234在源合同1e−10内一致；post.history输入等于proposed.history，其fresh trial也满足幂等检查。H通道1仍按opaque处理，身份相同不等于其本构意义已验证。原生original五步均有提交，但其保存fresh joint flag均为false；repaired五步均为true。不能把原生接受规则与加强的联合规则混称。

**E. MCS端点：时刻明确，但不是原轨迹。**c20s4的lower与c20s3 d、old history逐数组一致；case.current与outer18的u/d/raw/Ru/Rd/history234逐数组一致；源身份四文件全部通过。outer18的policy_pass=1，而该case保留原参考pass=0且required=0；这是原前态下的条件重求解。11个MCS条目中8个按其原联合规则接受，c60s4/c80s4/c83s4三个在20outer预算内未接受，不能当合格teacher或连续修复轨迹。这里“8”含独立c1_common_anchor，不是8个独立样本。来源：[cases.json](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/cases.json)。

**F. 保存的NN d与机械使用的d不同。**tight-coupling源码明确`mechanical_damage_exact_FEM=True`、`NN_damage_field_fixed_claim=False`。其NPZ中d是网络输出，隐藏层更新时可以改变；机械能与残差使用固定外置FEM d。E031–E034又是另一条血缘：外置physical d来自E030实际结果，不是FEM target，也不能换成S1500网络第三头。表中分别标记；单个fields.npz只有u/v/d，不是包含lower/A/r/f/载荷/源身份的完整restart。来源：[确切runner](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/tools/s04_e011_analysis/run_pidl_tight_coupling_hidden_newton.py:199)、E034 data_lock。

**G. 求解系数与提交后读数：仍有算法差异。**ad749c8的model_train.py先把f传入fit，之后更新hist_fat、重算f，再写diagnostic/checkpoint；原FEM phase trial则从固定old状态和当前u/d重建trial f。即使最后导出都叫post-commit，也不是完全相同的离散求解过程。compact保存场没有单独给出每步f_solve；不能由f_commit相同推断优化使用的f相同。E027读取outer18.history234中的目标f作固定系数，并使用FEM前态，故其P臂也是**给定FEM状态信息的条件物理求解**，不是从独立观测自主恢复疲劳历史。旧结论只在既定条件问题内成立，不因重新命名变成完整物理预测。

**H. 事件家族必须分开。**此前聊天引用的Hard5 first83/confirm86及旧PIDL89/90来自2026-09-29历史报告合同；近期E011 pair的fem_event_summary记录FEM84/87，trajectory summary记录PIDL-Q4为85、PIDL-T3为89。不同来源/问题的事件不能混接，不能通过减1使其一致，也不能在未统一检测规则前宣称事件探测器等价。本轮以各来源保留原标签。

## 3. 哪些已有结论受到影响

| 结论或读法 | 本次处理 |
|---|---|
| 旧约−99.98% active差异 | 沿用既有撤回，不可引用；以正确同量native-GP结果替代 |
| 当前所有误差只是cycle错了一格 | 保留索引与前态身份不支持这个解释；不排除未保留时刻中的问题 |
| c83→c85的事件附近失配 | 保留区间结论；不能升级成c84精确场突变 |
| 空间Q4/GP对齐已等于完整离散问题对齐 | 不成立；fixed committed f/trial f、求解器和接受规则仍不同 |
| c1修复改善接受态一致性 | 保留该c1合同下组件结果；不是f<1疲劳、全轨迹或teacher资格 |
| MCS多个端点已组成修复演化 | 不成立；零提交、不同冻结前态，且三个峰值未接受 |
| E024拟合/0.2缩放及E027–E034组件比较 | 保留其已见固定状态结果；不升级为演化、泛化或完整物理恢复 |
| tight位移残差/方向结果 | 保留外置FEM damage条件下解释；不声称网络damage已闭合 |
| E033 raw未达/反力代价，E034无严格接受 | 保留原判据及负结果；这次检查没有提供改阈值或重跑理由 |
| 新混合方法已有完整标签/训练收益 | 已读记录没有完整合格轨迹；成本停止不是NN效果负结果。后续状态由唯一owner维护 |

![状态核查图](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/pidl_fem_state_audit_20261020/audit_v1/state_audit_decision.png)

看到：配对峰值编号有清楚映射，但c84缺诊断；c1两条链均只提交一次，联合接受标志不同。
因此：应修复状态/字段接口与接受语义；不能靠改横轴或有提交文件就宣称物理一致。
该图不比较新方法物理误差，也不证明完整原始轨迹已经审完。

## 4. 第一性原理：解的是两个接口与一个状态转移

对当前模型，接受态应写为`S_n=(u_n,d_n,A_n,r_n,f_n; mesh,material,loading,solver-policy)`，其中A是累积疲劳量，r是前一接受态active driver，f由指定疲劳律得到。一次物理子步应从**不可变接受前态**构造trial：

`a_trial = g(d_trial)*psi_raw(u_trial)`

`A_trial = A_old + positive_part(a_trial-r_old)`，`f_trial = fatigue_law(A_trial)`。

机械平衡、损伤约束、fresh最终状态一致满足后才一次提交。外层迭代、优化器更新、日志行、导出帧都不是额外物理循环。原FEM软罚与新节点box约束是不同问题，必须各自保留，不静默替换旧参考。下述是解决设计，不是本轮新数值结果。

**接口一：导出到物理状态。**所有下游程序先读取统一状态表，以`family+trajectory+Umax+cycle+substep+load branch+commit phase+field definition+native support`连接，原始step只作来源。保存一份接受态及parent_state_id，trial/optimizer字段另分角色；导出f_solve与f_commit，raw/active/history-max分列，外置physical d与NN d分列。配对失败就明确缺失，不插值伪造history，不按曲线最像的位置配对。变子步/自适应加载/跳循环必须查日志；真实数据只有帧号时保持帧号，拿不到载荷计数就不输出cycle寿命。

**接口二：观测到状态。**真实图像满足`y_i=H(S_{n_i},camera,illumination,visibility)+noise`。mask是观测，d是内部变量；同一mask可以对应不同弥散d、开口、A/r/f与未来。给mask做距离变换可以构造几何先验/初始化，但距离尺度不能直接叫材料ell，平滑mask也不是已恢复真实d。更可行的连接是mask/裂尖几何＋已知加载＋DIC位移/反力的联合似然；对仍不可辨识的参数/状态保留集合或分布，避免强行输出唯一真值。

**状态转移：先保证正演可接受，再评价学习模块。**当前统一空间算子的资产足以重放既有场，却不能替代一条同合同、同前态、自身历史推进的完整接受轨迹。只把单态误差压低，并不能解决下一个加载/卸载态。

## 5. HQ推荐：继续现有完整混合路线，把两座接口桥接上

### 主线A：沿唯一owner完成共同物理问题，停止把固定头小修当主研究

这里的唯一owner是工作区`pidl-weight-gradient-fix-20261018`下的[混合方法主记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/decision.md)，不是本审计分支。2026-10-20本轮读到的当前科学选择为[D12完整比较v1](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/coupled_scientific_decision_v1.md)；具体参数及首次停止条件见[准备卡v4](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/coupled_repair_card_v4.json)，该卡仍禁用，不能从本文直接启动。[D10实际成本结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/linux_validation_result_v1.md)、[D11修复v2与预算](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/hybrid_constrained_design_20261019/coupled_repair_v2.md)保留其原日期/版本；未来精确执行卡只能由原owner按最新授权准备。本审计不接管该分支、协议或producer。

复用已实现的受约束增量混合框架：NN只提出可行damage初值；机械FEM解平衡；全节点damage约束块允许释放活跃集；trial历史永远从old重建；最后fresh联合验收后原子提交。reference、经典外推与NN三臂使用同一新合同与同一接受精度。旧软罚FEM/PIDL保持历史比较身份。不是再换一套网络，也不另起第二个producer。

当前明确瓶颈是完整耦合重复调用的实际成本：已有Linux记录中首步从56.952s降到38.733s，但第二步仍在第9轮机械重平衡的LU里达到120s；9次QP、8次完成重平衡，尚未得到全链数值/训练收益。既有受保护Anderson修复及当前owner后续D12衔接应继续复用，不重新提出同一方向或把首步31.99%当NN加速。保留失败和现行停止条件；不能因总预算未耗完自动重启。

决定性比较沿既有整套验证，而不是再做一个c20微步：完整加载/卸载、达到f<1的疲劳段、共同初态和各自历史、整轨迹留出，比较直接同合同FEM、经典可行外推和冻结NN初值。主判断是同质量下的完整路径误差与实际在线代价；预先选择一个承重主读数，接受态物理条件只作解释有效性的必要条件。旧预算/判据不由本报告修改；原方案1200训练+600验证+600测试参考状态，经典/NN测试各600共3600子步，12GPUh/136hosth只是上限和资产缺口，不是已生产标签或实测耗时。新执行必须服从原owner当前精确卡和实际授权。

若共同求解器自身仍无法接受路径，应修该数值问题，不训练网络遮盖；若NN与经典都同样好，采用经典；若NN质量相当且包含推理、失败、校正、存储的总在线成本更低，才有学习价值。离线标签/训练与失败费用另外计入盈亏平衡。

### 桥B：把mask限制为可观测几何，联合运动学辨识状态集合

复用既有反演文献、DIC和SCB owner方案，不新开并行反演试验。先定义想要支持的输出：当前裂缝几何、有效退化状态，还是未来裂长；不是默认恢复所有A/r/f。已知或独立标定加载/材料，采用掩膜/裂尖几何、可信DIC位移区及反力组成观测算子。先通过灵敏度矩阵、条件数和profile/状态集合判断哪些组合可识别；有多个相同观测拟合且未来分叉的状态时，报告未来范围并说明下一种观测能缩小它。

决定性验证应一次比较`几何+载荷`、`再加当前DIC/反力`、`再加真实自身历史`及保持当前信息但替换历史的对照；同物理试样、同加载相位、独立裂长参考，整试样留出。若有历史才稳定改善独立未来且替换历史失效，才投入疲劳状态同化；若当前响应已足够，就保留更简单模型。Kosin的18页出版PDF已在库，本轮核读pp.3–5 §2–3、pp.8–11 §4.1.1/Figs.4–6、pp.15–16 §5/Data availability：它支持图像—机械联合反演的组件和时空条件化，不是从二值mask唯一恢复d/A，也不是已验证真实疲劳。其phase变量约定1为完好，与本项目d方向相反，移植时必须显式转换。

对于只有发布序号的19组响应资料，继续现有预测状态路线：发布步只定义下一个记录观测。已有BRIDGE-PS R003平均增量及C30反例说明这条统计路线有组件价值，但不能补造独立试样身份、载荷或cycle。物理闭环沿已有SCB数据申请和独立参考设计推进；外联仍逐次审批。本报告没有授权外发或新计算。

### 开源材料如何具体使用

| 来源与本轮核对 | 可复用部分 | 不能直接照搬 |
|---|---|---|
| 已有GRIPHFiTH/Q4/GP导出、原子提交与hybrid代码 | 当前原生算子、字段与事务基线 | 未通过条件的端点不能自动当teacher |
| [IFENN原文](https://arxiv.org/abs/2505.19566)，已存完整原稿，§3/Fig.2 | FEM负责平衡、学习模块负责另一场的职责分配 | 其AT2/历史场和速度数值不是本项目AT1/Amor疲劳结论 |
| [PETSc SNESVI](https://petsc.org/release/manualpages/SNES/SNESVINEWTONRSLS/)及[Anderson](https://petsc.org/release/manualpages/SNES/SNESANDERSON/)官方说明 | 约束活跃集、非线性加速的可核查实现参考；仅当现有后端有明确替换收益时再评估 | 不能为了换库而改变eta、分支、容差或再造一个求解器 |
| [Kosin 2024](https://doi.org/10.1016/j.cma.2023.116689)及[pfm-cracks作者仓库](https://github.com/tjhei/cracks) | 图像残差、时空灵敏度和条件数；主动集/FEM参考 | p.16明确Correli3.2是inhouse、数据需申请；公开pfm-cracks不是完整即用IDIC pipeline |
| [Manav 2024](https://arxiv.org/abs/2404.13154)、[能量自然梯度](https://proceedings.mlr.press/v202/muller23b.html)，已存原稿 | 若必须纯神经，采用物理块/函数空间度量与裂纹尺度表示 | 投影头部驻点不等于完整平衡；理论假设不自动覆盖本耦合非凸疲劳问题 |

本轮使用agent-reach/Exa定向检索；Exa随后限流，按官方网页与gh只读API核对作者仓库（GPL-2.0）和PETSc。复用2026-10-19已有Crossref/OpenAlex检索及四篇全文矩阵，没有重复做系统综述或新颖性判断。Kosin复用已存出版全文和既有12篇反演综述，未新增下载。未安装、编译或复现这些开源项目。

## 6. 目前可执行的下一决定

本轮审计已完成，可直接用此映射审阅图表和限定结论。下一方法工作沿唯一混合owner把接受态/字段契约接入原整轨迹实现，先解决已测得的耦合成本；观测侧沿原SCB/反演owner落实同步载荷与独立参考。新增训练、FEM或远端执行属于各自精确方案，不由“HQ建议”自动启动。没有为了本次报告修改旧协议、旧负结果或现有运行卡。
