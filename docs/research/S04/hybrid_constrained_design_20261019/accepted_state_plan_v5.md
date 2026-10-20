# D13：把统一接受态和逐字段时刻接入原混合方案

目的：消除“同名字段、不同更新时刻”及“同编号、不同物理问题”的混比，让原D12完整比较可以判断联合轨迹可达性和神经初猜的额外价值。本轮复用原owner的求解器、Anderson、网络、事务和producer；仅修复身份、导出、标签与评分连接，没有新建数学核心。范围为本地实现、人工数据测试和独立只读Codex审核；没有SSH、项目数组重算、FEM或训练。

## 1. 当前事实与执行边界

原owner最新链为`codex/fem-surrogate-comparison-prep-20261020`，本次接入前HEAD为`77119a1d`。旧分支上准备的代码补丁已接回此链，数值核心一致；原3600步方案、共同state0、节点K、eta0、求解精度和初猜网络不变。

必须保留[已消费R2执行记录](complete_execution_20261020/run_status.md)：准确源`d703e3c8`、card `f3cc0463`、Run `pf_hybrid_complete_20261020_r2`。本地最后快照为英国时间2026-10-20 19:06:47，train_A已接受1步，第一步含IO/特征34.2491秒。它只证明当时状态，当前是否运行、是否首停、总费用、完整状态与模型产量均未查明。本轮没有远程查询，不能称R2现在成功、失败或仍在运行。

生产Matplotlib **3.10.3已有真实记录**，不再列为未知；今后仍须在实际任务内核环境未漂移。旧R2源码不含本契约，本地修改不进入它的远端进程；不热换、不重启、不沿旧RunID续写、不把它追认为新契约数据。已经未保存的真实`f_solve`不能从`f_commit`补造。签过的卡、审核、失败和运行收据保留原字节。

[v5准备卡](accepted_state_preparation_card_v5.json)及其执行模板均`execution_enabled=false`，RunID/路径为null。**这是可打包、可核查的代码准备方案，尚不是可启动科学任务。** 当前授权只覆盖本次实现和审核；下一次执行必须先结清R2和预算、在同一任务包络内决定是否还有完整比较的额度与权限。若R2已消耗拟用的fit/3600步，不能借换卡或编号重新获得这些额度。

## 2. 唯一接受态及字段时刻

沿用不可变`AcceptedState`数值数组与fingerprint，另加同一NPZ内的`state_contract`及两项证据数组。契约完整定义见[field_timing_contract_v1.json](field_timing_contract_v1.json)，逐字段表见[field_timing_map_v1.csv](field_timing_map_v1.csv)。数值state_id不因本地元数据补充而改写。

```mermaid
flowchart LR
  A[旧接受态 S_n] --> B[共同机械预测器 / NN仅给damage初猜]
  B --> C[原全空间机械与box QP / 共同Anderson]
  C --> D[final u,d重平衡 / 从固定旧态重建A,r,f]
  D --> E[原fresh力学 / KKT / 历史接受检查]
  E --> F[父状态与物理键 / 字段时刻与数组摘要]
  F --> G[原子提交 S_n+1 / 一步一次]
```

| 数据 | 保存/使用的准确时刻 | 防混用约束 |
|---|---|---|
| u/v、节点d | fresh联合接受的最终场 | NN第三头/初猜不充当接受d；原节点顺序与u交错顺序 |
| A、r、f_commit | 固定旧接受态，加最终u/d的trial，仅提交一次 | r是当前退化driver，不是最大历史；A不随inner累积 |
| f_solve_gp | 最后一次真正求解的damage QP所用系数 | 直接从该QP输入取值；不从最终A推回；与f_commit差值核对原fatigue residual |
| psi_raw_commit_gp | 最终接受u的未退化拉伸能 | 与r分列；原Q4元素/GP顺序，不与active/退化能混名 |
| opaque | 原source支撑，原样继承 | 不解释为本后端新更新的物理通道 |
| 反力 | 最终u/d的fresh平衡 | 同一约束自由度及顺序，同时核当前边界 |
| 特征 | 旧接受态＋目标载荷下共同机械预测器 | 训练前从封存前态和预测器重算；d_target只作输出标签 |

每个状态绑定：共同初态与输入清单SHA、mesh/physics、完整solver settings和coupling identity、载荷schedule/边界、step/cycle/substep/载荷值/分支、所属trajectory、自己的parent state_id。比较时trajectory名称可不同，物理键必须完全一致；父状态各自沿链核对，不要求两臂已产生的状态指纹相同。这里的“时间”是准静态载荷状态，不是墙钟时间或有量纲的动力学时间。

事务仍为原CAS＋临时文件fsync＋原子rename＋目录fsync；新证据与接受态同文件提交，不能只成功一半。非法/过期/降级合同在替换前失败；rename后异常仍是CommitUncertain，须核实真实存储，不能宣称回滚。

## 3. 实际入口如何执行契约

