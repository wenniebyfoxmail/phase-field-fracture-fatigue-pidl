# FN776-r5：r4 本地控制面终态后的工程性新身份

2026-10-25。r4 在 `local_package` 后进入预检时，本地操作员收据首字节为错误的 `+`，控制器在
解析 `thread_duplicate_check.json` 时停止。该错误发生在创建 SSH 子进程之前；没有远端 shell、
GPU/进程/路径状态、部署、五文件读取或科学计算。r4 终态回执保留，绝不重开。

r5 是新的 Run，仅修复控制记录的生成路径并使用新 root/archive。科学方法、五个输入、完整
776 坐标、随机种子、固定 16 外步/32 Armijo trial/3 线性细化、25424 工作账本、900 秒与
8GiB/100MiB边界、GPU7 UUID和共享服务保护均与 r4 一致。用户允许工程性重试；这不授权
第二次 guard 求解、数值停机规则改变、科学输入替换或未知 launch 重发。

Card：`S04-E011-UVH-C1-FN776-CARD-r5`。批准索引：`S04-E011-FN776-r5-A1`。
Run：`pf_s04e011_uvh_c1_fn776_r5_20261025`。
root：`/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r5_20261025`。
archive：`/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r5_20261025`。

控制器仍需从允许网络连接的执行上下文运行；不修改 SSH 配置、共享 master、VPN、主机、
凭据、GPU 服务或其他进程。每个技术重试之前保存前一终态并重新核对重复任务和资源；若
launch 远端状态未知，先只读观察，绝不重发 launch。
