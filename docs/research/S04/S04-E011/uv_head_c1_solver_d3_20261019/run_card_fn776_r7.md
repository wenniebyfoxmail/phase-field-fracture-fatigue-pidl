# S04-E011 FN776-r7：GPU7 精确三服务准入的唯一科学 Run 卡

## 身份与授权链

| 项目 | 精确值 |
|---|---|
| Card | `S04-E011-UVH-C1-FN776-CARD-r7` |
| 批准索引 | `S04-E011-FN776-r7-A1` |
| 新 Run | `pf_s04e011_uvh_c1_fn776_r7_20261025` |
| Dev | `5f6349a1f67ad4a38089304f6ed26b73211c94c4` |
| Producer | `ee6a57bce69c1c1dc6db315b24c8e307f3e9f111` |
| controller blob | `66f65bad8bae4ad67ab4ed85f9ed27ea97b2056a` |
| plan SHA-256 | `b94573cddae18c1ba1076d348220c72934cc97d06a87f2d52080d9566052edb9` |
| Bundle | `199364` bytes / `7acc09d2915bf7eaa88a15ad7c2c0b13d03dcf0cdfd58a4db790f943be718922` |
| GPU | Taobo 物理 GPU7，`GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81` |

r6 已完成只读 Taobo 预检，但在确认 GPU7 上的 PID `651952` 不属于其冻结白名单后，于上传、部署、五文件读取或 solver 之前安全停止。r7 使用新的 Card、索引、Run、root、archive、代码包和控制收据；r6 的终态材料保持不变。

## 固定科学范围

完整 776 维平方根 Newton、c1s4 `U=.11999988`、固定 388 基底、五个输入的完整 hash 与受限解码、16 外步、每步最多 32 个 Armijo trial、最多 3 次线性细化、25424 单位工作账本、阈值、种子和最终双读回均保持不变。`25424` 是算法调用核算，不是资源配额。

本卡没有自用 wall-time、RSS、CUDA 或输出大小上限：worker 不设置每进程 CUDA 配额，guard 不会因这些遥测值终止，控制器、打包和取回也没有输出尺寸上限。SSH/远端查询的短超时只约束该次 transport/control client，绝不限制已派发的 solver。

GPU7 的常驻服务白名单为三个精确身份。新增服务为 PID `651952`，start ticks `541746716`，UID `[0,0,0,0]`，cmdline SHA-256 `be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808`，cgroup SHA-256 `a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e`。三次只读样本中它稳定占用 `5638 MiB`；r7 将其上限锁定为 `6144 MiB`。GPU UUID、三服务身份与显存范围、12GiB 初始/4GiB 运行可用显存、16GiB 宿主可用内存以及 data2 5GiB 共享空闲空间均为共享机器安全条件。身份、服务集合或余量漂移时只终止本次已经核验归属的 child，绝不停止、重启或调整任何其他进程。

## 执行边界

执行序列是 `local_package`、新鲜重复检查、只读预检、上传、部署、唯一 `launch`、只读 `monitor`、终态后的 manifest/archive 和本地 hash/size 验证。一次 guard/numerical solve 是唯一科学尝试；任何未知 launch 只读观察、绝不重发。任何输入身份、数值、Armijo、驻点或其他科学性问题停止并与研究负责人讨论。技术性终态只能在保留证据、核对远端实际状态并使用新的身份后重新准备，不能复用旧 root/archive。

```bash
FN776_R7_CTRL='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_r7_20261025/package_5f6349a1/materialized/code/tools/s04_e011_fn776/control_r2.py'
FN776_R7_PLAN='/Users/wenxiaofang/phase-field-fracture-with-pidl/_isolated_worktrees/s04-e011-fn776-r7-gpu7-uvicorn-20261025/docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/execution_plan_fn776_r7.json'
python3 -B "$FN776_R7_CTRL" --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r7 --approval-index S04-E011-FN776-r7-A1 --plan "$FN776_R7_PLAN" --plan-sha256 b94573cddae18c1ba1076d348220c72934cc97d06a87f2d52080d9566052edb9 --step local_package
```

后续严格按 [执行计划](execution_plan_fn776_r7.json) 中的锁定 argv/stdin/hash 依次调用 `preflight`、`upload`、`deployment`、`launch`、`monitor`、`manifest`、`archive` 和 `verify_retrieval`。

## 已验证与未验证边界

已完成：源码静审、代码包 root-commit/完整 fsck/51 文件和 22 模块闭包验证；新增服务仅经三次只读身份/资源采样核验；没有读取科学数组或发起数值调用。未验证：r7 的实时 Taobo 准入、五文件读取、收敛、驻点或物理有效性。该 Run 仅回答固定单状态数值诊断，不能外推到轨迹、教师、物理或泛化结论。
