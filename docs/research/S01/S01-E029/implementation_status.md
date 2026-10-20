# S01-E029：Windows代码已审已批；Taobo空闲候选需Linux适配

2026-10-20最新：恢复授权后查遍gpu-server两卡及Taobo八卡；Windows两卡有compute且CPU79%，Taobo GPU5无compute/0%/24GB空闲，但Linux runtime不符合已审Windows锁。已完成独立最小迁移范围核查，见[Taobo迁移边界](taobo_migration_scope.md)；不是Linux Code Ready，没有实际生产或预算消耗。

原Windows交付：完整runner、逐fold GT隔离、六模型/预测冻结屏障、B1可信重放、全空间身份join、限量流式前向、9/12同scope评价、三图、受管首停与成功/停止打包接收均已实现。独立gpt-6.1-sol / High精确代码复审REVIEW_PASS，绑定owner `e6ef93c3dd6c3a833fe8d095c6e4143c8f8964d7`、source-only `5307a6f52a0877ad56f13df6efeb86e1481df6d6` 与manifest `7e4a45c848f6122d4e05a9c2104d485f35fdae9da9a04515208f302aaec3727c`。49项人工/mock测试通过；252绑定/253源码文件逐字节核验。v1/v2修改意见及原包保留，最终v3修复未变科学标准。

当前execution_enabled=false；未生成授权文件，没有真实fit/模型前向/GT或地图解码/源RGB/政策OOF/SSH/传送/推送。测试不等于实际净收益。Windows原生行为/私有输入与实时GPU准入留在未来同一首停链，不单独偷跑。

用户已批准[精确执行审批版](execution_approval.md)，但14:09Z准入发现GPU0利用率100%及四个既有Python训练进程，按冻结共享计算条件首停；尚未传送/推送/创建授权文件/启动，预算用时0秒。详见[当前执行状态](execution_status.md)。下文原先待批说明保留为历史：自有gpu-server/GPU0一次R001、新3600秒总预算，传送此源码包、推送指定source-only分支及本次固定结果取回验收。无普通代码准备的额外审批，也不继承E028余额。E003、原容量/弃权/正交集、新地点封存保持；九主地点是既有开发地点。

正式报告：/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/production_v3/independent_review.md。源包530050bytes / 253files / SHA256 `790dbba6ea1804fe3d3f4b04f4ebf6d21770b714796c7d54ac9dbd23fc069d3b`。

---

## 以下为此前离线设计阶段的原记录（当前状态以上文为准）

# S01-E029：离线设计与最小接缝准备

2026-10-20。候选设计2da7e4df；gpt-6.1-sol / High独立差异复审REVIEW_PASS，范围仅离线设计与数值adapter。D8目标是让E028已有空间能力转成原前三预算内的保旧实际收益，不重复证明定位器有响应。

已完成：定位E019–E022的group_cap排序瓶颈；冻结一组E003/既有E018几何/对齐S/固定错位M比较、九地点主效用和十二地点保旧保护；绑定E028原生输入/权重/预处理/存在汇聚；写GT-free两个空间列的纯数值接缝及固定地理角色；14项手工数组测试-Werror通过。本地v2 review包25成员55914字节，SHA cb1f3aeb036e472069c039f3f33c18566253c665736aa3fded6cb6250cfae0ca，manifest2490fe12…72ab0e。仅准备/本地提交，未传送或推送。

重要澄清：三套FIT8并集覆盖全12，必须按fold/model角色隔离GT，不声称所有模型冻结前全局从未读取held身份GT。v1审查指出该措辞缺口；v2明确FIT worker仅本FIT监督/校准、held worker仅本冻结模型与GT-free对象、全OOF冻结后独立评分角色；实际loader尚未实现。

现有B1三套模型/OOF文件已只读定位并记录字节摘要；不解码其语义或重放政策。本次只读835张非GT尺寸/地点身份：338图有已冻结空间投影、497图尚缺，未来需19880次新forward；它是新执行预算提案，不是已完成信息，也不继承E028剩余预算。未来18次小矩阵求解、新图推理、OOF评分均未运行。

**本交付是离线设计/adapter审阅包，不是producer Code Ready。** 还缺完整角色隔离loader/runner、B1模型/gate/预测可信链核验、835投影身份join/计数/流式输出、六模型/gate/OOF冻结屏障、9/12 operating-point评价与图表、Windows准入/资源/首停以及完整精确源码包审查。不能拿这个包请求直接R001执行。

具体下一决定：是否按已审候选继续完成上述完整实现及精确代码审查；随后才可能准备新一次R001的具体审批版。当前真实fit/train/infer/OOF=0、新GT/源图/封存访问=0、SSH/部署/传送/推送=0。E028通过的限定结论、地点24负结果和全部旧失败保持；E003、容量、弃权、正交集与封存不变。

正式审查报告：/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/preparation_v2/independent_review.md。v1 MODIFY原报告保留在preparation_v1；v2只澄清GT访问合同，未变数值adapter或方法/标准。
