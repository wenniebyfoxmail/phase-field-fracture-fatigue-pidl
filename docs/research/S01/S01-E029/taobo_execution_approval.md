# S01-E029 Taobo GPU5：迁移及一次R001完整审批版（2026-10-24用户已批准，执行状态见下）

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

以下为已批准整包及原前瞻管理条款，保留原版本措辞；其中“待批准”只描述签发前历史，不代表再次请批。

目的：让已合格的空间信息帮助有益修正进入原前三，在保住E003的前提下产生实际条件OOF净收益。此版只适配Linux平台；原四臂、FIT/held角色、固定交集、容量/弃权、9/12保旧和主D都不改。新确认/validation/reserve与353/1459/2028/5982继续封存。九主地点仍为旧开发数据，不当独立新地点。

用户已明确取消3600秒预算限制。本次配置和授权对象的wall_seconds均为null，没有另加替代总时限；按精确497图/19880forward、18solve等原工作量结束并记录各阶段elapsed。CPU1、单GPU、RSS/CUDA allocated/reserved各4GiB、研究输出/结果包各2GiB仍限制；Linux任务起始/监督空闲磁盘>=32GiB。不得用取消墙时增加数据、fit、随机种子或阈值扫描。

## 2026-10-20 前瞻管理修订：一次整包授权，机械检查自动完成

当前规则采用安装版 [research-decision-core：一次授权，机械检查自动完成](/Users/wenxiaofang/.codex/skills/research-decision-core/SKILL.md)、[agent_bootstrap 的2026-10-20更新](/Users/wenxiaofang/.codex/skills/research-decision-core/references/agent_bootstrap.md)及[research-review-channels](/Users/wenxiaofang/.codex/skills/research-review-channels/SKILL.md)。本节是原active卡的前瞻管理说明，不改已签名源码、历史准入/失败、已消费authority或科学合同；尚未批准的迁移/执行仍未批准。

**本次只需一次整包授权。** 它覆盖本文限定的目标、数据清单、Windows字节导出与Mac中转、Taobo GPU5专属环境、指定公开分支、一次R001及固定结果接收验收。整包获批后，Agent自动完成授权范围内的实现和同范围修复、相关测试、既选6.1 sol-High通道的必要聚焦复审、部署准备、版本/环境/资源核验，以及命令、RunID、路径、哈希、收据和卡字段补齐；不再分别请人批准“检查环境”“确认版本”“补齐卡片”“必要修复后的再审”或“取回同一固定结果”。满足本包已列前提后继续执行，不因机械字段从待定变为实测再开一道批准。

元数据补齐/纯一致性修订自动核对，不重启Code Ready；未变结论复用。涉及科学行为、数值语义、数据解释或执行安全的实质改变，才对相应风险做聚焦复核；科学范围、保护数据、producer/卡授权、预算或科学重试越出本包时，合并为一次人方决定。此治理修订不自行放宽当前冻结版本或安装共享/系统依赖，不把模型前向/新数据读取称为环境检查。

**仍需人方决定的当前唯一边界：是否批准本文限定的一次完整迁移/发布/R001/结果验收。** 私有输入外传、公开推送、runtime安装和真实计算在这次整包批准前均不执行；封存地点不因本包或本治理修订开放。获批后若确需越界，再统一说明实际变化，不把每个机械步骤变成人方决定。

用户明确的边界继续有效：3600秒墙时已取消（null），科学次数与资源上限未取消；仅GPU5/该producer、一次R001，既有首停/未知状态先核验、不隐含科学重试及不自动换卡/主机不变。本卡不追溯增加SSH/重查/重启次数；已知未启动的资源等待记录为准入等待，不记科学失败，仍按现有可用authority决定是否能再次检查。未来确需新卡时，须预先给出总预算内短的机械重查次数/时限，不能在失败后补造RunID或刷新authority。本轮仅本地条款迁移，不触发任何检查或运行。

## 本次具体账号、对象与文件

