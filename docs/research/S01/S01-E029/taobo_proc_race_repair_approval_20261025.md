# S01-E029 进程退出竞态修复：v7 最终发送审批版本

本地准备完成，尚未传送、推送或再启动。v6按用户批准执行，NVIDIA区域下载和独立运行库/设备检查均成功；随后进程监督退出竞态停止，科学run仅launch.json，首个科学worker尚未请求。两条停止记录保留。

## 修复与验证

Linux进程退出时，/proc读取可返回ESRCH（ProcessLookupError）。仅在stdlib进程适配器的stat、UID、cmdline、cwd读取和身份检查后的信号操作处，将它归一为既有NoSuchProcess，由原监督/清理逻辑处理。权限错误、意外I/O、PID出生身份、UID/命令/cwd校验均保持。旧版故障复现；六项针对性mock回归与28项原Linux检查通过，未运行真实GT、图像或模型。测试记录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v7_pending_20261025/test_receipt.json`。

科学程序、42依赖身份、来源清单、E003原检测、容量/弃权/正面积交集、结果标准和数据封存不变。不扫描阈值。任务资源硬上限仍无，共享准入和余量保护保留。新目录mechanical_resume_02，复用原私有输入；已建运行库留存，新根按原流程重建，不修改旧runtime/claim/源码/日志。继续尚未开始科学计算的同一次R001，开始科学后若停不自动重跑。

## 本次账号、对象和精确附件

发送端：Mac wenxiaofang；接收端：gpu-taobo / GPUServer8 / drtao。只写新根 `/mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_02`。源码包 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v7_pending_20261025/S01-E029-R001-Taobo-source-v7.tar.gz`，576386bytes、270普通文件，SHA `11a0cd02acd6e60a4bda964e238ffe1a8d10b4c15c220b37dfed6cf8ca4d0e69`；待批准对象 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/linux_preparation_v7_pending_20261025/approval.pending.json`，批准后写新根approval.json。原private目录只读复用，不再次发送私有数据。

GitHub SSH账号wenniebyfoxmail；Git作者xiaofang wen <wennie_wen@foxmail.com>；对象 `git@github.com:wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git`，指定分支 `codex/s01-e029-qualified-spatial-utility-20261020`。仅正常前推源码 `eb0b11ded518d8fc78fd41a58f147fd06342d04a`，tree `5571156d80e88ba91b5b6614f84b7df8aa221cd2`；manifest `9858d1fc5f7b5679847c545af7bb847316cd5eaf5b9c4e210607e0f7a51d3f95`。私有输入/权重/结果不进入公开分支。

```sh
git push origin eb0b11ded518d8fc78fd41a58f147fd06342d04a:refs/heads/codex/s01-e029-qualified-spatial-utility-20261020
```

## 一次启动授权对象和命令

```json
{
  "run_id": "S01-E029-R001",
  "reviewed_commit": "eb0b11ded518d8fc78fd41a58f147fd06342d04a",
  "source_manifest_sha256": "9858d1fc5f7b5679847c545af7bb847316cd5eaf5b9c4e210607e0f7a51d3f95",
  "execute_once": true,
  "wall_seconds": null,
  "GPU_uuid": "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
}
```

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 /usr/bin/nohup /bin/bash --noprofile --norc /mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_02/source/scripts/pavetrack_qualified_spatial_selector/producer_taobo.sh /mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_02/source eb0b11ded518d8fc78fd41a58f147fd06342d04a 9858d1fc5f7b5679847c545af7bb847316cd5eaf5b9c4e210607e0f7a51d3f95 /mnt/data2/drtao/wennie/S01-E029-R001/mechanical_resume_02/approval.json
```

由operator重定向新根launcher.stdout/stderr、断开stdin并记录PID/出生标识后唯一启动。沿用任一合格Taobo卡授权，启动前再核验各卡：选中卡无compute、0%利用率、至少8192MiB空闲，CPU<50%、RAM>=8GiB、磁盘>=32GiB。仅GPU/UUID和关联设备摘要可自动实例化，科学/Python/依赖改变不在设备实例化范围内。

固定结果或停止包从新根取回 `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E029/runs/S01-E029-R001-Taobo/mechanical_resume_02/`；按真实服务器bytes/SHA、CRC与清单验收，科学完成后核原图、保留率和实际净收益；缺失指标不填零。

请求批准的完整范围：本v7最小修复源码及授权对象传送、上述指定分支更新，在合格TaoboGPU继续同一次尚未开始科学计算的R001及固定包取回验收。总纲3.1要求“批准仅限该次账号、对象与版本”；因为本次新增Python修复，需要本版批准，不能沿用v6来源修订的发送许可。
