# 各FEM case的elapsed time记录要求

2026-10-20用户要求：如果重新计算不同FEM case，逐case保留elapsed time。本次只记录要求和建立空表，没有新运行；原v2准确包、执行卡和审核结论不改。

每条完整载荷轨迹是一个case；相同物理case的reference/classical/hybrid各占一行，各次实际尝试分别记录，不合并、覆盖或省略失败。每行关联Run/attempt、载荷路径、材料参数、初猜方法、实际机器/核数/GPU和准确代码版本。case定义优先指向实际执行卡，不能只写模糊的low/high。

主记录 **elapsed_seconds** 为producer端逐case实际墙钟耗时，另给elapsed_hours；包括该轨迹worker启动、导入/装配、模型准备、数值推进、状态/标签写入，以及失败后的该阶段清理。使用单调时钟差，不用CPU秒、核心小时或GPU小时替代。排队、SSH传输、公共依赖检查、共享回放/分析另列公共开销，不摊成假精确的逐case求解时间。

既有计时可复用：

- `tools/run_hybrid_producer.py` 在逐phase的finally中保存 `cost_ledger.json → phases[case_id].wall_seconds/cpu_seconds/completed`；这是逐case elapsed的主来源，失败/killed也入账。总ledger的numerical_seconds是trajectory phase耗时累计，**不是纯FEM内核耗时**。
- `tools/hybrid_producer_worker.py` 的trajectory receipt `wall_seconds` 是setup之后的轨迹循环时长，完整成功才有，不等于主elapsed。若展示该量，名称用worker_trajectory_seconds；缺失留空。
- `events.jsonl` 的 `total_step_wall_seconds` 保存已接受子步耗时；`work_trace.jsonl` 分解机械平衡、damage QP、推理、提交/IO等工作。失败子步和未闭合trace明确标缺失，不把已完成子步求和冒充完整case elapsed，不将嵌套块相加造成重复计时。

输出：实际运行证据目录保留原ledger/receipts/events/work_trace，事后从真实记录导出 `case_elapsed_times.csv`；本目录的 `case_elapsed_times_template.csv` 只有表头，无实测值。结果中并排报告完成状态、接受/计划子步数和停止原因；未运行case不填0秒，缺失耗时不按预算或别的case推算。

后续新增loading/property runner必须同样逐case计时。当前这些runner尚未实现；记录要求不代表已执行或已完成新增case支持。正式启动前将该输出要求带入准确执行说明，保持现有求解/精度/预算条件。