Mac `wenxiaofang`向自己的Windows `gpu-server / D-26-09 / ad\xw436`传送精确源码包、私有catalogue及六字段授权对象，位置全新 `C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-export-v1`。Windows仅做原始输入字节校验/导出，不运行模型、解码GT/源图或修改共享环境。固定导出 `C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-private-v1.tar.gz` 与 `.receipt.json`，未知状态先查证、不覆盖重发。

原私有字节包经同一Mac中转至 `gpu-taobo / GPUServer8 / drtao`，最终任务根 `/mnt/data2/drtao/wennie/S01-E029-R001`：source=`/mnt/data2/drtao/wennie/S01-E029-R001/source`，private=`/mnt/data2/drtao/wennie/S01-E029-R001/private`。只在新目录安全解包、逐项核验；所有runtime/tmp/cache/run/日志/档案都在/mnt/data2，不用root/home存大输出。**私有输入和catalogue不进入公开分支。** 实时GPU与source/run/launch_claim状态在审批后重核，过期快照不代表预留；无法准入即止，不自动改卡/主机或重试。

迁移对象为11原输入+497图共508payload文件，另1个catalogue成员，共509成员。[完整私有对象与逐项SHA清单](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v1/private_catalogue.json)；catalogue SHA256 `5dc25418f62a6493ad0412d24d6d253b6f23e8b42471308d701bb0f7783adb66`。源图名/原Windows逻辑位置/内容SHA来自同一固定GT-free E017身份成员，未新读RGB或GT。338张有投影图不迁移/重解码，直接复用12238 native-max投影。metadata与图像若bytes未曾记录，不虚填；原SHA和单文件256MiB/私有包4GiB上限强制。整包实际bytes/SHA在一次固定导出后读回并核验，再接收同一对象，不预造结果哈希。

