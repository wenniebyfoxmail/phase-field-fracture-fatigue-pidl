# S04-E011 FN776-r5：r4 本地收据错误后的工程性重试卡

## 身份和授权链

| 项目 | 精确值 |
|---|---|
| Card | `S04-E011-UVH-C1-FN776-CARD-r5` |
| 批准索引 | `S04-E011-FN776-r5-A1` |
| 新 Run | `pf_s04e011_uvh_c1_fn776_r5_20261025` |
| Dev | `56a504b8016227d93dc5f4f9beacf3dbfa8831c9` |
| Producer | `6eb6c64effc76d7f34f05daa6959e418f7f0293c` |
| controller blob | `0998524d497dd43b166ab2117eab35973995d095` |
| plan SHA-256 | `fdcf831d7ae75127678f2a2e3846c9496b590c6ce44b6382132c8e1412069f68` |
| Bundle | `196501` bytes / `467fa59af7bf9550ef05c9d4d834e9e955fd330309388deacc30b5cd0a924aa3` |
| GPU | Taobo物理GPU7，`GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81` |

r4 的本地包完整性检查成功；随后在本机解析错误格式的线程重复检查收据时终止。该异常发生在 SSH
子进程创建之前：没有远端 shell、GPU 检查、路径创建、部署、五文件读取或科学计算。r4 的
`terminal.json` 保留原样。r5 使用全新 root 和 archive，仅作为这次工程控制面错误的重试。

用户明确允许工程性重试。本卡仍只允许一次 guard 和一次数值求解：SSH/传输/部署等技术终态可
在保留原始收据、核对远端实际状态并新建身份后重新准备；未知 launch 不重发。五文件一旦开始
读取，任何数值、输入身份、Armijo、驻点或其他科学性问题均暂停并讨论。

## 科学合同保持不变

完整 776 维平方根 Newton、c1s4 U=.11999988、固定 388 基底、五个输入的全文件 hash 与
受限解码、16 外步、每步至多 32 个 Armijo trial、最多 3 次线性细化、25424 工作账本、
阈值和最终双读回均与 r4 相同。`worker.py`、`square_root.py` 及冻结力学源码 blob 保持不变。

900秒、8GiB RSS/CUDA、100MiB输出与 12/4GiB GPU 余量仍保留。它们是被命名卡锁定的
数值停机/可比性条件；取消它们会改变该诊断的含义，因此不在一次工程性重试中悄然修改。
GPU7 UUID、已审服务身份、NVML/CUDA健康、路径和重复检查也保持为共享机器保护；绝不停止、
重启或修改他人进程。

## 执行序列

先在允许网络的控制器上下文执行 `local_package`、新鲜对话重复检查和只读 Taobo 预检；预检
通过后才上传本 bundle、空仓物化和验证。guard 自行在重复/资源准入后读取五文件并启动唯一
求解。仅在 guard/worker 都确认退出并有终态后取得 manifest、归档和本地 hash/size 验证副本。

```bash
FN776_R5_CTRL='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_r5_20261025/package_56a504b8/materialized/code/tools/s04_e011_fn776/control_r2.py'
FN776_R5_PLAN='/Users/wenxiaofang/phase-field-fracture-with-pidl/_isolated_worktrees/s04-e011-fn776-r5-unbounded-20261025/docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/execution_plan_fn776_r5.json'
python3 -B "$FN776_R5_CTRL" --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r5 --approval-index S04-E011-FN776-r5-A1 --plan "$FN776_R5_PLAN" --plan-sha256 fdcf831d7ae75127678f2a2e3846c9496b590c6ce44b6382132c8e1412069f68 --step local_package
```

逐步换 `--step` 为 `preflight`、`upload`、`deployment`、`launch`、`monitor`、`manifest`、
`archive` 和 `verify_retrieval`；每步只运行计划中锁定的 argv/stdin/hash。

## 证据边界

此卡和本地静态检查只证明包、身份和计划一致；不证明当前 Taobo 可连、GPU7 准入、收敛、
驻点或物理有效性。运行结果只回答该固定单状态数值诊断，不能支持轨迹、物理教师或泛化结论。
