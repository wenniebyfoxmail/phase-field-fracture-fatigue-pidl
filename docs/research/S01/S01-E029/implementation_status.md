# S01-E029 Taobo GPU5 Linux：整包已批准，资源等待，R001未启动

## 2026-10-25 v6 已批准并实际继续执行

用户本轮明确批准 NVIDIA 区域来源修订、精确 v6 源码传送、指定分支更新和同一次尚未开始科学计算的 R001 继续执行。八卡重新检查，GPU5 为唯一无计算进程的合格卡；启动准入 CPU 2.0%、显存24077MiB、利用率0%。GitHub SSH账号wenniebyfoxmail核实；指定分支已正常前推至 `a99e97d5a2be9c39083d0c557d22c9bf16b21562` 并读回一致。远端269源码文件/268绑定与批准对象核验通过。

实际启动 `2026-10-25T22:33:49.128234+00:00`，PID3506720、birth_ticks598971163；新根 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01`。原停止根/包/claim保留，原509私有输入复用。来源仅新增精确pypi.nvidia.cn，科学和Python程序不变，任务资源硬上限仍null，共享余量准入保留。启动记录不代表环境准备或科学验证完成；当前检测读数仍null。实际状态与历史：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/execution_R001/mechanical_resume_01_20261025/`；固定结果取回对应runs子目录mechanical_resume_01。

## 2026-10-25 当前：环境停止已归档；修订版待逐次版本批准

原R001环境链止于NVIDIA固定URL向pypi.nvidia.cn跳转的来源检查（82.6秒），无科学前向/拟合、无run/runtime目录，受管进程已清理。停止包10成员已接收验收，保留率/净GT仍null，不当科学失败。源码及509输入已在Taobo，原公开分支已推送34ec77ef。

已完成本地环境元数据修复，精确来源补充及小文件原SHA核验；Python源码、42依赖/URL/SHA、科学/数据/资源合同不变。新版本 `a99e97d5a2be9c39083d0c557d22c9bf16b21562` 仅本地，未发往Taobo或公开分支，未重启。按最新总纲3.1需批准此次新版本的传送/推送与同一R001环境恢复；[最终审批版本](taobo_bootstrap_repair_approval_20261025.md)。不再重开普通检查/未变审查。原运行/私有目录不覆盖，新子目录仅候选，当前不存在。

[停止与接收记录](bootstrap_stop_20261025.md)。以下保留原先运行中/待批等历史措辞，以本段为当前状态。

## 2026-10-25 实际启动：R001已在GPU5运行

509成员私有包已由原Windows字节导出，经Mac校验、中转与Taobo分段前缀续传后完整重组：595789790bytes、SHA2424ed391fe41ef3d8d61c9c2c32bde0f20f3f2fe50c2219c3ff5a5c687f331a，和原Windows收据完全一致。Taobo原接收器完成509成员/CRC/逐项SHA核验，未额外解码GT/RGB/模型。串行/分段传输的退出与部分文件均保留；已知超时后先核前缀再续传，未重发已验证字节或增加科学Run。

在18:41:33 UTC重新准入：GPU5无compute/0%/24077MiB，CPU2.78%。实际detached wrapper PID `2996467`，出生tick `597577573`；源码 `34ec77ef29674622cf4d87bb46912fe4943aea14`、manifest `dc243bbad5ae7a9fc19d3869d990308da57c805fb6968125eeb6295be0aed1ce`，指定公开分支已推送并核对。任务根`/mnt/data2/drtao/wennie/S01-E029-R001`；日志`wrapper-logs`，唯一固定包`S01-E029-R001-fixed-v1.tar.gz`。已创建launch_claim，不能重复启动。

当前阶段为专属运行库构建/同一运行链；科研推理/拟合和最终效用尚待实际进度，保留率/净GT为null。已接好固定成功/停止包的一次自动取回与CRC/清单验收，接收后才做结果解释及原图检查。新确认地点继续封存；科学方案、次数与原容量/弃权不变，任务资源硬上限按用户取消、共享RAM/磁盘余量保留。