|输入|Windows只读来源|Taobo只读目标|SHA256|
|---|---|---|---|
|E017_zip|`C:\Users\xw436\pavetrack_runs\S01-E017-R001\delivery\S01-E017-R001-evidence-v1.zip`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/E017_zip.zip`|`189f1cb23688013c3692c8cc3dfb0df1400ac6f01ac6b65316c4cd180314cd6d`|
|metadata|`C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\development\manifest_train_validation.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/metadata.json`|`6fc622943a78063926d96a13e727013ae22d12919a3af3814cfc221bd1a7e5bb`|
|contexts|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\pixel_contexts.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/contexts.json`|`eba16f6623e7eaf209f7e40f8ca0368a41fb7b4a9b93021ebcda57eae7c4a325`|
|R002_scope|`C:\Users\xw436\pavetrack_runs\S01-E028-R002\scope.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/R002_scope.json`|`a414473eb65a51b242b7799a5653368d40425317650face52444a2523500e160`|
|R002_projections|`C:\Users\xw436\pavetrack_runs\S01-E028-R002\projections.npz`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/R002_projections.npz`|`898bac8fb30b7dc8ae18d6beddcd8390456ce5062c2d077c3dbc639334ae0be1`|
|checkpoint|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\DeepCrack_CT260_FT1.pth`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/DeepCrack_CT260_FT1.pth`|`945239375c2b3de45abccc2dbdc374e3259b55d16298b298fb9e0cd13be5ad63`|
|network|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\deepcrack.py`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/deepcrack.py`|`92650883b6f6c993bc29635450035e066c968c4f5a9022a6c1966a0b9f0d3360`|
|E018_OOF|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\OOF_predictions.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/E018_OOF.json`|`0d883cae8e22a3f00054afb258a6ed65d8e4fea12d924af7a1330ba17c3badf2`|
|E018_model_0|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_0.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/E018_model_0.json`|`39f169d49eed1743ede3b2b6d55237063d7eecfc2646edb48481b714a7653dbe`|
|E018_model_1|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_1.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/E018_model_1.json`|`ac5ea38f2688ca2d13a80b99ca89bad8ebab1eb758853ed5634a4f57b7537792`|
|E018_model_2|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_2.json`|`/mnt/data2/drtao/wennie/S01-E029-R001/private/E018_model_2.json`|`91a1cc32e0f6a7b9d4c8d42b83fd843d4b662ef35740d1fbe6823f13cc684ab3`|

## 精确源码与公开发布

[source archive](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v4/S01-E029-R001-Taobo-source-v4.tar.gz)：573464bytes/269普通文件，SHA256 `f22481377bcba84a9acd11de3d5b210a7d18fa5486ef418bfed5540a9db73256`；Linux manifest 268绑定，SHA256 `3cbde12cc84b8b8b677b04b5b182a1c7255f0cd41b1c30ada3fa7deff9645a4e`。源包与source-only commit `2dd8487f604112e061032e7a006367f344e74454`一致；owner内部结果commit不用于传送。独立 gpt-6.1-sol / High 代码复审结论见同目录 taobo_code_review_20261020.md；以其精确签出版本为准。

公开对象 `git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git`，预期GitHub SSH账号wenniebyfoxmail，Git作者`xiaofang wen <wennie_wen@foxmail.com>`，指定分支`codex/s01-e029-qualified-spatial-utility-20261020`。身份/远端ref若非预期即停，不替换账号、不force。完整推送动作：

```sh
git push origin 2dd8487f604112e061032e7a006367f344e74454:refs/heads/codex/s01-e029-qualified-spatial-utility-20261020
```

随后从同一origin读回精确ref。公开差异仅源码、配置/recipe/hash/科学合同，不含私有catalogue、图像、标签、权重、模型/运行结果。此审批文档留owner记录，不作为外发附件。

## 隔离Linux runtime与准入

不借用Taobo现有Python3.10/Torch2.7。源码内[完整Linux runtime来源锁](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s01-e028-target-spatial-qualification-20261019/docs/research/S01/S01-E029/taobo_runtime_spec.json)指定CPython3.12.14官方source 20820300bytes/SHA `5c8462af5790baf43a321a1559dbe0db06d1be4300fb85fb53c40060668e548a`，以及42个Linux wheel的逐URL/SHA，含CUDA12.8与Linux条件依赖。审批覆盖在专属 `/mnt/data2/drtao/wennie/S01-E029-R001/runtime`内下载这些固定artifact、make -j1编译Python、make -j1 COMPILEALL_OPTS=-j1 install安装及offline/no-deps安装这42包；不sudo、不改变系统/共享venv，不触碰其它任务。构建后生成完整runtime库存/hash/origin记录，wrapper保留可信runtime_lock摘要，系统stdlib在调用专属Python前核库存及所有文件；controller/worker复用同一可信摘要并按阶段复核。干净环境启动shell/编译/安装，不继承用户加载器或编译选项；独立父存活监督进程在wrapper消失时清理自己的阶段进程组。记录真实编译器/driver可用性；缺依赖/驱动/runtime错误止于同一首停链，不临时换版本或扩大安装。当前Mac只准备来源锁与代码，没有安装或编译runtime。

选中**GPU5 UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`**、逻辑cuda:0、CUDA_VISIBLE_DEVICES=5。启动/空间模型前再次检查：选中卡无compute、利用率0%、空闲>=8GiB；CPU<50%、RAM>=8GiB、磁盘>=32GiB。其它卡上的任务允许继续且不触碰；这是Linux共享平台的明确差异，不沿用Windows全机无Python限制。Linux权限只给自身proc元数据、任务runtime/字体清单和角色所需文件；只清理经PID/birth/UID/cmd/cwd核验的本任务树，不按用户名/进程名杀人。

## 本次唯一授权对象及命令

只有用户批准本版后才分别在Windows临时导出位置和Taobo `/mnt/data2/drtao/wennie/S01-E029-R001/approval.json`写入相同对象；当前文件不存在，源码execution_enabled=false保持：

```json
{
  "run_id": "S01-E029-R001",
  "reviewed_commit": "2dd8487f604112e061032e7a006367f344e74454",
  "source_manifest_sha256": "3cbde12cc84b8b8b677b04b5b182a1c7255f0cd41b1c30ada3fa7deff9645a4e",
  "execute_once": true,
  "wall_seconds": null,
  "GPU_uuid": "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
}
```

Windows原始字节导出（已接收精确source/catalogue/approval并核hash后）：

