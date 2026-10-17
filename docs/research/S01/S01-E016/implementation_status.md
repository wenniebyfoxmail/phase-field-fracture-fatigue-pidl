# S01-E016：设计与代码独立审查通过，有限排序实现测试完成

2026-10-17。设计b29288b1ae6f4b7d09c68eef8de5e49a4be35cee经用户指定6.1 sol-Medium独立审查通过后，完成实现4eab421c0262e8784262be8f752440343db47818，6.1 sol-Medium独立代码复审及三张合成PNG/README验收通过；真实PaveTrack收益未测试。

## 冻结方案

唯一可学习对象是六选一政策：q=(1−alpha)*tanh(x/2)+alpha*IoU(original,corrected)，alpha固定0/.25/.5/.75/1，另含abstain。固定x>=0取代E015的七选一阈值学习，不做alpha×阈值网格，不拟合13参数回归头，也不声称预测了逐候选U。每个FIT只以自己的真实联合净GT优化，要求100%保旧、净>=1及macro提升才active，否则弃权。

原框/检测分数、base eligibility、严格原坐标正交集、冲突、每图1/四地点源组3及accepted-only状态保持；q只决定容量占用。最终仍看一次pooled12 OOF保旧>=95%、净GT>=1、macro delta>0。FIT3/5/6正例及10整地点删除仅约束模型容量/描述稳定性；不称样本充分、不以支持归零强制弃权、不让诊断反馈主模型。新确认地点封存。

## 验证

32项新合成测试、19个绑定测试文件全部293项通过；12条既有scalar人工矩阵警告，不涉及E016学习。覆盖正例与极端变化候选争夺cap、排序实际联合优化、原分数/资格不改、稳定并列、冲突拒绝不占cap、极小正交集下IoU为0仍准入、非冻结alpha拒绝、FIT/held GT隔离、3主模型预测先冻结、10删除诊断/审计不反馈、RSS/时限/计数停止及收据语义篡改拒绝。

合成正案例中三模型均学alpha=.5，14/14旧命中保留、净+6；另有同类有益入cap却造成预算失旧的案例，正确弃权。两者验证实现的决策机制，不能当真实7正GT已入选或检测收益。完整合成execute使用真实pixel audit hook，实际三张PNG及README已由根代理打开核对；QA路径：/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E016/implementation_QA/。合成Guard内存回调为100，不是生产RSS；完整Windows时延/内存仍需真实授权Run验证。

140文件source_manifest SHA256 a2add33820d3fef249287dd757b9d85d32fe33c6462a9e17aa0602d66bd448dd；源包需141文件含manifest。E003–E015冻结依赖源码不变。config a45bd694c66a51c33d0ca621469665de4653938e64972557c98a9b5e0372dc5d，lock 2c7d22740f7026445d89e6d144226b6aad56300a4000ae16ea642d94178e35cf。

## 预算和下一步

未来一次R001：gpu-server/D-26-09/ad\xw436，CPU1/禁GPU，3600秒/聚合RSS4GiB；13有限排序学习、78联合政策比较、13FIT基线、1pooled+3held。0像素/模型前向/新U/梯度/线性求解/full12refit；无自动补跑、alpha细化、交集阈值扫描或换机器。若无FIT保护下主动净增则停止此混合排序家族，同一Run完成预定评价后如实记录，保留组件成果。

本轮没有真实缓存拟合或政策评价，没有SSH、源码传送、公开分支推送或R001。用户授权的冻结→独立设计审查→实现测试已完成，独立代码审查已闭合，可准备后续精确执行版本。safe during running trainings。

分支codex/s01-e016-utility-ranking-20261017，base950f9f65a4e7499e6d30d4e5511d8b88dc1ed36c。源码与内部审查分开；此本地文档HEAD不是公开源码分支的发布身份。