- `solve_step`保留最后QP的真实f_solve与最终raw；原接受判据不改。producer绑定上下文后交原StateStore提交；事件、标签和封存状态带同一契约摘要。
- `StateStore.load`核数值fingerprint、契约、证据shape/hash及证书绑定；commit核父链和不变的问题身份。旧档可读，不能在新链中丢合同，也不能自动升级旧档。
- `fit`只接受完整train_A/train_B/validation各1…600顺序，无漏步/重复/乱序。核状态/特征文件SHA、父链、物理键、settings/coupling、输出证书和事件一致；从旧态及保存的u_pred/psi_pred重算特征，核d_old/d_target。模型收据和冻结推理也绑定同一contract与feature timing。
- `analyze`先核各步对应当前card、同物理键与自身父链，再算u/v/d、A/r/f和反力。不同原始步号、载荷族、初态、精度或字段时刻不能按文件编号直接评分。图中经典臂也核同合同。
- 沿用现有`prepare_hybrid_comparison.py`打本地禁用包，原generic supervisor与budgeted launcher执行未来已准许任务。两个launcher均在reserve/spawn前拒绝disabled或未结清运行的卡。启用检查须读取本地SHA绑定的`hybrid-budget-reconciliation-v1`收据：R2已结清、无active/unknown、RunID未复用、可用步数/fit覆盖计划；该同源同SHA成本收据还须进入prior_costs，由原账本核费用并扣减。当前没有这份真实收据，不能把布尔声明当核实结果。不复用硬编码已消费R2的stage/receive脚本来创造下一次尝试。

## 4. 完整科学比较及判据（原D12不变）

完整计划状态表：[state_schedule_v5.csv](state_schedule_v5.csv)，3606行含6个初态；这是**计划表，不是已接受状态清单**。

| 顺序 | 数据/工作 | 数量与phase上限 |
|---|---|---|
| 准入、已见算子回放与最终分析 | 原输入/源身份、限时Agg/PNG/PDF、原五态算子回放，最后封存评分 | 共用4 hosth；绘图120秒含45秒清理储备 |
| train_A / train_B / validation | 幅值系数.8 / 1.2 / 1.0；NN-off，原受约束FEM＋共同Anderson，各自历史 | 各120cycle×5=600；每条≤20 hosth；合计1800新契约转移 |
| 单次fit | 前两条1200训练、第三条600验证；原4×64图网络、seed、loss、最多20000更新、validation early-stop | ≤6 GPUh；只有完整合格标签才fit；测试不参与选模型 |
| test_reference / test_classical | 幅值.9；分别前态初猜/经典外推；同一强求解器与缓存政策 | 各600，分别≤20 hosth |
| test_hybrid | 幅值.9，冻结NN仅供damage初猜，完整校正、自身历史 | 600；≤6 GPUh |

每臂共同初态/载荷、原全空间K、same physics/precision/硬件；只改变初猜。NN-off不能被削弱成冷启动。train_A开头5步是整条producer的正常前缀，通过自然继续，不另开小试/重置历史。首个科学失败停止，无retry；单子步120秒、max_outer100及原QP/力/KKT/历史阈值全部保留。

原质量与收益判据：mean J≤0.001、max J≤0.01，A/r相对RMS≤0.05、f绝对RMS≤0.01、反力相对L2≤0.01，三臂joint接受与六条轨迹f<1覆盖；经典及神经均达质量后，NN相对前态和经典**完整在线worker wall**分别至少节省10%。记录每轮fresh残差、active/trace/loading变化、QP/LU/缓存及总费用；标签、fit、setup、推理、修正、IO、回退、失败及统一后处理均入总账。新增合同/证据IO不从在线时间扣除。

输出固定step4/304/599/600的共尺度场图、u/v/d及raw/driver、A/f、反力和不可逆演化；未到达就标缺失，不替换成好看步。共同事后分析不进入在线CF/CC/CH，全部计入研究总费用。旧普通算法第2步120秒失败是删失对照，不重跑、不赋予无穷场误差、不宣称其完整轨迹加速倍数。

## 5. 预算：上限模板与当前可用额度分开

| 项 | 完整计划上限 / 可核事实 |
|---|---|
| 数值/训练 | 原计划3600子步、一次fit；并不自动授予再做一遍的额度 |
| GPU | ≤12 GPUh，fit6＋hybrid6；不是预计必能完成 |
| 主机/CPU | 原研究总136 hosth，≤16核，分配上界2176 coreh；所有GPU阶段也消耗host时间 |
| phase合计 | 116 hosth，replay＋analysis共用4h；总上限不能补超单phase |
| 内存 | RAM64GiB、VRAM24GiB上限；实际空闲/共用账户/设备身份须在任务内核实 |
| 存储 | 主输出128＋归档128GiB，要求可用256GiB；详见storage_budget_v5.json |
| 新字段存储代价 | 86756节点/86408 Q4×4GP：两项float64 GP证据每个接受步5,530,112 bytes，3600步新增约18.54GiB；NPZ状态＋标签未压缩payload约86.51GiB，再预留20GiB元数据/轨迹/图/临时空间；仍受128GiB单份硬上限实时约束，压缩收益不预支 |
| 已知旧成本 | R2前625.6987804058秒＋实际dispatch5.258660625秒保留；R2阶段费用尚未结清，不能报当前余135.826h/12GPUh |
| 当前剩余 | host/GPU/数值步/fit可用量均待R2终态账本与producer状态对账；本卡为null，执行前拒绝未结清记录 |

