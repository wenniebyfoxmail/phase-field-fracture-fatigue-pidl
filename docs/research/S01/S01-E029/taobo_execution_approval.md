# S01-E029 Taobo GPU5：迁移及一次R001完整审批版（待用户批准迁移与执行）

目的：让已合格的空间信息帮助有益修正进入原前三，在保住E003的前提下产生实际条件OOF净收益。此版只适配Linux平台；原四臂、FIT/held角色、固定交集、容量/弃权、9/12保旧和主D都不改。新确认/validation/reserve与353/1459/2028/5982继续封存。九主地点仍为旧开发数据，不当独立新地点。

用户已明确取消3600秒预算限制。本次配置和授权对象的wall_seconds均为null，没有另加替代总时限；按精确497图/19880forward、18solve等原工作量结束并记录各阶段elapsed。CPU1、单GPU、RSS/CUDA allocated/reserved各4GiB、研究输出/结果包各2GiB仍限制；Linux任务起始/监督空闲磁盘>=32GiB。不得用取消墙时增加数据、fit、随机种子或阈值扫描。

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
