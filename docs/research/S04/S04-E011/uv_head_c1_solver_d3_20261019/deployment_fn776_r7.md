# FN776-r7：GPU7 已核验 uvicorn 服务的最小准入修订

2026-10-25。r6 已在 Taobo 完成只读预检，但 GPU7 PID 651952 当时不属于其冻结的双服务白名单，因此在上传、部署、五文件读取或 solver 前安全停止；r6 的证据和路径均保持不变。

r7 使用新的 Card、索引、Run、root 和 archive。它唯一实质性控制面改动是加入第三个精确 GPU7 常驻服务：PID `651952`、start ticks `541746716`、UID `[0,0,0,0]`、cmdline SHA-256 `be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808`、cgroup SHA-256 `a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e`。三次只读样本均为 Docker scope 内 `python -m uvicorn app.main:app --host 0.0.0.0 --port 28011 --workers 1`，占用 `5638 MiB`、GPU 利用率 `0%`；r7 将其上限固定为 `6144 MiB`。身份、PID 集合或上限漂移即拒绝或只终止本次 child，绝不触碰该服务或任何其他进程。

完整 776 维平方根 Newton、同一 c1s4 U=.11999988、固定 388 基底、五个输入的路径/大小/hash/受限解码、16 外步、每步最多 32 次 Armijo trial、最多 3 次线性细化和 25424 单位账本都保持不变。这些是固定算法范围，不是资源配额。

本 Run 没有自用 wall-time、RSS、CUDA 或输出大小上限；时间、RSS、CUDA 保留量和输出量仅作遥测。GPU7 UUID、精确三服务身份及其显存上限、12GiB 初始和 4GiB 运行显存余量、宿主 16GiB 可用内存及 data2 5GiB 空闲空间仍是共享机器保护。SSH 和每个远程查询的有限超时只约束该次 transport/control client，不会限制已派发的 solver。

一次 guard/numerical solve 是唯一科学尝试。任何未知 launch 只读观察，绝不重发；任何数值、输入身份、Armijo、驻点或科学合同问题停止并与研究负责人讨论。技术性终态必须保存收据、审计远端状态并以新的身份重新准备，不能覆盖或复用旧 root/archive。
