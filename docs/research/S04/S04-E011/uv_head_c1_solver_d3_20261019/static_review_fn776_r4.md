# FN776-r4：网络执行上下文差异静审回执

审查范围仅为本地 r4 准备材料的身份、包、计划和卡的一致性；没有 SSH、远端资源
查询、科学数组读取、控制入口调用或数值计算。

| 项目 | 已核对值 |
|---|---|
| Card / 索引 | S04-E011-UVH-C1-FN776-CARD-r4 / S04-E011-FN776-r4-A1 |
| Dev | 2a71db70fa898635b0bd664f63f398fb41855470 |
| Producer | f808c9ae96fdd68fe94f59b0a1d3d360ce7977ff |
| Controller blob | ea0ccc6a44d47abbaed38f5ed5eaecc8106d163a |
| Plan SHA256 | 368bc89c57848a10cd84d04bb45b8eee93772481a0efa66b37e1064ea4ffd216 |
| Card SHA256 | 3f881ac6e86699d79aab1988e9ef51b04c65869d56c981c7b68ef1300420e64a |
| Bundle | 198396 bytes / b3831ae9a00aeeb369cbeb27dd6395c6f65eaa97e1c8bb9561dd2cb0c06b00da |

结论：**本地静态差异通过。** r3 的 claim、terminal 与 stderr 均保持原样：其预检
SSH 客户端在 TCP 连接前被本机执行沙箱以 exit 255 / `Operation not permitted` 拒绝，
`retry_allowed=false`；没有把该失败清除、修复或重开。

r4 的 Card、计划、契约、控制器和自包含包身份互相一致。包为 51 个文件、22 个
本地模块闭包，完整 fsck 与 materialization verifier 通过。`worker.py`、
`square_root.py`、力学源、科学协议、五输入清单、GPU7 政策、所有判据以及
25424 单位／900秒／8GiB／100MiB预算均保持不变。

相对 r3，唯一实质差异是新的 Run 身份、相应包路径与 hash，并在计划中明确要求：
精确控制器必须从获准联网的执行上下文启动。远端命令逻辑、私有 SSH 参数、阶段
超时和失败不重试联锁未变。

本回执不验证该执行上下文是否已获权限、当前远端资源、连接可用性、数值收敛或
科学可行性，也不构成 r4 执行授权。