```powershell
C:\Users\xw436\pavetrack_env\Scripts\python.exe "C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-export-v1\scripts\pavetrack_qualified_spatial_selector\e029_migration.py" export --catalogue "C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-export-v1\private_catalogue.json" --archive "C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-private-v1.tar.gz" --approval "C:\Users\xw436\pavetrack_stage\S01-E029-Taobo-GPU5-approval.json" --reviewed-commit 2dd8487f604112e061032e7a006367f344e74454 --catalogue-sha256 5dc25418f62a6493ad0412d24d6d253b6f23e8b42471308d701bb0f7783adb66
```

Taobo仅在读取实际Windows导出receipt并核整包SHA/bytes后接收：

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 /usr/bin/python3 -I -B "/mnt/data2/drtao/wennie/S01-E029-R001/source/scripts/pavetrack_qualified_spatial_selector/e029_migration.py" receive --archive "/mnt/data2/drtao/wennie/S01-E029-R001/S01-E029-Taobo-GPU5-private-v1.tar.gz" --server-receipt "/mnt/data2/drtao/wennie/S01-E029-R001/S01-E029-Taobo-GPU5-private-v1.tar.gz.receipt.json" --root "/mnt/data2/drtao/wennie/S01-E029-R001/private" --approval "/mnt/data2/drtao/wennie/S01-E029-R001/approval.json" --reviewed-commit 2dd8487f604112e061032e7a006367f344e74454 --catalogue-sha256 5dc25418f62a6493ad0412d24d6d253b6f23e8b42471308d701bb0f7783adb66
```

唯一R001生命周期命令（CPU编译/版本与设备预检→原十phase→固定成功/停止包；detached并记录实际PID）：

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 /usr/bin/nohup /bin/bash --noprofile --norc "/mnt/data2/drtao/wennie/S01-E029-R001/source/scripts/pavetrack_qualified_spatial_selector/producer_taobo.sh" "/mnt/data2/drtao/wennie/S01-E029-R001/source" 2dd8487f604112e061032e7a006367f344e74454 3cbde12cc84b8b8b677b04b5b182a1c7255f0cd41b1c30ada3fa7deff9645a4e "/mnt/data2/drtao/wennie/S01-E029-R001/approval.json" >"/mnt/data2/drtao/wennie/S01-E029-R001/launcher.stdout" 2>"/mnt/data2/drtao/wennie/S01-E029-R001/launcher.stderr" </dev/null &
```

外层先验证manifest和全部源码，再创建一次launch_claim；任何有claim/Run/partial/已有runtime的冲突均先查现场，不重复调用。取消墙时不取消count/资源/首停。任何有效失败留首因及尽可能完整的stop包；写盘失败仍清理。bootstrap/库/私有输入/实际吞吐都由这一次已批链验证，没有额外真实微测、R002或隐含重试。

## 固定结果取回与验收

结果固定于 `/mnt/data2/drtao/wennie/S01-E029-R001/S01-E029-R001-fixed-v1.tar.gz`及同名`.receipt.json`；完整与停止均同一路径，部分包不覆盖。先读实际server receipt bytes/SHA再将同一对象取回自己的Mac `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/`。本次审批同时覆盖这一次接收、核验、独立证据复算/三原图README验收及归档，不再另加普通取回许可。

```sh
python scripts/pavetrack_qualified_spatial_selector/receive.py --archive "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/S01-E029-R001-fixed-v1.tar.gz" --out "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/evidence" --server-receipt "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/S01-E029-R001-fixed-v1.tar.gz.receipt.json"
```

评价只在六模型/全部held/B1冻结后读取角色许可的原12地点目标；按各scope own1FP/image operating point核9/12的旧/新/失/净与主D、gate/前三轨迹和模型/来源链。停止或不全保持null，不写净0。所有新确认/封存地点继续不解码/评分；没有事后改交集、权重、threshold或挑图救结果。三图是原固定保存的F00/F01/F02，原图验收与独立数字复算不能被Code Ready或接收成功替代。

当前仅本地准备/审查及待批版本，无生产执行或私有数据迁移。GPU5空闲为既有快照，必须在实际批准执行链重新核验。
