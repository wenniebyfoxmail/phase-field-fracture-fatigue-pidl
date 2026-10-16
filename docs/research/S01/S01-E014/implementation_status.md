# S01-E014：几何排序最小修复已冻结并实现，尚未执行真实R001

2026-10-16。设计bb763b9先经6.1 sol-Medium独立设计审查通过，再实施6cf26e04d684787fda48a33c2555290b6cb9bd01；独立代码复审及合成实际图表验收通过。24项新测试、全部172项相关测试通过。

## 唯一决策改动

容量内按d=1-IoU(original_box,corrected_box)降序，再按原s0与稳定image/box/key排序。d只表示几何变化，不等于定位质量；d=1的完全不相交候选继续按s0并列回退。不学习几何权重、不搜其他量或方向。

E003原框/概率/分数/顺序、GT无关eligible、x七档（含不修正）、每图1/每源组3、accepted-only冲突处理、实际FIT联合目标及100%FIT旧命中保护均不变。实现使用E013私有模块实例，不改E003–E013任何冻结源码。

## 两层结果必须分开

容量进展：每个FIT8正GT仍为3/5/6，用各自已保存singleton身份和已经评估的source_keys，分别报告任一固定政策与最终所选政策是否选入已有正GT；按GT去重，不把其他FIT标签拿来评价当前held，不反馈模型选择。

实际解决问题：一次汇总12地点OOF仍需同时旧检测保留>=95%、净GT>=1、macro地点召回提升。原框保留不能代替预算后保留，正例入cap不能代替联合新命中。各fold允许弃权，不能要求所有fold活跃或复现oracle+7。

## 冻结预算与停止规则

拟议S01-E014-R001一次、gpu-server/D-26-09/ad\xw436、CPU1/禁GPU、3600秒/聚合RSS4GiB；13有限阈值学习（3主+10地点删除）、91政策比较、13FIT基线、1汇总及3held比较。3主预测先冻结，10诊断不反馈阈值；全FIT弃权仍完成这一次冻结评价，再停止本几何量家族。0原图/模型前向/新U/线性求解/full12refit，不扩网格/cap或自动重跑。新确认地点持续封存。

## 已验证及未验证

测试覆盖唯一政策差异、GT无关d和不变分数、稳定同分、容量/NMS状态、GT去重/本FIT隔离、审计不反馈、主预测冻结、语义篡改检测、源包导入以及完整合成流水线/三图。独立真实audit hook合成流水线也通过。合成规模43347/31156/835仅评估七次固定policy+metric，未拟合阈值，完整Windows时延未实测。

真实E014缓存未学习或检测评价；未SSH/传送/推送/启动R001，合成净增不代表实际净收益。下一步是在单独获准的一次Run中检验“正例进cap→联合净增”链条，不能用设计/代码审查通过代替它。

原始合成QA：/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E014/implementation_QA/。所有图表是构造数据，非实际R001。

分支codex/s01-e014-geometry-ranking-20261016，base cf042e2ac998dcbd2bbffbaa0897d9c8e9cc2672；122项源码manifest。safe during running trainings：仅独立新适配器及记录，不改变现有producer行为。
