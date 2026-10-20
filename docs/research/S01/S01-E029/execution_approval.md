# S01-E029-R001 精确执行决定（完整执行审批版，未执行）

目的：一次验证冻结空间定位组件能否让有益修正进入原前三，并在保住E003的条件下得到比固定强对照更多的实际净GT。完整本地代码准备不另请求审批；本页的最后决定只针对新一次传送/公开推送/生产执行。当前execution_enabled=false，授权文件不存在。

## 拟发送账号、对象与版本

Mac owner wenxiaofang → `gpu-server` / `D-26-09` / `ad\xw436` 的全新 `C:\Users\xw436\pavetrack_stage\S01-E029-R001-v3`。只传送精确源码档案，不传私有GT/标注/图像；11项原私有输入在服务器按冻结摘要只读复用，位置及版本下表。目标仅物理GPU0 UUID `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`，logicalcuda0，不回退Taobo或其它卡。

拟公开对象 `git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git`，指定新分支 `codex/s01-e029-qualified-spatial-utility-20261020`，source-only commit `5307a6f52a0877ad56f13df6efeb86e1481df6d6`，direct parent `efbf54c66d41840768de33d001670f7020a4a52c`，public base `b675c51b62ca8d793067a64467351c13d0644213`。本地Git作者 `xiaofang wen <wennie_wen@foxmail.com>`；SSH key对应账户及远端分支实时状态本轮未连网核验，执行获批后先读回，非预期即停，不替换账号/force-push。预期GitHub发送账号wenniebyfoxmail；SSH身份读回非预期即停。source-only差异不包含新结果、审查记录、运行数据、私有标签或权重。

源码包：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/production_v3/S01-E029-R001-source-v3.tar.gz`；530050 bytes / 253普通文件，SHA256 `790dbba6ea1804fe3d3f4b04f4ebf6d21770b714796c7d54ac9dbd23fc069d3b`。source_manifest 252绑定、SHA256 `7e4a45c848f6122d4e05a9c2104d485f35fdae9da9a04515208f302aaec3727c`。公开分支commit/源码档案和拟运行源码是同一绑定，不用owner内部结果commit替代。独立gpt-6.1-sol / High代码复审REVIEW_PASS；49项人工/mock测试和全部绑定通过。正式报告：[production v3独立报告](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/production_v3/independent_review.md)；汇总：[代码审查记录](../../../reviews/S01-E029_production_code_review_20261020.md)。

公开推送的完整动作（未执行，不force）：

```sh
git push origin 5307a6f52a0877ad56f13df6efeb86e1481df6d6:refs/heads/codex/s01-e029-qualified-spatial-utility-20261020
```

之后从同一origin读回该ref确认精确commit；检查既有其它分支时不更改。源包传送后只在全新目录解包，逐252文件身份核验，旧共享checkout/venv不变；source路径已存在或未知传送状态即核查首停，不自动覆盖/重发。

## 唯一拟执行命令

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\Users\xw436\pavetrack_stage\S01-E029-R001-v3\scripts\pavetrack_qualified_spatial_selector\producer.ps1" -Source "C:\Users\xw436\pavetrack_stage\S01-E029-R001-v3" -ReviewedCommit 5307a6f52a0877ad56f13df6efeb86e1481df6d6 -ManifestSha256 7e4a45c848f6122d4e05a9c2104d485f35fdae9da9a04515208f302aaec3727c -ApprovalFile "C:\Users\xw436\pavetrack_runs\S01-E029-R001-approval.json"
```

仅在用户明确批准本版后才在上述专属路径写下列一次授权对象（本页仅展示，尚未生成可用授权文件；源包开关保持false）：

```json
{
  "run_id": "S01-E029-R001",
  "reviewed_commit": "5307a6f52a0877ad56f13df6efeb86e1481df6d6",
  "source_manifest_sha256": "7e4a45c848f6122d4e05a9c2104d485f35fdae9da9a04515208f302aaec3727c",
  "execute_once": true,
  "wall_seconds": 3600,
  "GPU_uuid": "GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7"
}
```

## 输入、成本和运行承诺

