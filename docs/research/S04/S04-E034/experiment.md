---
storyline_id: S04
experiment_id: S04-E034
protocol_revision: v1-finite-raw-reaction-F8-F802-20261019
status: code_ready_awaiting_HQ_evaluation
---
# E034：反力保护下的实际有限 raw 双臂比较

目的：相对实际 E032 起点，达到原 raw-global RMSE 至少下降 0.1%，同时原十一保护、冻结共同下降锥、2%原头半径和 top/bottom 各自反力误差不增加。区分当前八轴中的有限选择与原802坐标空间的预算内表现。范围仍是单一已暴露 synthetic c20s4 / horizon0 / seed1 的状态修复；不证明物理演化、teacher真值、泛化或任何空间全局无解。

本轮：用户 2026-10-19 明确授权按已有双臂方案准备代码、必要检查及独立代码审查。**仅本地合成 fixture 和 import；禁止资源预检、SSH、真实PT/模型加载、真实梯度/拟合及运行。** E033原代码、首停和结果封存。新协议独立登记，设计复用 [原完整方案](../S04-E033/finite_reaction_comparison_plan_20261019.md)，不更改其中目标、约束或预算。

## 比较与实现契约

- Z0 是实际 E032 缓存；H0 是 E033 既有终点，均不重算搜索。H0只作历史整体配方比较，不是单因素因果消融。
- 固定先 F8、后 F802。各自从 E032 零增量独立 SLSQP 开始，不顺接、不热启动、不共享 optimizer。每臂 maxiter60、ftol1e-12、最多120个不同实际参数点、600秒；剩余额度不转移。
- 目标是原生Q4实际 raw 相对平方误差。原十一项实际平方值各不增加，top/bottom 反力相对各自 E032 与 FEM 非零误差平方分别<=1。UV/u/v六约束直接从仿射特征场计算，等价于精确二次式。没有切线目标、任意反力权重或有限差分优化。
- 原802梯度乘 R，除以其投影固定B8的范数；两臂使用同一分母和 kappa=.04418604213300339，F8精确嵌入F802。保留球约束 ||h||<=1；R=.039821608331992005。
- SLSQP搜索使用闭合的不增约束以保留零点可行；raw<=.998001与global UV RMS<1-1e-8共同构成成功接受条件。所有实际保护、冻结锥/球均无容差放宽。
- 首次符合目标的点立即通过 functional actual NN forward 重核实际13值/物理身份，与affine场<=1e-10，成功即结束该臂。试探点从不改正式参数。每臂最多一个成功终点checkpoint；未达返回精确缓存E032，不能挑微小收益替代原目标。
- status0或事前60次迭代status9且数值/资源/来源有效才是预算内未找到，可继续另一个事前臂。其他solver错误、非有限、物理/身份错误、600秒、121点或共享/整包超限立即停止整个包，不重试/换卡/换权重/换solver。
- F802成功后保存B8内外分解。仅outside norm与maxabs均<=1e-12，允许共享预算内至多一次投影点 actual forward 复放；必须同一无slack目标实际通过才认定八轴可表示。outside>=1e-8只证明本次见证含解析平面外分量，不证明八轴不可达。

## 来源及固定物理语义

[data_lock.json](data_lock.json)绑定原四MAT、原S1500、E032五文件，以及E033 basis/full-gradients/fields/scores/receipt。原S1500 hidden/activation/第三头不变；UV起点实际E032 theta；外置physical d是E030实际值，经E031/E032逐位继承，不用FEM target d，不用E030训练hidden。c20s3 lower/history/fatigue不动。

新源文件 source/s04_e034.py；显式入口 SENS_tensile/run_s04_e034.py；未来一次性启动入口 SENS_tensile/launch_s04_e034.py；标准库独立阶段watchdog source/s04_e034_watchdog.py。复用原E027/E028/E031/E033原生Q4/force/fields定义，不修改旧模块或默认训练路径。Mac仅合成fixtures，不触碰真实输入。

## 原预算与未来准入

新增整包<=0.5 GPUh，旧保守累计1.108339654581623，最坏1.608339654581623<2。各臂600秒，共享准入/零点Jac/输出绘图归档480秒，不转额。臂内输出同时扣共享导出时间，保守重叠计时。独立watchdog在阶段额度前5秒TERM、到期KILL；外层1790秒TERM+5秒KILL覆盖worker import至退出。原0.5和2总限不变。

唯一GPU5/UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，未来授权后再实时核验>=20GiB空闲、SM0、无计算进程、host RAM/规范磁盘，allocator<=free-1GiB且保持1GiB余量，RSS<=32GiB、输出<=2GiB。所有新run/cache/tmp和archive在规范/mnt/data2私有fresh目录。不能查询当前卡、预留或启动。未来用独立无hardlink/alternates的exact clean clone；grant须新确切commit、review与人方授权，不沿用E033。

## 最小完整产物与判读

所有不同点保存系数、13实际值/比值、锥/球、calls、精确Jac批次、solver及时间。第120点可完成判定，第121点禁止进入物理评价。shared零点13项Jac在两空间中核验嵌入，并回放原11冻结梯度。共享features只保存一次，不为每点保存802×N速度。

共享Z0、每臂实际达到的15/30/60主迭代及首达标/最终点输出u/v/d/raw/active、有符号误差、force、ε/σ和全域/Z/左窄带/顶层统计；未到里程碑明确列缺。全域与局部视图共用native GP4支持和未截断色标；trace横轴是不同参数评价序号，不是物理时间。报告反力双端误差、free力及有符号竖向合力、早期global-active代价和相对E031的u残余。checkpoint明确外置physical d；完整hash清单和来源/resource回执。

F8成功即证明已有八轴足够此次有限目标，优先简单方案。F8未达/F802成功需结合B8分解与复放解释，不能宣称八轴全局无解。两臂有效未达则停止当前冻结头/半径/锥/预算配方追加，回HQ讨论机制路线；工程停止则比较不完整，不能算方法/容量失败。

结论：本地准备和独立审查阶段，不是运行结果。代码检查通过也不授予运行权限。完成确切审查后将运行卡和不可变源版本交HQ决定。

## 2026-10-19 准备完成，独立代码审查通过

代码冻结于 `5319bf47e6c5b7ca6fe3a95884b610e0d7251848`；17项本地合成fixture通过，另完成全合成完整入口/导出/归档路径检查。独立审查初审和两次焦点复审保留，最终 REVIEW_PASS；收尾双重故障被修复，原异常、首停和watchdog清理均有针对性检查。数学、目标、预算和旧E033源码/判据不改。

[确切运行包与HQ决定项](hq_handoff_20261019.md)、[准备回执](preparation_receipt.json)、[独立审查回执](independent_review.md)。当前是Code Ready本地准备，不是Run Ready；本轮0真实数据拟合/模型加载/NN梯度/GPU/资源预检/远程传送/执行。下一步由HQ决定是否批准此确切源版本的资源预检和一次运行，不能沿用旧E033授权。
