# D15：R3第2子步的残差反弹与下一耦合方案

2026-10-20；沿原D12/D13/D14，目标仍为在同一物理接受精度与真实自身历史下，完成前态/经典/神经初猜的完整比较。本轮 `continue / repair`：只分析已归档R3/R2 JSONL、核对冻结源码与方法文献、制作图和提出方案。**没有SSH、FEM重算、场数组重建、训练、solver实现或重跑；R3失败和一次许可已消费的事实保留。**

结论：机械内层复用有效，前三次Anderson也有效；但加速提议在第5轮耗尽，之后普通map没有全程残差保护。联合残差第17轮最低仍高于门槛，第18轮起回升，R3仍保留所有这些普通点。已证实的是这个控制机制和观测到的误差增长；未测得Jacobian谱、病态程度或主导节点，不能把“存在某个不稳定特征值”写成实证。建议下一候选是**有界全程保护的混合外层：持续有用的Anderson＋受约束约化Newton/Schur方向＋真实原QP最终认证**，保留R3已成功的机械后端，避免只改提议次数或延长时限。

## 1. 复用、身份与图的来源

- R3：`pf_hybrid_solver_v6_20261020_r3`，执行源`9216909dffc90df09d60da8cfb076c2be32c79f5`；原artifact/card见[准确执行复核](execution_r3/execution_review.json)。
- 原始日志：`local_archive/research/hybrid_solver_repair_v6_20261020/execution_r3/terminal_evidence/archive_train_A/{iterations,work_trace,events}.jsonl`。全部8份已取回日志先按remote inventory逐份bytes/SHA核验；train_A/failure.json因SIGTERM未落盘，不伪补。
- R2对照：`local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/timeout_diagnosis_20261020/`；复用`analyse_timeout.py`分组思路。没有重跑R2。
- 新解析、CSV、图及机器可读结论：`local_archive/research/hybrid_solver_repair_v6_20261020/execution_r3/analysis/coupling_diagnosis/`。`analyse.py`仅标准JSON解析及Matplotlib作图；栈配对每个start/end，机械子块从不再加到机械父块上。两图选取全部已存第2步fresh记录，不挑最好片段。
- 科学源码复核：`hybrid_coupled_acceleration.py`的`propose/trial_improves`、`hybrid_incremental.py`的`rejected/last_kept/next_guess`、`hybrid_mechanics.py`的GMRES/真实残差/回退路径；以冻结packet的源为准。当前报告不是修改原运行卡或重签其源。

![R3残差转折](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v6_20261020/execution_r3/analysis/coupling_diagnosis/r3_step2_residual_turn.png)

看见什么：蓝线先降，三次加速后进入普通map；最低点仍在接受线以上，之后回升。下图是固定点RMS与它的连续比值两个标量，采用双轴。
说明什么：需要修外层如何选择和保留工作点；比值大于1只是这条轨迹的标量增长，不是已测谱半径。

## 2. 按真实顺序重建“先降后升”

联合merit `m`为原有约束/KKT/投影、力平衡、联合L2、边界与疲劳一致性残差除各自原阈值后的最大值；`m<=1`才同时过原标量门，本身还不能替代最终当前K pivot及提交合同。

| 阶段 | 真实读数 | 对应控制行为 |
|---|---|---|
| outer1–2 | m15.0967→9.88541；8.55→15.85秒 | 普通map，累积Anderson窗口 |
| outer3–5 | m6.81066→4.92988→3.49756；25.59→46.33秒 | 三次Anderson均strictly improve并保留，0拒绝 |
| outer5后 | `step_budget_exhausted`一直到outer38 | `max_proposals=3`是整个子步的总提议数，不是重启窗口配额；即使三次全有效也永久退出加速 |
| outer6–17 | m3.14380→1.78274568；best在134.063920秒 | 普通map继续下降但越来越慢，仍未达原门 |
| outer18 | m1.78345185>1.78274568 | 初次反弹；仍`kept_as_iteration_point=true` |
| outer19–38 | 固定点RMS比由1.00465升至1.12011；m最终6.53011 | 全是普通map；38轮共0拒绝，全部保留；最后joint L2也超门 |
| 300秒保护 | 第39个QP已返回，后续mechanics/GMRES未闭合 | 不能把未完成块当零成本/已完成，或推断它本会成功 |

m和固定点RMS的最低点并不完全相同：m在17轮最小，RMS在18轮最小，RMS自19轮开始增长。不能把两条标量当成同一残差。最后fresh检查为294.013481秒：KKT_inf6.53011e-7（门1e-7），damage KKT_L2约5.20166e-6（联合L2门4e-6），Ru_L2约8.23e-11、fatigue一致性0。39QP只是已完成work block，38个QP的迭代/status字段在decision中持久化，最后一个没有额外迭代数记录。

