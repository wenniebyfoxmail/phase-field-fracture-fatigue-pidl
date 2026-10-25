# S04-E011 FN776-r6：无自用资源上限的唯一科学 Run 卡

## 身份与授权链

| 项目 | 精确值 |
|---|---|
| Card | `S04-E011-UVH-C1-FN776-CARD-r6` |
| 批准索引 | `S04-E011-FN776-r6-A1` |
| 新 Run | `pf_s04e011_uvh_c1_fn776_r6_20261025` |
| Dev | `82776a75e844f033872fa4e820209e3b98a4d8ff` |
| Producer | `edd930b55fe64ac178bdf14c1c0e146e346d80e4` |
| controller blob | `1fc1ab2d4e1a6cc29e771007cbffb7c0fd671f18` |
| plan SHA-256 | `4d9f69fd1d05873d8dbf65486086018fdf3515781168c27507421b98e3c228ff` |
| Bundle | `198028` bytes / `3be19e6d16b30ae97d64615b72b5acfd34a5e7a1b6b1150f8bfa4f93c78d5135` |
| GPU | Taobo 物理 GPU7，`GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81` |

r4 在本机解析错误的线程重复检查收据时停止，发生在 SSH 子进程创建之前；没有远端 shell、GPU 检查、路径创建、部署、五文件读取或数值计算。r5 没有创建 Run；其静态复审发现仍保留与你随后明确取消的自用资源上限。两份既有终态和材料保持不变。r6 是新的、独立可审计的技术控制面身份。

## 固定科学范围

完整 776 维平方根 Newton、c1s4 `U=.11999988`、固定 388 基底、五个输入的完整 hash 与受限解码、16 外步、每步最多 32 个 Armijo trial、最多 3 次线性细化、25424 单位工作账本、阈值、种子和最终双读回均保持不变。`25424` 是算法调用核算，不是资源配额。

本卡明确**没有自用** wall-time、RSS、CUDA 或输出大小上限：worker 不设置每进程 CUDA 配额，guard 不会因这些遥测值终止，控制器、打包和取回也没有输出尺寸上限。SSH/远端查询的短超时只约束该次 transport/control client，绝不限制已派发的 solver。

GPU7 UUID、固定服务身份和服务显存范围、12GiB 初始/4GiB 运行可用显存、16GiB 宿主可用内存以及 data2 5GiB 共享空闲空间仍为共享机器安全条件。发生漂移时只终止本次已经核验归属的 child，绝不停止、重启或调整任何其他进程。

## 执行边界

执行序列是 `local_package`、新鲜重复检查、只读预检、上传、部署、唯一 `launch`、只读 `monitor`、终态后的 manifest/archive 和本地 hash/size 验证。一次 guard/numerical solve 是唯一科学尝试；任何未知 launch 只读观察、绝不重发。任何输入身份、数值、Armijo、驻点或其他科学性问题停止并与研究负责人讨论。技术性终态可在保留证据、核对远端实际状态并使用新的身份后重新准备，不能复用旧 root/archive。

```bash
FN776_R6_CTRL='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_r6_20261025/package_82776a75/materialized/code/tools/s04_e011_fn776/control_r2.py'
FN776_R6_PLAN='/Users/wenxiaofang/phase-field-fracture-with-pidl/_isolated_worktrees/s04-e011-fn776-r6-unbounded-20261025/docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/execution_plan_fn776_r6.json'
python3 -B "$FN776_R6_CTRL" --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r6 --approval-index S04-E011-FN776-r6-A1 --plan "$FN776_R6_PLAN" --plan-sha256 4d9f69fd1d05873d8dbf65486086018fdf3515781168c27507421b98e3c228ff --step local_package
```

后续严格按 [执行计划](execution_plan_fn776_r6.json) 中的锁定 argv/stdin/hash 依次调用 `preflight`、`upload`、`deployment`、`launch`、`monitor`、`manifest`、`archive` 和 `verify_retrieval`。

## 已验证与未验证边界

已完成：源码静审、代码包 root-commit/完整 fsck/51 文件和 22 模块闭包验证；没有 SSH、科学数组读取或数值调用。未验证：当前 Taobo 可达性、GPU7 准入、五文件读取、收敛、驻点或物理有效性。该 Run 仅回答固定单状态数值诊断，不能外推到轨迹、教师、物理或泛化结论。
