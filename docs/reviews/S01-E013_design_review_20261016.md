# S01-E013 独立设计审查

审查者 e008_independent_review，gpt-6.1-sol Medium。DESIGN PASS，绑定冻结提交02af259ab8812603f96ff0e1637aa41be0172f98。配置SHA256 41bb2f441124769f8b67aac56cc76908b7e01f36e7c547af97ca56df19566621；数据锁SHA256 f7db8940ef3bab89063822784ccfb7c38183c169df60994e8e5a9786ae7f5dc4。

通过后才实施。FIT8仅3/5/6正GT，单log-odds增量特征、七选一阈值（含abstain）、每图1/每源组3有限追加，不扩网格/特征或高容量头。FIT实际联合指标选择：全保旧命中、净GT>=1、macrodelta>0；否则不修正。主预测先冻结，再10次整地点删除诊断及held/full12评价。汇总主标准保持旧保留>=.95、净GT>=1、macrodelta>0，不要求复现oracle+7或三fold全活跃。

实现注意：只有accepted修正占据NMS/cap；新增FP必须依据canonical预算前缀身份，不能将原框不变等同预算保留；毒化held GT/full12 U/诊断应不能改变对应主预测。已消费地点和上游模型复用只支持条件选择器OOF，不是整管线独立验证或新地点泛化。

预算1Run/CPU1/3600s/聚合RSS4GiB，13阈值拟合、91校准比较、13FIT基线、1汇总及3held；0模型前向/原图/新U/线性求解/full12refit。设计通过不授权真实拟合或Run。新确认地点继续封存。