phase6h/600步要求hybrid平均≤36秒；120秒只是一子步上限，不能保证完整轨迹赶得上预算。新增证据IO成本尚无实测；本轮人工测试不能预测大网格速度。若结清R2后不足完整计划，需要缩小能回答的问题或明确新的总额度，不能静默清零成本/fit/尝试数。没有在本轮请求或执行新增额度。

## 6. 数据缺口与旧结论影响

详细逐项[data_gaps_v5.csv](data_gaps_v5.csv)。当前真正缺的是：(1)R2终态/完整费用/已耗fit与步数；(2)新合同1800连续标签和1800测试接受态；(3)f<1的完整加载—卸载疲劳反馈覆盖；(4)同质量三臂在线总时间与新增IO代价。没有新合同合格模型可调用。

已见c1五态可作原算子回放，不能补出1800标签；历史GP合同不自动等价新节点K。旧PIDL与FEM的raw/active混名、PIDL NN d与机械外部d分工、MCS条件端点/未接受峰值、c84诊断缺失仍按逐状态审计解释。本次不会补回失去的时刻，也不改E033/E034、旧首停、c1单次提交或已撤回的旧raw/active结论。新比较能阻止再次混用，不能倒推此前差异全部由时间错位造成。

本方案限定一套mesh/material和既定幅值路径。Gc/alpha_T及变幅loading扩展、跨网格、实验/道路观测与未来裂缝真值仍缺，未加入本预算。开源/文献给出的神经初猜＋数值校正分工已沿用原[定向研究](comparison_preparation_20261020/README.md)，本轮不借外部成功替代本模型实测。

## 7. 这次比较能够回答什么科学问题

| 问题 | 可识别的结果与决策 |
|---|---|
| 在固定物理方程、节点不可逆与单次历史提交下，现有联合求解器能否产生完整可接受疲劳演化？ | 连续接受、f<1覆盖和fresh联合残差/成本回答teacher可达性；若失败，用最后fresh分量区分机械、QP、耦合/历史与预算瓶颈。不能用降能或若干漂亮端点替代 |
| 在这个共同强求解器上，学得初猜是否有额外计算价值？ | 同问题、同质量、完整自身历史的三臂，能隔离NN相对前态/经典外推的在线收益。共同Anderson收益不归NN；NN不利则保留强NN-off方法 |
| 去掉状态/字段时刻混用后，误差发生在哪个物理环节？ | 分开u/v/d、raw/driver、A/f_solve/f_commit及反力，区分初猜偏差、校正后场分支差异、历史反馈和不合法配对；报告失败/缺失而非补值 |

不能凭本比较证明原PIDL差异唯一原因、全局唯一解、材料参数真实、跨材料/跨网格泛化、道路未来裂纹预测或统计显著加速。数值参考是同一受约束问题的参考，不是独立实验物理真值。

## 8. 可执行交付与下一动作

代码与精确源清单：[accepted_state_source_manifest_v5.json](accepted_state_source_manifest_v5.json)；检查收据：[accepted_state_checks_v5.json](accepted_state_checks_v5.json)；独立审查：[accepted_state_review_v5.md](accepted_state_review_v5.md)。本轮测试均人工数组/故障注入，不是项目FEM或训练结果。

本地打包（仅读输入字节哈希，不解码数组；输出fresh目录）：

```sh
PYTHONPATH=source:tools:.:tests /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_implementation_20261019/venv/bin/python tools/prepare_hybrid_comparison.py --inputs-root /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_producer_20261019/inputs_v2 --out /absolute/fresh/local_packet
```

输出`code/`、`source_manifest.json`、`complete_comparison_disabled.json`、`inputs_inventory.json`、tar及build_receipt。现有supervisor的`--check`可对该禁用卡、源包和准确inputs只做身份核查；不会执行科学阶段。

未来任务只有在R2真实状态/成本/次数与完整数据缺口核实、科学执行获准且预算可承担后，才实例化fresh RunID/路径、实际账本/完整费用与准确源审核绑定，检查兼容环境/资源并用原`launch_hybrid_budgeted.py --card <exact enabled card> --package <exact source manifest> --inputs <retained exact inputs> --review <exact review>`单次启动。路径/版本/哈希等机械字段在已获准包络内自行补齐；当前没有发出此命令，也不拿已消费R2许可授权新尝试。若R2已完成，只先按其原合同分析；是否必须重做哪些数据，由缺失字段对科学问题的影响决定，不能先假定全部重跑。
