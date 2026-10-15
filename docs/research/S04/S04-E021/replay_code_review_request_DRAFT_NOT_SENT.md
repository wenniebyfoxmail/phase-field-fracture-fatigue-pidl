# Frozen-model replay code review — exact proposed send, NOT SENT

Sender:current S04 residual main chat01a1131d-017c-7b03-a95a-ad73ba8fcc9c,
not an email account. Recipient:`多目标优化学习 FEM–PINN Delta`,
01a12d15-9b60-7280-8248-18386d6ef741. Attachments:none, local references only.
Exact review snapshot:45d36055ea10ef1177de342dd01dbfe3c4376ee8.
Human approval needed for this specific send; no actual replay authority.

## Full message body

请只读审核45d3605的冻结模型推理重放实现，依据bcb58a6中的next_validation_plan_v1.md。工作树：
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-raw-replay-preparation-20261015

新增代码是SENS_tensile/s04_raw_replay.py、s04_raw_replay_guard.py和s04_raw_replay_checks.py。它固定已保存的模型、尺度、归一化和alpha，不调用拟合或重新选参；独立重建预测与误差，并核对已有记录。真实入口要求新的重放授权文件，预算仍300秒／2GiB／100MiB，不重试。

仅执行生成数据和mock核验：164个toy cycle的MSE最大差6.94e-18，固定快照差2.22e-16；异常、容差外差异、缺失/不匹配授权、相对路径交接及三类触限均有测试。未读取真实轨迹或冻结结果内容、未拟合或真实重放，也未做完整资源测试。实际解压/I/O、条件数与峰值内存仍待验证。记录及证据位置见docs/research/S04/S04-E021/replay_runner_engineering_20261015.md。

请重点核对冻结输入身份、模型参数不变、独立预测/非负映射、面积加权和分层聚合、容差与失配终止、授权入口及资源清理，并指出测试覆盖不足。请只读代码和既有核验记录，不执行测试、拟合、重放或重绘，不修改共享笔记；额外核验请先提出。

请返回绑定45d3605的代码审核结论、必须修改项及理由。本主对话仍是唯一实现和记录方；代码通过也不授权真实重放，后续须单独运行卡和用户批准。E021开发结果及U0.11晚期退化的结论不变；确认数据关闭，S04-E017和多目标训练继续暂缓。
