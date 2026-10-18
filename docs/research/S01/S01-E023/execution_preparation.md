> 2026-10-18更新：本精确版本已按用户本轮授权完成传送、指定公开分支推送、唯一R001及固定结果接收核验。下文保留执行前准备历史，实际状态见execution_status.md与runs/S01-E023-R001/result.md。

# S01-E023-R001 执行准备（未传送、未推送、未执行）

精确实现 ba596aa2acc7737b818c535befbbf8f6711152e0；方案 e5b490b9190026f547a2a3dc372c988f5480fc66。用户选定的6.1 sol-Medium独立设计审查通过；代码最终结论见 implementation_status.md 与 docs/reviews/S01-E023_code_review_20261018.md。仅源码/合同/测试，219绑定、220成员；manifest SHA a9b478c449fe0a3d5bfab3b02ded37589ec30c9c0a2b5635f923f83b60e2c2e9。

本地包：local_archive/experiments/S01-E023/prepared_R001/S01-E023-R001-v1-ba596aa2-source.tar.gz，589939bytes，SHA 470168e18ce3524ef97c989c180f6502f18a7705e8a4797682621dd49a2f4745。已逐项核对220成员。任何源码修改使当前包失效，须重新绑定复审与包。

私有输入另置 prepared_R001/private_input/train_polygons.json，1546138bytes，SHA 98542eb41ec03eebf7a1f73ddf372dc36bb4432aefa259a6e4e3e168e202e3e9。来自已审计835允许训练图/850标注，其中819裂缝区域多边形。此附件不可进入公开分支；未来仅传至 C:\Users\xw436\pavetrack_inputs\S01-E023\train_polygons.json，loader按data_lock核验。原Excel只是本地来源，不需要传送整本工作簿或额外地点。

未来指定公开分支 codex/s01-e023-pixel-supervision-20261018，基于已公开E022 d893c5fb7a5d8f9a058d7ea48d919fda163f4949 生成source-only提交，核219绑定后方可推送。本轮尚未生成/推送公开E023提交，无SSH或任何输入/源码传送。

未来唯一R001 producer为gpu-server/D-26-09/ad\xw436，物理GPU1/逻辑0，CPU1、3600秒、聚合RSS4GiB、GPU allocated/reserved各4GiB，8GiB临时空闲盘、证据包<=2GiB。启动前核验GPU UUID/占用与固定运行时、原19成员/metadata/E003 checkpoint/835图身份；新source/run/log目录，断线先查状态，不重试/换机/放宽。入口 scripts/pavetrack_pixel_selector/producer.ps1 参数 Source、ReviewedCommit、ManifestSha256；包装进程须脱离SSH保存PID及日志。

预算：835source+最多6case图片读取，31156冻结backbone contexts，无分类器调用/梯度/更新；977052160bytes特征payload；996992像素训练样本、93468地图行、3pixel+9role=12线性求解。held像素参考仅在OOF/模型/maps冻结后做组件评价。人工多边形是区域包络，不是物理宽度真值；像素样本多不增加独立有益GT3/5/6。

决定性问题：原前三容量下有益修正能否入选、进入实际检测预算并形成保旧OOF净收益。一次pooled12条件OOF相对E003684旧命中，旧保留>=95%、净GT>=1且macro召回变化>0。原框/分数/次序、容量与弃权不变，不扫交集。若仍前三0/全弃权，停止固定中间层41系数pixel-ridge方案，无R002、换层/采样/阈值/L2/容量救结果；保留组件证据，另定有新依据的路线。新确认/validation/reserve与旧资格排除地点封存。

本请求授权到冻结、独立审查、实现与合成测试；真实R001未执行，合成收益不能计为实际效果。