|逻辑输入|只读服务器位置|SHA256|
|---|---|---|
|E017_zip|`C:\Users\xw436\pavetrack_runs\S01-E017-R001\delivery\S01-E017-R001-evidence-v1.zip`|`189f1cb23688013c3692c8cc3dfb0df1400ac6f01ac6b65316c4cd180314cd6d`|
|metadata|`C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\development\manifest_train_validation.json`|`6fc622943a78063926d96a13e727013ae22d12919a3af3814cfc221bd1a7e5bb`|
|contexts|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\pixel_contexts.json`|`eba16f6623e7eaf209f7e40f8ca0368a41fb7b4a9b93021ebcda57eae7c4a325`|
|R002_scope|`C:\Users\xw436\pavetrack_runs\S01-E028-R002\scope.json`|`a414473eb65a51b242b7799a5653368d40425317650face52444a2523500e160`|
|R002_projections|`C:\Users\xw436\pavetrack_runs\S01-E028-R002\projections.npz`|`898bac8fb30b7dc8ae18d6beddcd8390456ce5062c2d077c3dbc639334ae0be1`|
|checkpoint|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\DeepCrack_CT260_FT1.pth`|`945239375c2b3de45abccc2dbdc374e3259b55d16298b298fb9e0cd13be5ad63`|
|network|`C:\Users\xw436\pavetrack_stage\S01-E028-R002-v1\private_inputs\deepcrack.py`|`92650883b6f6c993bc29635450035e066c968c4f5a9022a6c1966a0b9f0d3360`|
|E018_OOF|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\OOF_predictions.json`|`0d883cae8e22a3f00054afb258a6ed65d8e4fea12d924af7a1330ba17c3badf2`|
|E018_model_0|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_0.json`|`39f169d49eed1743ede3b2b6d55237063d7eecfc2646edb48481b714a7653dbe`|
|E018_model_1|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_1.json`|`ac5ea38f2688ca2d13a80b99ca89bad8ebab1eb758853ed5634a4f57b7537792`|
|E018_model_2|`C:\Users\xw436\pavetrack_runs\S01-E018-R001\model_fold_2.json`|`91a1cc32e0f6a7b9d4c8d42b83fd843d4b662ef35740d1fbe6823f13cc684ab3`|

metadata的完整SHA已冻结，未在本轮打开其GT；其实际bytes/存在性在同一执行链首停核验，不另跑取样。源图身份从已固定E017候选派生，只允许835旧train图；338图直接复用R002的12238投影，剩497图需19880次native前向、0cached前向。空间权重不训练，S/M各3fold/合计18solve；B1只重放冻结模型。完整依赖/GT角色和预算见production_contract.md/run_config.json，不新增GT、地点或留出访问。

运行上限总3600秒（准入/生产3480＋打包预留120；实际工作截止100/3460/3580秒，各保留清理时间）、CPU1、RSS及CUDA allocated/reserved各4GiB、output/archive各2GiB、空闲>=16GiB。E028的剩余预算不抵扣/不授权本Run。Windows运行库/PowerShell/驱动/实时共享GPU/私有输入可用性只在本次已批准链上核；任何失败先留原因/受管PID现场，再只清理本任务，固定停止包，0自动重试/换机/增预算。

固定四臂/11系数/固定错位/原group_cap3、1/image、弃权、正面积交集不改，不扫描权重或阈值。主九地点D与pooled9/pooled12零失旧保护原样；资格三地点含24与原12比较完整报告。三FIT8合法交叠不冒充全链独立OOF，九地点也已消耗，所有新确认/validation/reserve及353/1459/2028/5982继续封存。

## 结果取回、接收与验收

运行/日志：`C:\Users\xw436\pavetrack_runs\S01-E029-R001` 与同名`-wrapper-logs`；固定成功或停止对象 `C:\Users\xw436\pavetrack_runs\S01-E029-R001-fixed-v1.tar.gz` 与其`.receipt.json`。不全/停止不能填净0；打包若未完成保留.part和现场，不再试跑。

本次执行许可也覆盖同一固定结果从自有producer取回自有Mac、接收核验、归档与必要独立证据审查，避免再误加一个普通收尾审批。归档目标：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001/`。先读取已固定server receipt的实际bytes/SHA再取回同一对象，不预造结果哈希；接收命令：

```sh
python scripts/pavetrack_qualified_spatial_selector/receive.py --archive "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001/S01-E029-R001-fixed-v1.tar.gz" --out "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001/evidence" --server-receipt "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001/S01-E029-R001-fixed-v1.tar.gz.receipt.json"
```

接收核SHA/CRC/安全成员/双清单；之后只用保存预测/模型/旧评分引用独立重建九与十二地点的旧/新/失/净、D、每fold gate/前三链、三张原图F00/F01/F02及README，不能把接收或Code Ready当净收益。验收引用、图表与研究记录归档后决定集成/保留组件/停止固定配方，不自动启动R002或访问新地点。

当前止于本地最终包与具体执行决定；没有对外传送/推送、SSH/部署/占卡、真实模型/标签/GT访问、fit/infer/OOF或其它producer执行。
