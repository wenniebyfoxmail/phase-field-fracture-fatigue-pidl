# S01-E013 实现完成，尚未执行真实学习

2026-10-16。设计冻结02af259、独立6.1 sol-Medium设计通过后实现；代码a1fb2278d6fd04ccfe6264ddfa828a156a0652ff及113文件manifest经同模型独立复审通过。完整相关148项测试通过，包括31项新selector测试；仅合成测试，实际R001未执行。

目标是把E012可信正例转成学得选择器的实际净收益。FIT8正GT3/5/6不足以支撑原高容量头，因此只学习一个七选一阈值，包括不修正；输入是修正块相对原块的分类log-odds增量。按真实FIT联合结果选择，并要求100%旧命中保留。原框永久保留为不可变前缀，每图最多1、每源组最多3个追加，限制暴露；仍需实测预算后的旧命中保留。

一次汇总OOF成功需同时满足旧保留>=95%、净GT>=1、macro地点召回变化>0；分项安全弃权、覆盖和新增支持单独保留，不重写主结论。十次正例地点删除只诊断稀疏支持敏感性，不反馈阈值或增加主门槛。3主模型及OOF预测先冻结，再做诊断和真实held/full12评价。

拟议S01-E013-R001：gpu-server/D-26-09/ad\xw436，CPU1、禁GPU，单次3600秒、主进程及后代聚合RSS4GiB；13次阈值学习、91固定政策比较、13FIT基线、1汇总及3held比较；0原图、模型前向、新U、线性求解或full12refit。输入仅固定R004包及12既有训练地点metadata，不访问新确认地点。完整Windows时延未实测。

后续执行对象是这一精确代码及冻结预算的一次R001。当前用户授权止于设计审查后的实现/测试，没有启动该Run。实际收益要由这一次运行验证，不能拿合成净增或E012 GT知情+7替代。若全部FIT弃权则停止本单特征家族，按冻结规则设计一个最小表征修复；若旧检测受损优先解决集合保护，避免无变化重复搜索。

工作区：.codex/worktrees/s01-e013-protected-selector-20261016；分支codex/s01-e013-protected-selector-20261016，基于e5c431db6ff51756bd7d8722553e1eecffafd7d5。实现只新增隔离runner，无现有训练行为变化，safe during running trainings。

本地合成QA归档：/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E013/implementation_QA/。图中14旧命中/+6均为构造测试值，不是实验结果。