**源码原因是明确的**：`rejected = was_trial and not passed and not trial_improves(...)`，所以strict-merit guard仅保护pending Anderson候选。普通map即使比上一轮更坏，仍走`elif not passed`，覆盖`last_kept`并把`d,u_cache`推进为新点。`last_kept`是“上一保留点”，不是全步最优点；没有best checkpoint来阻止134秒后从1.783滑到6.53。此次不存在Anderson候选反复拒绝；扩大`max_rejections`的修复在R3没有被实际使用，不能给它记收益。

## 3. 哪些解释有证据，哪些还没有

1. **疲劳因子反馈不是该次反弹的已见驱动。** 所有38次完整检查`fatigue_below_one_gp=0`，即f始终1，fatigue一致性残差0。加载掩码第一次变化在outer21，迟于outer18反弹；它变化会改变trial A/r，但在当前f=1分支不能通过f改变这次damage方程。仍须保留原A/r历史规则，未来f<1时不能冻结f。
2. **不是已记录的大规模拉压或边界切换。** 全38轮345632个GP均trace-positive、0次trace切换；outer18–20节点active变化数也均0，加载掩码变化0。其后少量节点active释放/激活可能参与非线性增长；日志未存每节点梯度/向量，不能排除其贡献或定位裂尖。
3. **机械块没有表现为未平衡的主门。** 最后Ru_L2仍远低1e-8；QP决策记录均`solved`，100或125次迭代，roundoff projection约1e-22。然而QP解的是固定u/f的子问题，重新平衡u后ψ及fresh damage算子改变，故“QP solved”不能证明联合KKT。缺少每个冻结QP的独立fresh KKT、当前K中间pivot/条件数及GMRES逐调用返回info，不能绝对排除内层误差放大或条件性问题。
4. **最符合现证据的机制**是普通交替map残差在该支路变慢后增长，三次有用的外层校正在早期用尽且普通步无保护；低维secant的完整向量、方向余弦和Jacobian未落盘，不能证明其某个本征模态或ρ(G')>1。即便某能量下降，残差也未必单调；本次未保存逐轮总能量，不以降能解释曲线。

在固定分支的局部表达中，若联合方程Jacobian为`[[A,B],[C,D]]`，对R3的f=1、固定trace/约束分支、块可逆且在光滑非活动子空间上，原交替map含`D^-1 C A^-1 B`，真正damage约化切线为`S=D-C A^-1 B`。未来f<1且QP使用lagged f_solve时，实际G'还含显式滞后疲劳反馈，不能直接将完整历史链导数的D/C代入这条Gauss–Seidel表达；下文S是原reduced残差的切线，应与实际G'区别。这是为什么“每块解得更快/更准”和“整体方向可靠”不同。它是下一方案的机制推导，不是本次已测矩阵。若某实增长模态λ>1，单纯ω∈(0,1)阻尼的模态仍为`1+ω(λ-1)>1`；当前没有测得λ，因此也不能把阻尼当作必然有效的修复。

## 4. 修复的实际收益与剩余成本

![R3工作成本](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v6_20261020/execution_r3/analysis/coupling_diagnosis/r3_step2_work_cost.png)

看见什么：单次机械再平衡明显更便宜，但更多外层调用积累了QP与机械费用。左图R2/R3有不同截止窗口；LU/GMRES已含在机械父块内。
说明什么：保留机械后端，下一重点减少无效耦合工作，而非继续围绕LU或NN训练投入。

| 读数 | R2 | R3 | 能下的判断 |
|---|---:|---:|---|
| 已完成新LU（第2步） | 9次/52.807秒 | 0次 | 旧LU仅预条件当前K的策略确实替代了这批重新分解；不称“LU复用为当前精确因子” |
| 已返回GMRES调用 | 0 | 82次/70.373秒 | 不是82次inner iteration；未完成第83调用不推断 |
| 重平衡单次中位数 | 7.784秒，n8 | 2.884秒，n38 | 观测降低约62.9%，非有重复/随机化的纯因子A/B |
| 前3次fresh elapsed | 51.102秒 | 25.587秒 | 相同目标载荷、几乎同merit前缀更便宜；不是完整轨迹提速 |
| 3rd fresh m | 6.81066095 | 6.81066144 | 前缀联合残差近同；不能据此替代完整场差检查 |
| QP单次中位数 | 2.882秒 | 2.871秒 | QP内核未见同量级提速 |

R3已完成、不重叠root工作294.782秒：mechanics121.339（41.16%）、QP112.508（38.17%）、damage装配34.043（11.55%）、独立force审查23.599（8.01%）、其他3.293（1.12%）。不是“剩余时间主要是日志”：物理子问题和反复装配仍占绝大多数。最后未闭合父子mechanics/GMRES、块间隙与终止延迟另列，不能再加一笔完整GMRES到mechanics上。

300秒新保护按卡真实触发、旧accepted状态与首停合同受保护，属于控制记录有效；延长本身不是数值修复收益。R3没有新增f<1接受覆盖、完整轨迹或NN训练/比较。

## 5. 推荐的下一候选：有全程保护的混合外层

不改物理模型、材料/加载、原接受容差或历史规则；不把“3改成更多”“只加阻尼”“再给时间”单独作为下一主方案。比较三个层次：

| 候选 | 作用/证据 | 限制与决定 |
|---|---|---|
| 持续有界Anderson＋统一残差保护 | 直接利用R3三次全有效、plain map无保护的证据；实现增量最小 | 值得保留为廉价proposal；没有证据保证后段仍能提供下降方向，不单独承诺根治 |
| **混合约化VI Newton/Schur＋上述保护** | 显式处理u–d交叉反馈，而非只以QP固定u解耦；可复用当前机械/装配与低维活动子空间 | 推荐；新增切线和全局化需人工验证/独立审查，有实现与inner-solve成本，无已测速度保证 |
| 裸Newton、单纯增时/加训练/放宽门 | 没有对应本次证据，可能换分支或掩盖未接受状态 | 不推荐；新模型/材料数据也不能修复此标签生成首停 |

### 5.1 统一工作点接受机制

- 记录当前点、按统一m_work定义的best点（d/u/fresh审查/线性缓存及域一致快照）；**原不可逆lower始终d_n**，不能把best数值迭代当新的不可逆下界。
- 所有普通、Anderson、Newton候选统一以可定义的工作残差`m_work`作fresh全局化：取原阈值归一化的原方程/VI投影、力、可行域及边界分量的最大值，fresh f_trial均从同一旧态构造。中间无QP的点没有真实f_solve，QP–提交疲劳一致性分量必须记`NA`，不得假设为0或伪造系数。所有候选和其基点都用同一`m_work`比较；下降才保留，未下降则完整回滚并有界回溯或换方向。只回滚子步内部工作点，不改accepted旧态。`m_work<=1`绝不等于原最终门已通过；真实QP后的`m_accept`才是完整原m。
- Anderson仍depth3/同投影和信赖约束；改为按剩余总函数评估/时间预算自适应使用和重启，不以“成功3次”永久关闭。不能把仅删掉cap当收敛保证。
- 回溯/拒绝/证据写入/Schur动作计同一步起点和预算；后续准确卡应显式冻结总fresh候选数（建议仍不超过原100）、每方向有限回溯数、线性迭代与同300秒，不以一个outer包无限内部尝试。找不到合格方向仍停止，不放宽门。

### 5.2 复用力学消元，解原约束方程

固定旧态S_n，先求当前damage下机械平衡`u=U(d)`。用原装配定义

\[
R(d)=R_d(U(d),d;f_{trial}(S_n,U(d),d)),\quad
F(d)=d-\Pi_{[d_n,1]}\{d-\sigma R(d)\},\quad \sigma=1/\text{原damage gradient scale}.
\]

预裂纹/旧d=1固定节点直接消元，其余节点通过投影残差的活动/非活动集可释放，不由NN/前几轮active mask永久冻结。固定分支时`U'=-A^-1B`、`S=D-C A^-1B`；投影选择矩阵P下`F'=I-P(I-σS)`。实现matrix-free Schur向量积，复用当前A分解对多个rhs作用，以原damage Hessian在非活动集上的块作预条件，不显式生成稠密S；不能默认S正定。若内层A逆采用可变不精确迭代，须相应采用支持可变预条件的线性方案；首版可用每Newton点固定当前A因子，避免混用普通GMRES假定。

重点是**原残差的链导数**：后续f<1时D/C须包含`∂R_d/∂f·df_trial/dd/du`及原loading max的分支；不是把f(u,d)代入能量再对能量全微分，后者会改变原R_d物理方程。R3 f=1仅是该次简化，不能永久冻结f/历史。近分支切换用一致广义切线并检查方向导数；机械真实残差、当前K资格与坏pivot首停继续保留。

用上述m_work的残差回溯/信赖约束全局化Newton方向；数值正则只作用搜索方向，不加入物理R_d/材料残余刚度或接受门。初始少量G/Anderson可把点送入可解区域；停滞或增长时应换Schur方向，而非持续接受恶化plain map。该方案没有全局收敛或唯一物理分支保证。

### 5.3 D13真实f_solve与最终认证必须保留

Newton/Schur生成的只是内部候选，不是直接accepted状态。中间自然残差评估可以不跑QP；**不能把每个Newton点立即强制过一整轮G来覆盖其方向**。但当候选接近原接受门时，必须实际执行一轮原`damage QP → mechanical re-equilibration → trial history → fresh damage/force/fatigue audit → current K LU/pivot`认证，记录该次QP真实的f_solve_gp和最终trial的f_commit，只有这个完整认证的m_accept及其他原门全部通过才输出proposal、绑定逐字段时刻并CAS一次提交。

如果该认证改变d/u后使fresh条件再坏，仍不提交，回到受保护工作点/继续有界求解或停止。不能把f_commit复制成f_solve冒充实际QP系数，也不能取消最后QP而宣称D13合同原样保留。中间Newton点不作为label；真实accepted历史始终仅由最后认证态、同一S_n构造。

可直接复用：`MechanicsWorkspace`的装配/真残差/精确域缓存、`assemble_nodal_qp`及原gradient/KKT、`solve_nodal_qp`的warm-start/基线/最终认证、`trial_history`、`bind_proposal`、`StateStore.commit`、pidfd保护与case费用记录。新实现仅外层策略、耦合Jacobian向量积与活动集/全局化；不是重写网络、材料或历史内核。

### 5.4 下一验证应回答什么

本轮仅方案，不生成启用卡、不实现新solver、不重跑。后续实现若获授权，先人工小系统核验残差/切线方向导数、边界活动释放、真实f_solve/f_commit、best回滚与所有候选预算计数；这是新切线/操作合同的必要实现检查，不插入新的大网格反复微型FEM尝试。独立审核后，如获得**新一次科学尝试许可**，沿原完整比较路线一次推进：首个循环5子步为正常前缀，随后600步轨迹及原各标签/测试阶段；不重跑R3作为人为负基线。数据/预算边界另按真实剩余额度形成准确卡，不在此凭空扩预算或承诺耗时。

应见到的签名：第2步m穿过1并经真实QP最终认证；不是只有更小固定点步长或一次降能。完整加载/卸载/后续f<1覆盖若未出现须保留缺口；所有三臂用同一新耦合策略和原质量门。若严格保护后无下降方向、切线检查失败或Schur成本仍过预算，保留各自失败，不借额外训练救标签。分支不同仍须按原场/历史/反力质量比较；同KKT不等于唯一/物理真值。

最小补齐的durable读数：每次机械GMRES内迭代/真实残差及目标/回退/当前因子身份；最坏KKT节点的index、符号、距lower的gap、active类别；原冻结QP和重平衡后的fresh KKT分别记录；m_work/m_accept及不适用的QP操作分量明确分列；best/stall/last若保存trial向量须标为未接受，不进入标签。已有失败轨迹不重算以补这些缺测。

## 6. 方法来源与迁移边界

- [Farrell–Maurini原稿arXiv:1511.08463v2](https://arxiv.org/abs/1511.08463v2)，本地完整22页已核对身份及定向方法正文。§2.3–2.4（PDF pp.7–8）描述分块与带回溯主动集Newton组合；§3.3（pp.9–10）给块Jacobian及Schur预条件，允许非正定。本文支持方法结构，不验证本项目Amor/Carrara、自然投影残差、D13操作证据或速度；上文是本项目迁移设计，不是作者算法逐字复现。
- 复用已归档[Storvik等2021](https://arxiv.org/abs/2008.11787)，19页原稿§3.3/Algorithm3（pp.6–7）按残差持续加速及切换，不等于当前全步固定3提议上限；模型/历史场及不可逆实现不同，不能据其结果许诺本项目收敛。
- [PETSc当前官方SNES手册，Variational Inequalities](https://petsc.org/release/manual/snes/#variational-inequalities)提供box约束的reduced-space/semismooth Newton接口及监控。这里只作方法参照，不表示现服务器已装或本轮要装PETSc；首版可复用现有SciPy/装配接口。

检索是本次日志诊断的定向方法lookup：agent-reach Exa一次查询＋arXiv原稿/官方手册核验，复用既有文献；不是新系统综述或首创判断。原报告《Deep Research - 疲劳相场FEM的神经初猜与受约束校正》继续维护此问题，不另开重复路线。所有新建议均未实测。
