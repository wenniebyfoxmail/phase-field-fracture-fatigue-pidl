---
storyline_id: S04
experiment_id: S04-E027
protocol_revision: v1-source-faithful-P-20261018
status: preparation
---
# 固定c20s4的FEM监督与联合机械微调

Owner：本对话01a14bc7-fd2a-73e1-9d0f-de457ba1dcc0；沿用唯一方案`../fem_synthetic_augmentation_plan_20261017.md`的A。用户2026-10-18批准本地接口/三臂代码、必要检查及独立代码审查，**不批准训练、FEM、远程预检或运行**。本任务沿用干净worktree/branch `codex/fem-synthetic-augmentation-design-20261017`，起点ea421670；只改本Experiment、专用模块/CLI/测试与复用核查，其他owner源码和档案不改。

## 2026-10-18 实施前源码修订

v2方案对P的转录错误按真实E011目标纠正：`L_P=log10(E_el+E_d+E_irr)+1e-5*sum_{name contains weight}(parameter²)`，必须正能量，不加epsilon或重写负值。PIDL不可逆容差`.005`、gamma16875；FEM参考的`.001/421875`不移给PIDL。manual L2仅P保留，Adam weight_decay仍0。S=Lsup，C=Lsup+.1Lmech。此项尚需本轮exact代码/协议独立审查；旧Pro设计审查不冒充已覆盖本修订。

## 固定合同

- synthetic，已看过的单个状态/horizon0；不是新留出、泛化或自主演化。参考只取E011 MCS c20s4 outer18，无history commit。
- 精确四个FEM文件：`output/mcs/c20_s4/outer_18.mat`、同case的`case.mat`、`inputs/common_common_initial.mat`、`inputs/c0020_s003_post_commit.mat`；身份沿用原retrieval/input manifest。初始化只取绑定Q4生产archive的`best_models/trained_1NN_98.pt`，不取checkpoint内前态、不更换缺失模型。
- 三臂同一8×400三输出TrainableReLU、原始坐标/整边lifting/nonsmooth映射。实际shape/GP语义/前态/自由DOF/参考力/边界必须检查；不clip预测，不重新commit历史。
- P1500；共享监督前缀1000，S续500，C复制前缀全部参数/Adam/RNG后续500；3500唯一更新，seed1/float64/Adam1e-4(.9,.999,eps1e-8,weight_decay0)。C/S采样流相同，只有机械项不同。
- 全域与Z=`0<=x<=.5,abs(y)<=.03`各半质量加权监督；Us=.11999988；损失/机械归一、active定义、原始可行性代价与NA规则沿用A。唯一探索主读数Eactive(C)/Eactive(S)，方向容差1e-8，无显著性/综合成功承诺。无独立样本，不做伪置信区间。
- 参考机械原生向量重放maxabs<=1e-10、free norm<=1e-8；这些是已有一致性屏，不把模型性能阈值前置。FEM前态/当前trial f不可由PIDL状态替代，f不直接进入机械力。
- 上限2 GPU小时（含三图预检、评估与保存）、32GiB host RAM、2GiB输出；Run/producer身份和硬件可行性由HQ统一决定。Mac禁训练；无批准不读初始化权重、不进入优化循环。无重试、扩容、换机、换seed或新留出。

## 交付与当前限制

代码与轻量测试不等于已运行。必需交付三臂固定终态/数值分母、全域/Z u/v/d/raw/active、force/reaction/可行性、0/1000/1500结果、实际预测场/同色标图、曲线及README_analysis；没有真实输出不生成“结果图”。当前初始化模型仅有原producer路径，未发现本地文件且不远程取回；正式数据身份/可用性若未闭合不能冒称完整Code Ready或Run Ready。旧负结果与旧判据不改。


## 2026-10-18 非训练准备检查

专用模块`source/s04_e027.py`复用本分支原生Q4/网络/constitutive helper；CLI`SENS_tensile/run_s04_e027.py`默认无执行，须显式prepare或未来execute+HQ grant，Mac执行禁止、当前init身份空则强制拒绝。13个轻量单测通过，包含原生能量与FieldComputation等价、力有限差分、damage机械梯度、无重复质量权重、非空Adam状态/RNG隔离复制、坏输入/禁止运行保护。没有optimizer.step、生产训练循环或远程预检。

指定四MAT实值校验和参考重放通过：全力maxabs差8.60543e−17、free norm3.77612e−15、raw gap3.02002e−12、trial history gap1.72392e−12、BC误差0；这些是接口/已有参考数值的一致性，不是新方法结果。摘要在nontraining_checks.json，原准备收据在本地`local_archive/experiments/S04-E027/preparation_20261018/`。

当前初始模型未在本地找到且无精确字节身份，data_lock明确null，execute必停；不能用随机初始化、晚一帧或旧UV头替换。独立审查应将源码正确性与数据身份未齐分开；完整Code Ready/Run Ready不得因13 tests通过而自动宣称。

## 2026-10-18 独立审查后的交付补充

首轮只读审查绑定c0113d565799f08e91be721f8019edb8d6767d9c：核心接口、三臂目标、native Q4/damage梯度、分叉与禁止运行保护未发现关键算法错误；独立重跑13项测试和四MAT参考重放通过。审查提出三项P2交付缺口，修复后须再次绑定exact commit复审：

- 每更新记录实际目标分量；固定0/1000/1500另存完整指标及L_U/L_D/L_mech/L_P和参数梯度L2。诊断使用独立固定seed1采样，不推进任何训练采样流；C的0/1000复用common/共享前缀，绝不另跑前缀。metrics.png仅连接三个固定观测点。
- P、共享前缀、S尾段、C尾段分别计时和记录CUDA allocated/reserved峰值；时间包含该段约定的检查点评估，显存是包含其他常驻模型的进程峰值。实际执行总成本只计一次共享前缀；概念S/C成本各自包含前缀，峰值取max而非相加。最终渲染/保存等总开销另在全程receipt体现。
- 四图各自产生同stem说明，完整README自动带入exact输出/commit和主表及解释边界。数据锁复制进运行目录。实际结果生成后仍须人工检查图和独立证据审查，源码存在不等于图已验收。

聚焦复审识别并修复一项新增诊断副作用：跨臂L_P只在能量为正时定义；S/C若非正，原始能量保留且L_P/其梯度记NA及理由，不新增S/C停止条件。P实际目标仍严格正能量、无floor。新增无step单测覆盖该边界。

## 2026-10-18 最终代码准备结论

最终源码91537ce240d892fc71f714cceedc1cea92c32b1b经只读独立复审，15项轻量测试独立重跑通过，代码准备范围无剩余已知阻断性问题。详见`code_review_20261018.md`。完整Code Ready/Run Ready仍未签：初始化权重的精确字节身份/可用性未齐，producer三计算图资源预检未做，运行授权仍由总部决定。未训练、未FEM、未远程、新留出未读。

## 2026-10-18 初始化身份澄清（不改设计）

本地源码与原manifest匹配，确认原Q4运行trained_1NN_98应为c20s3、U=.08999988结束时的裸网络state_dict；三臂仍在目标U=.11999988共用该参数，历史只取FEM。原NCP contract仅绑定97/99网络与history98，没有trained98自身条目，旧“已绑定权重”措辞更正为“由原保存源码与状态映射确定的唯一期望文件”。其自身hash/bytes仍未知，所查本地文件名清单未发现正确运行映射。详见code_review_20261018.md及initializer_identity_20261018.json；只需补这一确切文件及自身身份收据，未换初始化/未改lock/未重复15项检查与代码审查，无远程或训练。
