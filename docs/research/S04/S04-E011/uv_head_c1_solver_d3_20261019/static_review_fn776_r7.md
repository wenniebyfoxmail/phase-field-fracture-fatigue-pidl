# FN776-r7 静态复审

**结论：通过静态复审；允许进入 r7 的卡内本地包验证和实时只读预检。**这不是 GPU 实时准入、五文件读取、数值收敛、驻点或物理结论。

## 复审范围与绑定

- Dev：`5f6349a1f67ad4a38089304f6ed26b73211c94c4`
- Producer：`ee6a57bce69c1c1dc6db315b24c8e307f3e9f111`
- bundle：`199364` bytes，SHA-256 `7acc09d2915bf7eaa88a15ad7c2c0b13d03dcf0cdfd58a4db790f943be718922`
- 计划：[`execution_plan_fn776_r7.json`](execution_plan_fn776_r7.json)，SHA-256 `b94573cddae18c1ba1076d348220c72934cc97d06a87f2d52080d9566052edb9`

`DIFF_STATIC_PASS` 确认五文件身份、c1s4、776 维/388 基底、16×32×3 算法范围和 `25424` 工作账本与冻结合同一致；worker blob 为 `9e02f72ef309304ad86018cf78c7a7fb43568daa`，square-root blob 为 `0f485e08d39a55e4ee53f88d8e2652372a388a30`，两份 mechanics blobs 为 `6e34160207ba1ac75c9cbb51e6e688c60ee1c26b` 与 `64c0a815f5f875d5be93faa9e918714d0fb07ebf`。

r7 唯一实质资源差分是追加第三个精确 GPU7 服务：PID `651952`、start ticks `541746716`、UID `[0,0,0,0]`、cmdline SHA-256 `be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808`、cgroup SHA-256 `a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e`、基线 `5638 MiB`、上限 `6144 MiB`。原两服务、12GiB 初始/4GiB 运行余量、10% 准入利用率阈值、三次采样、16GiB 主机可用内存和 data2 5GiB 余量均未放宽。

guard 与远端 helper 的 `digest`、`service_identity`、`gpu_snapshot` AST 相同；嵌入远端合同与 r7 JSON 相等。没有自设 wall/RSS/CUDA/output 硬停；仍保留 GPU UUID、精确服务身份、空闲显存、主机内存和磁盘安全检查。代码没有针对常驻服务的终止、重启或变更路径。

代码包独立验证通过：51 个文件、root commit、完整 `git fsck`，且没有 sparse checkout、partial clone、alternates 或先决对象。计划绑定检查也通过，逐项验证 controller blob、Producer、bundle/stdin 的路径、长度和 SHA-256、r7 card/index/run，以及 9 个阶段的顺序；监控无调用次数上限。

以上检查均为 AST/文本/Git/代码包验证。没有 SSH、没有读取科学数组、没有数值导入或数值调用。实时预检仍必须重新核验远端路径、重复 worker、三次服务身份/显存/利用率样本及机器余量；如果任何值漂移，r7 安全停止且不改变其他进程。
