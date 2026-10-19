# S01-E028-R001 本地待执行版本 — 2026-10-19

本轮按用户指令完成方案冻结、6.1 sol / High独立设计审查、实现/测试与精确代码复审；没有SSH/传送/公开推送/真实forward或训练。后续真实执行需批准此版本，不能沿用E027执行许可；本文件不新增预算或执行授权。

- 已审源码：b045170988b3f2a8fc641b7a7b89c617bb6c9e41；分支codex/s01-e028-target-spatial-qualification-20261019。
- source_manifest：24绑定，SHA256 11c67539cadac809aa22efc8b74689fd3f54fe5b719be93c1f5df4b400d5a76b。
- 源码包：S01-E028-R001-source-b0451709.tar.gz，55074字节/25成员，SHA256 2f6b9f39ad1498af02ee0fbe7e8b09ccba8e62a49877ac74f0ae56592bf5c3e0。
- 包与package_receipt：owner local_archive/experiments/S01-E028/prepared_R001/；9私有输入见data_lock.json，原路径清单在owner local_archive/experiments/S01-E028/input_paths.json，仅本地核验，未制作包含全部大输入的新归档、未传送。权重/原模型代码、RGB缓存、旧annotation与legacy参考等不进入公开分支。

未来一次R001：gpu-server/D-26-09/ad\xw436，物理GPU1 UUID GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a；CPU1/3600秒，RSS与GPUallocated/reserved各4GiB；输出及固定档案各6GiB、临时盘>=16GiB。338张旧资格图，12238个既有候选context，13520native512tile+12238cached128共25758forward，1checkpoint、0拟合/更新、0选择器/OOF。首次停止不自动retry，不换卡或放宽上限。服务器原路径/摘要、运行环境/旧桌面服务、共享GPU与磁盘在执行前另核，不把静态测试称为已实测吞吐。

唯一主候选native/max/.5/any不变；八组合共同R_any-FG集合、六固定比较器，至少一个原qualification pair的两地点均胜基线。全部预测先冻结再解码参考。原生输入同时改变尺度与上下文，不能把差异只归因于分辨率；部分包络不是精确像素真值。通过也不自动连接选择器；之后另冻GT-free角色学习/OOF预算和保旧净益标准。E003、容量1/image与3/group、弃权、正面积交集、不扫描交集阈值、新确认地点封存保持。
