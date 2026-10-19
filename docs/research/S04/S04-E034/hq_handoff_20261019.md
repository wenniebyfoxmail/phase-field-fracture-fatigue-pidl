# E034 总部评估：双臂代码与确切运行包已备，尚未执行

目的：在原十一项保护、冻结原锥/2%头半径、top/bottom反力误差分别不增的条件下，达到相对实际E032的原raw-global RMSE至少下降0.1%。固定F8后F802，各自独立从E032出发；复用Z0和历史H0，不重跑旧E033。

本轮完成：新opt-in代码、17项本地合成检查、全合成完整导出/归档路径、独立代码审查。最终 **REVIEW_PASS / Code Ready本地准备**。未资源预检、SSH、GPU预留、真实PT/模型加载、真实梯度/拟合或运行；新增GPU用量0。旧E033原代码、判据、首停与结果保留。

- **确切运行源码**：`5319bf47e6c5b7ca6fe3a95884b610e0d7251848`，协议`S04-E034/v1-finite-raw-reaction-F8-F802-20261019`。后续记录提交只补文档；未来producer必须checkout这一源码commit。
- **不可变源码审阅镜像**：[S04-E034_5319bf47_source.tar.gz](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E034/preparation_20261019/S04-E034_5319bf47_source.tar.gz)，16,249,685 bytes；SHA-256 `70f9bd763a2c34cd4de5964cab0d0b043d56a6b6f8304eb64248801306d71ac0`。它是审阅快照，运行仍须GitHub来源的独立exact clean clone，不能拿无Git的tar解压目录绕过准入。
- **来源/文件SHA与本地依赖**：[source_manifest](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E034/preparation_20261019/source_manifest_5319bf47.json)；[data lock](data_lock.json)保持四MAT、S1500、E032五文件与E033五文件身份。
- **检查及审查**：[准备回执](preparation_receipt.json)、[独立审查链](independent_review.md)、[17项合成检查日志](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E034/preparation_20261019/final_fixture_checks.log)。收尾双重故障已修复；通过不代表原目标可达或实际运行成功。
- **运行卡与完整契约**：[run_card](run_card.md)、[experiment](experiment.md)、[原批准完整方案](../S04-E033/finite_reaction_comparison_plan_20261019.md)。

每臂60主迭代、120不同实际点、600秒；第120点可完成判定，121点禁止进入物理评价。共享准入/零点函数Jac/输出归档<=480秒，额度不转移；GNU timeout1790秒TERM+5秒KILL，独立phase watchdog。首个实际达标点经actual NN复核后固定；正常未达返回精确E032，任何异常停止整个包、不重试/换卡/换权重。

新增整包<=0.5GPUh、原累计<=2；旧保守累计1.108339654581623，最坏1.608339654581623<2。RAM32GiB、输出2GiB。唯一GPU5 exact UUID；未来启动前重新实时核验20GiB空闲/SM0/无计算app和host RAM/规范磁盘，持续1GiB余量。当前资源和实际802维耗时都未测，不预报600秒内必能完成。

总部下一决定：是否接受此确切包，并另行明确授权未来一次准入及运行。`grant.template.json`保持execution_authorized=false，未填写approved_commit、人方执行引用、review引用和fresh运行ID；准备授权不替代这些条件。源码本轮未push或远程传送，后续跨机同步与运行需按既有规则处理。无需追加设计、真数据检查或资源探测即可审阅当前包。

结果解释仍按原矩阵：F8成功优先简单8轴；仅F802成功须看B8内外分解/至多一次投影身份复放，不称8维全局无解；两臂有效未达停止当前配方追加并交HQ讨论机制路线；工程停止为不完整比较。当前没有新增科学结果。
