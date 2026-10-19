# 完整混合框架实现 v2 — 2026-10-19

用户授权：实现受约束求解、历史与网络接口、核查既有标签、代码复审与完整验证预算。禁止本轮训练/新增FEM。延续已复审design_v1；当前D7为整套方法的工程实现，不恢复逐开关研究路线。

## 已实现的闭环

- `source/hybrid_history.py`：不可变接受态与native GP A/r/f，严格拒绝不合格前态；trial从固定前态重建，卸载保存当前driver而非历史峰值。数组以不可变bytes为底层。
- `source/hybrid_damage.py`：复用既有AT1能量装配，但用完整节点lower/box/硬线；固定DOF精确消元，OSQP完整自由空间求解，活跃约束可释放。求解器微小越界仅在声明QP精度内恢复可行，最终原算子KKT必须另查，投影不算收敛。
- `source/hybrid_incremental.py`：统一native Q4后端、mesh/material身份、显式Gc/ell=w1、共同机械预测、一次NN初值、u/d/f固定点、最终重新装配damage与机械残差。返回proposal而不修改前态；失败保留逐调用时间/工作账本，不重试、不推进历史。所有缓存仅为本次调用内精确相同d的u，不跨加载步复用。
- `source/hybrid_transaction.py`：本地POSIX单文件原子替换、排他锁、前态digest/version CAS、单次提交及restart。写入/替换前故障不改变旧态；替换后fsync故障属于commit outcome uncertain，必须核对durable版本，禁止假报回滚或盲重试。这是对抽象设计中“完整回滚”的必要IO细化。锁若因进程崩溃残留，先人工核对再处理。
- `source/hybrid_network.py`：27维可追溯特征、native网格与ell粗图、4消息块/64宽度/单d头参考网络，以及冻结推理接口；GP投影只用于特征。需明确trained manifest、权重、物理身份、归一化与训练receipt；未提供模型时NN-off，不把随机网络作为混合结果。无训练/优化器/自动checkpoint加载。
- `tools/audit_hybrid_labels.py`：既有已见c1五态只读核查与prospective标签metadata合同；不遍历关闭holdout、不补解、不生成标签。metadata通过本身不代表数组或物理资格。

## 工程检查与科学计算边界

新测试使用解析对角QP、mock耦合固定点、人工history及临时事务文件；真实Q4仅做一单元装配/特征结构检查，没有新FEM求解或训练。旧QP/机械模块的轻量既有回归同时运行。闭环mock特意使局部QP收敛后最终u改变，要求>10次联合迭代，防止沿用旧KKT。

运行环境：独立开发venv（system-site-packages，Python3.12.2、NumPy2.2.6、SciPy1.14.1、Torch2.11.0、OSQP1.0.4），未修改基础环境。初始系统Python无pytest、conda缺OSQP以及未设PYTHONPATH的收集失败已修正；不将依赖错误解释为方法负结果。

核查命令：`PYTHONPATH=source:. <dev-venv>/bin/python -m pytest -q tests/test_hybrid_incremental.py tests/test_native_q4_damage_qp.py tests/test_damage_conditioned_equilibrium.py`。收据见implementation_checks_v2.json。新增源码不改变旧PIDL runner、旧FEM或冻结实验协议。

## 现有标签结论

不是所有既有FEM都只有软约束。2026-10-16 c1 repaired臂已用节点lower/box/硬线并fresh联合接受，具5个连续候选，不能把它整体排除。只读核查五个已见accepted MAT中的pre/candidate/proof/proposed数据，确认[0,1]、无回退、旧lower等于前态、A映射、相邻链和版本；未读其他轨迹或关闭评估数组。

但加载s1–s4保存的可行damage梯度Linf为2.992e-7/9.628e-7/2.209e-6/1.878e-6，高于本实现当前unit-scale 1e-7工程默认；旧4e-6 L2协议结论仍原样有效，不放宽它，也不事后追认新合同。s5为0，但其前态链尚未满足新接受合同。还缺新后端原算子/阈值绑定和目标载荷下共同u_pred输入资格。五端点均f=1，不能建立f<1反馈或整轨迹train/validation/test划分。故本次确认5个可回放候选、0个可直接投入新框架训练的已认证标签；这不是证明全部远端档案不存在合格数据。

其他资产：C/W0/W25为单已见c1s1软罚PIDL端点且有负damage/回退，不是相邻合格FEM标签；旧E003 c83 trial-f端点未通过其原站定性门槛；历史完整FEM/PIDL轨迹仍为其原问题参考，不能未经核查改作新节点K的teacher。保存的c1候选可用于未来只读算子/特征回放；本轮不靠补FEM使它们变成标签。

## 适用范围与未交付的执行能力

此实现是整套方法的库/API与开发检查，尚无训练模型、producer runner、远端部署、参数/轨迹验证或实测提速。当前机械后端仅支持位移控制、无体力/外牵引、平面应变AT1/Amor、eta=0；未支持载荷类型须拒绝，不能套用无外力公式。零模/近奇异沿用原后端拒绝策略，不自动加eta或伪逆。Picard失稳/达到cap直接失败，不自动换算法。

数值默认精度为显式工程候选：force fixed scale与damage fixed gradient scale均由调用方提供，Ru_inf/scale≤1e-8、damage KKT及投影≤1e-7、bounds≤1e-10、f一致性≤1e-8、QP eps1e-10、100outer/50mechanics/200000QP。它们不是旧正式协议替代品；未来卡须绑定单位、尺度和最终精度。现场更换精度需要前瞻变更，不能看结果调阈值。

库的wall cap在原生调用边界检查，OSQP另有time_limit；不可中断的稀疏mechanics可能越过软边界，未来producer必须有外部watchdog控制硬总预算。backend.setup_seconds、network.setup_seconds、逐调用work、StateStore.last_io_seconds都须计入完整账本；GPU/CPU峰值内存及训练/标签成本由未来runner测量。不得只报NN推理时间。

网络与经典外推对照的输入接口已经具备；经典初值由调用方声明可行数组，前态为默认。完整方法验证需同后端NN-off、经典外推、NN初值并列，以及历史PIDL/FEM描述性参照；不需为每个模块另起一条科研最小验证路线。

独立代码复审见code_review_v2.*（v1问题及修复轨迹保留）；预算见validation_budget_v2.md/json。科学执行仍不在本轮授权内。

## 独立复审修复（v2）

保留整数且不可写的predictor DOF输入；未标识model_id的predictor在任何mechanics前拒绝；证书区分attempted model、实际初值来源及fallback后的NN-off。既有数据摘要改为1份已见c1序列、0份合格完整轨迹，避免把5个子步称完整训练轨迹。预算补入12h GPU任务host CPU，CPU总cap136wall/2176coreh，所有工作共享最多16cores。原v1材料按原commit留存，未改变科学精度或执行任何新FEM/训练。