实时记录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/execution_R001/taobo_all_gpu_20261025/execution_receipt.json`；完整启动命令/PID见`actual_operator_launch.json`；接收目录`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/`。

## 2026-10-25 当前执行入口：任一合格Taobo卡，任务资源上限取消，迁移进行中

用户明确授权重新检查各卡，找到合格卡后自动更新字段并推进原一次R001，保持科学方案且没有资源上限。八卡实查仅GPU5无compute/0%/24077MiB可用，故仍选原GPU5 UUID；CPU2.77%、MemAvailable376528200kB、大盘剩余586518487040bytes。允许别卡仍有任务，不抢占或杀进程。

任务RSS/CUDA/输出/结果包硬上限改为null；墙时仍null。共享主机RAM至少8GiB、磁盘至少32GiB余量及固定输入/下载完整性尺寸防护保留，防止影响其他任务。单线程仅维持原数值复现，不改变模型、科学次数/四臂、容量/弃权/正交集或封存。更宽的资源修改被自动审批拒绝；上述收窄方案获准，原77项固定人工/mock基准通过；未追加科学测试或重开未变审查。

当前源码 `34ec77ef29674622cf4d87bb46912fe4943aea14`，manifest `dc243bbad5ae7a9fc19d3869d990308da57c805fb6968125eeb6295be0aed1ce`，源码包SHA `de5868cfbebcbf609a672dbed77091a811f49909e088e291dc2254666cba369b`。公开指定分支已实际推送且读回一致，GitHub SSH账号wenniebyfoxmail。269源码成员/268绑定在Taobo已接收验证；Windows源ad\xw436已完成509成员私有字节包（595789790bytes，SHA2424ed391fe41ef3d8d61c9c2c32bde0f20f3f2fe50c2219c3ff5a5c687f331a），Mac中转核验通过，正在传至Taobo。初始Windows detached导出进程消失、无部分/结果文件；确认零启动后改为保持连接等待并成功，仅字节导出，不是科学重试。

原一次S01-E029-R001尚未启动；批准对象已按实际commit/hash实例化，不重复请批。后续仅同一链的私有接收、再准入、runtime构建、十phase、固定结果取回验收。保留已签名v4与旧资源等待历史，不倒签。当前保留率/净GT仍null。实时记录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/execution_R001/taobo_all_gpu_20261025/execution_receipt.json`。

## 2026-10-24：整包已批准，GPU5资源准入等待，R001未启动

用户已明确“批准，请执行”，本次整包不再待批准。精确Linux v4源码包/268绑定本地核对未变。一次成功只读SSH核实GPUServer8/drtao、三挂载和八卡：GPU5 UUID匹配，但compute PID3290978、利用率100%、空闲3292MiB，不满足无compute/0%/至少8192MiB；其余七卡也均有compute。E029任务根不存在。

因此没有源码/私有输入传送、公开推送、runtime安装、远端授权或launch_claim，也没有producer、前向、fit或GT/RGB/maps/OOF读取。保留率及净收益为null。这是已知零启动资源等待，不是科学失败；未消耗科学R001，不另造RunID、不触碰现有任务、不默许换卡或重复启动。3600秒限制仍取消；授权范围和原首停/重查边界保持。当前待解决的是指定GPU资源，不是再次批准同一整包。

实际记录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/execution_R001/taobo_execution_20261024/admission_receipt.json`。

## 当前入口治理修订（2026-10-20，前瞻生效）

执行唯一入口仍为 [taobo_execution_approval.md](taobo_execution_approval.md)，其中新增“一次整包授权，机械检查自动完成”。目前整包迁移/发布/一次R001仍待人方批准；批准后，范围内实现/修复/测试、既选通道必要聚焦复审、版本/环境/资源检查、命令/RunID/路径/哈希/收据补齐及同包接收归档均自动完成，不另开逐项批准。纯元数据不重启Code Ready。越出科学/保护数据/producer/预算/科学重试范围才合并升级人方决定。

本次仅本地管理条款迁移：科学方案、原数据与封存、GPU5、一次R001、资源/次数上限及用户取消3600秒的决定均保留；已签名源码包、review PASS及历史失败/首停/authority不改。没有签发approval、改enabled、SSH/安装/探针/迁移/推送/真实计算或新审查，未恢复自动化。已知零启动资源等待不冒充科学失败，也不新增未经许可的重查或科学重试。

2026-10-20。用户要求的Linux最小适配和必要平台修复已完成；独立 gpt-6.1-sol / High 精确代码复审 REVIEW_PASS。最终source-only `2dd8487f604112e061032e7a006367f344e74454`，owner实现 `3d6113fb498e9ee00a5e45818e0254f3aed05046`，Linux manifest `3cbde12cc84b8b8b677b04b5b182a1c7255f0cd41b1c30ada3fa7deff9645a4e`；268绑定、269源码包成员与Git逐字节一致，77项手工/mock/字节测试通过，fresh解包复跑一致。审查意见及原v1/v3档案保留。

取消3600秒限制，wall_seconds=null，没有替代总时限；原科学范围/次数、CPU1、RSS/CUDA各4GiB、容量1/image与3/组、弃权及固定正面积交集不变。目标仍是同信息四臂比较中有益修正进入前三，九主地点形成实际OOF保旧净收益，并在全部十二旧地点保旧。新确认/封存地点不访问；没有新地点泛化声明。

已准备[完整迁移与一次R001执行审批版](taobo_execution_approval.md)，包含精确源码/私有508文件及catalogue、Windows只读导出→Mac→Taobo GPU5、专属Linux运行库、指定公开分支、唯一R001与固定结果取回验收。当前没有源码或私有输入传送、公开推送、runtime安装、SSH占卡、真实前向/fit/GT/RGB/maps/OOF；GPU5准入仅旧快照，批准后重新检查。代码通过不是净收益结果，科学读数仍null。

[独立复审记录](taobo_code_review_20261020.md)。旧Windows准入及科学负结果保留，下面均为历史记录。

---

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
