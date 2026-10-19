# S01-E027-R001 待执行版本 — 2026-10-19

2026-10-19后续：用户已明确批准本版本传送/指定公开分支推送和唯一R001，已执行并取回，见 runs/S01-E027-R001/result.md。以下保留运行前准备记录，不代表当前仍待启动。

准备时仅本地准备完成；本轮未传送、未公开推送、未真实推理或训练。协议与精确预算见 experiment.md / run_config.json。本文件不扩大执行授权。

已审源码 `97db708e19d7eb9f5340bf18c6b57840887a09c7`，源码包15成员（14绑定文件及manifest）：
- 文件：S01-E027-R001-source-97db708e.tar.gz，31591字节。
- SHA256：`df3f8644edc8d3a72123a11d95d79e35abb876cc3ec0662083af335eb27a57ec`。

私有输入包恰好6成员：cfd.npz、cfd_identities.json、pavetrack.npz、pavetrack_identities.json、DeepCrack_CT260_FT1.pth、deepcrack.py；不包括准备receipt，不公开分发图像、标注、权重或第三方源码。
- 文件：S01-E027-R001-private-inputs-v1.tar.gz，111178335字节。
- SHA256：`d1f830dea041ae03e4f2debe3f3c8d75bfe4c666fb2bd6eac040b2995ddace53`。

两包及package_receipt.json均在 owner 仓库 local_archive/experiments/S01-E027/prepared_R001/。每个输入的身份、大小及摘要见 data_lock.json；源码与已审commit逐文件核验一致。

唯一拟执行对象：gpu-server / D-26-09 / ad\xw436，物理GPU1，UUID GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a。一次R001、CPU1、600秒、RSS与GPU allocated/reserved各4GiB、产物100MiB；一个固定checkpoint、56次单图forward、0拟合/更新。权重为输入，不重复收入产物。先停止、不自动重试、不换GPU。执行前核验原桌面服务与GPU身份，既有共享服务保持。

12张已暴露CFD开发图固定顺序，16个既有PaveTrack控制块；0新源图、资格参考或封存地点访问。全部预测及模型摘要先冻结，再解封评分参考。CFD主标准为至少7/12图的固定0.5阈值Dice超出五项简单/错配基线最大值>1e-6；只证明这批开发图上的发布边界响应。反序重复仅验证数值一致，不证明训练稳定性或泛化。PaveTrack仅作包络描述，域资格、前三入选、E003保留率与OOF净收益均留空。

通过来源检验后仍需独立的目标域资格方案，不能直接连接选择器。保留E003、原容量与弃权，不扫描交集阈值，新确认地点继续封存。
