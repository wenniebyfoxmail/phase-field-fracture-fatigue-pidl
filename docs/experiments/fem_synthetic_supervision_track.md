# FEM synthetic supervision track

机制问题：在固定已知前态的合成FEM状态上，保留数据锚点的机械微调能否改善PIDL局部active场，而保持u/d与损伤可行性？历史已存在MIT-8/Path C/四字段/mesh预训练，本路线不主张首次FEM增强。

唯一当前实验为[S04-E027](../research/S04/S04-E027/experiment.md)，冻结单状态c20s4/horizon0/seed1与C/S主比值。[实际结果](../research/S04/S04-E027/result_20261018.md)：3500更新/.675GPU小时完成，输出与独立图审查完成；C/S=.952342，但C几乎抹去损伤，不能称有效完整修复。初态active误差也优于S/C。历史负结果和原主判据保留。

当前状态：执行完成，科学处置待HQ。证据/身份/成本见E027 runs摘要与本地Case指针；不外推泛化、物理演化或道路有效性。下一判别由HQ先审梯度尺度及损伤可行性设计；没有新卡/人方批准，不新增训练或调参。
