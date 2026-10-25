# S01-E029 运行库来源修复与继续执行：最终审批版

当前：本地已准备，本版尚未传送、推送或启动。此前源码与509成员输入已送达Taobo；科学前向/拟合/检测评价均未开始。此次只修环境来源识别，继续同一S01-E029-R001。

## 已发生什么

上一条环境链在82.6秒停止：固定NVIDIA地址跳转到区域域名 `pypi.nvidia.cn`，未在原来源清单中。停止包已取回并核验，10成员、14490bytes、SHA `6f60ce4464b3aeeb3b50cd602df4babdef558cf4db0a2634f4176343c3bfa8bd`，位置 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/`。原wrapper及两个受管子进程均已退出，清理无未决项，原run/runtime不存在。没有检测保留率或净收益读数，不能记作净0或科学失败。

## 修复内容及已做核验

仅增加精确域名 `pypi.nvidia.cn`；16个原NVIDIA地址的HEAD均确认此跳转，2283字节cuda-toolkit文件与原冻结SHA `adc7906af4ecbf9a352f9dca5734eceb21daec281ccfcf5675e1d2f724fc2cba`一致。42个wheel的版本/原URL/文件SHA及Python来源均不变，Python程序逐字节不变。科学四臂、数据/GT角色、E003、容量、弃权、正面积交集、次数、结果标准及封存范围不变。

直接一致性核验已完成：三份配置/合同和重建manifest之外无差异；源码包269成员与精确Git对象一致，268绑定正确；原v5固定77项基准结论复用，不重复未变测试或科学计算。[核验记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v6_pending_20261025/direct_consistency_checks.json)。

旧环境停止目录保留。本次使用新子目录 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01` 放置源码、授权、运行库、日志和结果；原私有输入仍读 `/mnt/data2/drtao/wennie/S01-E029-R001/private`，图像仍读 `/mnt/data2/drtao/wennie/S01-E029-R001/private/images`，无需再次跨机传送约596MB私有包。没有新增数据或开放新确认地点。

## 本次发送账号、对象、附件和发布版本

发送端：自己的Mac `wenxiaofang`。接收端：`gpu-taobo / GPUServer8 / drtao`，只写 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01` 及其子目录；原目录只读保留。发送附件：

- [完整源码包](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v6_pending_20261025/S01-E029-R001-Taobo-source-v6.tar.gz)，575018bytes，269普通文件；SHA `7a30c24577bf9544c70f6061f041749517a727bf2537b6202a2175b65902cbe6`。
- [待批准授权对象](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v6_pending_20261025/approval.pending.json)，完整字段如下。批准后才写为 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/approval.json`，当前远端新目录不存在。

公开对象：`git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git`；预期SSH账号`wenniebyfoxmail`、Git作者`xiaofang wen <wennie_wen@foxmail.com>`，分支 `codex/s01-e029-qualified-spatial-utility-20261020`。此前已推送 `34ec77ef29674622cf4d87bb46912fe4943aea14`；本次拟推送源码 `a99e97d5a2be9c39083d0c557d22c9bf16b21562`，manifest `008db789115d9f11cd4852065ffdb043610b461bdaeb489bd755603a521607e2`。公开仅源码/配置/既有科学合同，私有输入、原catalogue、权重、结果不进入公开分支，本审批文档留本地。

```sh
git push origin a99e97d5a2be9c39083d0c557d22c9bf16b21562:refs/heads/codex/s01-e029-qualified-spatial-utility-20261020
```

## 授权内容和唯一启动命令

本版请求批准：上述新版本传送、指定分支更新、在新子目录重新完成环境准备并继续这次尚未开始的R001科学运行，以及同次固定结果取回验收。保留上一条环境停止包，不覆盖旧claim/日志/源码，不造R002。若已开始模型前向或拟合后停止，不自动重新运行科学部分。

继续沿用用户已声明的任一合格Taobo GPU选择范围；当前候选GPU5/UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`。实际启动前重新检查各卡，可仅按该范围自动实例化GPU/UUID等设备记录并更新相应命令与摘要；Python程序、依赖文件身份或科学内容变化不包含在此项设备实例化中。其它账号/producer、额外数据或科学重试需另行决定。

任务墙时/RSS/CUDA/输出/结果包硬上限均为null；单线程数值设置、精确科学次数与共享安全准入保留：选中卡无compute、0%利用率、至少8GiB显存空闲，CPU<50%、可用RAM至少8GiB、大盘余量至少32GiB。不改共享运行库或全局配置，不触碰其它任务。

```json
{
  "run_id": "S01-E029-R001",
  "reviewed_commit": "a99e97d5a2be9c39083d0c557d22c9bf16b21562",
  "source_manifest_sha256": "008db789115d9f11cd4852065ffdb043610b461bdaeb489bd755603a521607e2",
  "execute_once": true,
  "wall_seconds": null,
  "GPU_uuid": "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
}
```

输入原509文件由wrapper按原catalogue/每项SHA重核。随后仍是同一运行库来源锁与42依赖、CPU单线程构建、版本/设备检查、原十phase与固定打包流程；不额外做模型微测。当前源码execution_enabled=false保持，以外部授权对象决定启动。

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 /usr/bin/nohup /bin/bash --noprofile --norc "/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/source/scripts/pavetrack_qualified_spatial_selector/producer_taobo.sh" "/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/source" a99e97d5a2be9c39083d0c557d22c9bf16b21562 008db789115d9f11cd4852065ffdb043610b461bdaeb489bd755603a521607e2 "/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/approval.json" >"/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/launcher.stdout" 2>"/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/launcher.stderr" </dev/null &
```

记录实际PID/出生时间/命令及新claim。失败留原停止原因与固定包，不把未知状态当退出，不重复spawn。结果固定 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_01/S01-E029-R001-fixed-v1.tar.gz` 及其receipt；先读真实服务器bytes/SHA，再取回 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/mechanical_resume_01/`，用同一接收器 `--unlimited-resources` 验CRC/两份清单/逐文件SHA；若完成科学部分，再核数字、原三图和README，汇报有益修正是否进前三、E003旧检测保留及实际净收益。若环境再次停止，科研读数仍保留null。

本次新增审批源于用户最新总纲3.1的“批准仅限该次账号、对象与版本”；不把未变的代码审查、版本发现或普通检查另设为人方决定。
