# S01-E029 Taobo GPU5 Linux：整包已批准，资源等待，R001未启动

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

# 当前：已复查全部可用GPU，Taobo GPU5空闲但需Linux适配

# S01-E029：GPU选择复查与Taobo迁移边界（未执行）

2026-10-20。承接用户恢复授权：重新检查GPU0及其他卡，不只等待GPU0；一次R001总3600秒，含结果取回验收；E003、容量/弃权、固定交集和封存不变。此记录不是Linux Code Ready，也不是实际模型/OOF结果。原v3源码和原准入记录均保持。

## 已核实的选择

14:15:19Z，D-26-09 GPU0利用率83%，GPU1为32%，分别有真实compute PID16340/39912；四个既有Python训练进程、CPU79%，原CPU<50/无共享Python/选中GPU零利用率规则不满足。检查覆盖该机全部两卡，没有只等GPU0。

Taobo GPUServer8全部八卡均已查。GPU5 UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，0%/4MiB已用/24077MiB空闲，无compute PID，是唯一无resident compute的候选。GPU0/1/2/3/4/7虽有0%快照，但均有resident compute；GPU6为55%。不能把0%单次快照当作其它任务已释放。大盘/mnt/data2可用638906994688bytes，/mnt/data3可用1008188522496bytes。只读核查，没有预占GPU。

Taobo现有/usr/bin/python3为3.10.12、Torch2.7.0、vision0.22.0、numpy1.24.4、psutil7.0.0、matplotlib3.10.3、Pillow11.1.0；已审v3锁定Windows、Python3.12.14、Torch2.11.0+cu128、vision0.26.0+cu128、numpy2.5.2、psutil7.2.2、matplotlib3.11.2、Pillow12.3.0。当前未满足原runtime，不能简单改CUDA_VISIBLE_DEVICES=5或借用旧环境执行。

## 最小迁移范围（独立静态核查结论，不是实现通过）

1. 在/mnt/data2/drtao/wennie/任务专属目录提供隔离Linux运行库，锁解释器/依赖的Linux构建版本、文件hash/origin及兼容驱动。不得用Windows wheel，不改共享环境，不默许Torch2.7替代2.11；不放宽旧B1数值重放1e-12。
2. 原11私有输入逐字节/SHA不变；ZIP、scope里Windows路径保留为原逻辑身份，验证用PureWindowsPath。另冻结497图image_id→Linux物理路径/SHA，仅open与caps使用resolver；不重写旧输入、source_image_root或R002 scope来救join。
3. 迁移对象仅精确源码、11个原输入、497张缺投影原图和独立runtime/字体清单；338张图只复用12238投影，不额外迁移/重解码。私有输入不进入公开分支，跨主机传送在最终精确版本/对象清单批准之后；当前没有传送。
4. Linux worker的psutil需只观察自身；controller在精确权限外聚合本任务PID/birth。只给必要自身/proc元数据及固定字体/runtime读能力，不放开整个/proc、/mnt或数据根。字体发现不得在cap后偷偷spawn。
5. 用本任务专属session/process group与PID/birth/UID/cwd/cmdline代替taskkill，只清理本任务；保留写盘失败仍清理、有限等待、绝对墙时内清理预留、停止包/CRC/双清单和不重试。
6. 将gpu-server绑定迁至GPUServer8/GPU5精确UUID（运行前重新核验）；他卡任务不等于选中卡任务。Windows全机无Python规则不能自动放宽成Linux共用规则，需作为显式平台准入差异审查，保留CPU/RAM和选中GPU独占/内存/功耗约束。
7. 科学接缝全部原样：四臂/同11系数/固定错位/阈值/18solve/497图19880forward、FIT逐折隔离、六模型及全部held冻结后评分、B1可信重放、前三容量/弃权、主九D与9/12零失旧保护。新确认地点与原封存仍不访问。不得插入真实微测、减少样本或追加forward来救预算。

没有发现静态必然超过4GiB或3600秒的矛盾；RTX4090实际吞吐/峰值尚未证明，不能写成已可行。全部实际预检和执行仍须在同一次首停链，保留实际停止而非扩预算。Linux启动代码、隔离runtime来源锁、精确迁移清单和权限/进程测试尚未完成，因此当前不能提交Linux执行批准或声称Linux Code Ready。

下一可执行的开发工作是按上述范围完成Linux适配、测试及精确代码复审，再形成一次具体迁移/运行决定；不再以等GPU0作为唯一出路。原Windows版本仍Code Ready，但本次没有满足其冻结准入的机器。源码/私有传送、公开推送、授权文件/producer启动全0，预算用时0秒，前三/保留率/净GT为null。

证据：local_archive/experiments/S01-E029/execution_R001/resume_admission_01/里的全部GPU快照、runtime metadata及admission_receipt.json。独立静态可迁移性核查使用原6.1 sol / High审查者；其结论仅必要实现清单，不作Code Ready PASS。

---

## 原首次准入记录（保留）

# S01-E029-R001 admission stop — no launch

User approved exact v3 source transfer/designated public push/GPU0 once R001 total3600s incl retrieval. At2026-10-20T14:09:12Z the approved machine/account were verified, all planned fresh paths absent, and GitHub SSH authenticated as wenniebyfoxmail. GPU0 UUID matched but utilization100%,17478MiB used; four existing unrelated Python training processes4280/16340/25300/39912 were present. GPU1 also busy56% and is not a fallback.

The frozen wrapper forbids shared Python conflict. This read-only admission snapshot stopped the chain before any source transfer/public push/approval-file write/launch. No other process was terminated, no occupancy reserved, no fallback or retry. Producer budget used0s; model forward/fit/RGB/GT/OOF all0. No retention/netGT result: null, not0; E028 qualification and site24 negative remain unchanged. No producer result/stop package exists because no wrapper or Run was started. This folder archives the local admission evidence only.

Resume condition: the original GPU0 and machine meet the original no-conflict/CPU/RAM/GPU/runtime criteria, with explicit authority to resume after this first stop. Do not reconnect merely to poll for idle, auto-retry, switch GPU/host, relax conditions, extend budget, or generate another RunID. Reuse exact reviewed5307a6f5 source and frozen scientific design unless separately amended.

Evidence: execution_R001/predeploy.ps1, predeploy_stdout.log/stderr.log, admission_stop_receipt.json. Source package remains production_v3/S01-E029-R001-source-v3.tar.gz, exact SHA790dbba6ea1804fe3d3f4b04f4ebf6d21770b714796c7d54ac9dbd23fc069d3b.
