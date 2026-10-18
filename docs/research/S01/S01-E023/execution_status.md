# S01-E023-R001 执行收据

2026-10-18 用户明确授权精确源码、私有标注传送、指定公开分支推送及唯一R001。此前准备状态已被本次授权更新。精确审查源码 ba596aa2acc7737b818c535befbbf8f6711152e0，manifest a9b478c449fe0a3d5bfab3b02ded37589ec30c9c0a2b5635f923f83b60e2c2e9；220源码成员服务器端逐项SHA核验。公开source-only提交 fd85517f62b128ef99cb20df5550076d661d5ffa，指定分支 codex/s01-e023-pixel-supervision-20261018，远端读回一致，14项新增仅源码/合同/测试。私有850行标注单独传送至data_lock固定路径、SHA核验一致，不进入公开分支。

服务器D-26-09/ad\xw436，GPU1固定UUID/WDDM桌面进程白名单/0%活动核验通过；835训练图存在性/身份清单、checkpoint、原始19成员包、metadata和固定运行时核验通过。无其他Python计算，CPU6%、空闲RAM约231GiB、磁盘约2.5TiB，预算未放宽。预检未解码源图。

启动：2026-10-18T12:53:16.5082534+01:00；Win32_Process.Create脱离SSH，wrapper PID 29304。运行目录 C:\Users\xw436\pavetrack_runs\S01-E023-R001；源码 pavetrack_stage\S01-E023-R001-v1-ba596aa2。3600秒、CPU1、RSS4GiB/GPU allocated-reserved4GiB、原前三/弃权/检测及交集规则不变。唯一执行，无重试/额外地点。当前真实结果待程序结束，不能以启动/预检通过计作收益。

本地详细SSH/transfer/publication/launch日志：local_archive/experiments/S01-E023/execution_R001/。

## 最终状态（2026-10-18）

R001 completed，1087.031秒/RSS3140538368bytes（2.925GiB），GPU allocated48395264/reserved73400320bytes，所有计数完整且预算未放宽。原835图31156contexts/996992像素样本/93468maprows/12solves；841图像读取，无CNN参数更新、额外地点、重试或交集扫描。

主标准negative：旧684/684保留，新增/损失/净0，macro0；有益GT3/5/6全部留池、最大/所选入前三均0，三模型弃权。区域Brier0.171709差于常数0.034257；全contextDice0.113087、参考前景context子集地点均Dice0.358392。固定像素ridge家族停止，研究主线保留。

固定65成员ZIP1007307504bytes，SHA02a60f57bf8050873f4cbd7ed2f599af95cc16a114ad804884e213e0bf8dde37，已取回local_archive/experiments/S01-E023/runs/S01-E023-R001/。核验SHA/CRC/严格清单/全部输出/19输入/私有标签/模型-OOF-maps冻结/featurecache/43347原行和资源。四实际PNG/README已由HQ打开验收，FIT六图明确非OOF新增；没有追加独立证据审查或新计算。事实源runs/S01-E023-R001/result.md、run_receipt.json及local saved_summary.json。
