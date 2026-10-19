# E034 确切运行卡（准备包；尚未授权执行）

协议 `S04-E034/v1-finite-raw-reaction-F8-F802-20261019`。完整契约见 [experiment.md](experiment.md)，原设计见 [E033后续双臂方案](../S04-E033/finite_reaction_comparison_plan_20261019.md)。目标、原十一保护、冻结球/锥、双端反力、预算及首停规则均保持。

本轮只做代码、合成检查和独立审查；execution grant模板为false，approved_commit和人方执行批准引用为空。没有资源预检、GPU预留、远程传送、真实权重/模型加载或启动。Code Ready不等于Run Ready。

## 固定执行内容

1. 新独立checkout必须无hardlinks/alternates，clean exact批准源版本；原默认训练代码不动。运行入口自己拒绝Mac、旧grant、错commit和错协议。
2. 未来先重新核验GPU5 exact UUID与实时free/SM/apps，host RAM和 `/ /mnt/data2 /mnt/data3`；不满足即首停，不留下可自动重试授权。
3. 只读核对锁定输入；加载原S1500，在E032 head和外置physical d上零步复放。固定八轴和原11全头梯度身份/投影复放；新13实际Jac做两空间嵌入核验，均计入共享480秒。
4. F8和F802各唯一SLSQP，独立零起点，60主迭代/120不同点/600秒，无额度转移。首实际目标经实际NN复核即固定。未达留精确E032；异常停整个包。
5. 按已锁定条件最多一次投影见证复放。输出/图/sidecar/checkpoint/hash/receipt和规范目录归档，交HQ统一评估，不自动续跑。

未来grant由 `grant.template.json` 复制到fresh run，填写确切源commit、独立审查引用、人方明确执行批准引用和唯一fresh run ID，并置execution_authorized=true。它们只能在HQ确认确切包后填写，不从当前准备授权推导。

未来唯一命令形状（**本轮不执行**）：

```text
<producer-python> SENS_tensile/launch_s04_e034.py --execute --grant <exact-approved-grant.json>
```

启动入口创建fresh根目录一次性标记，GPU固定5，cache/tmp均在该根；GNU timeout1790s TERM+5s KILL。应通过任务自有detached session运行，留PID/cwd/argv/log及outer_receipt，断线只读核验，不重新提交。worker独立phase watchdog也限制共享480s及每臂600s。禁止换卡、换权重、改solver/目标/阈值、补跑或干扰共享进程。

资源：新增<=0.5 GPUh，累计最坏1.608339654581623<2；RAM32GiB、输出2GiB；GPU5 UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`，启动时空闲>=20GiB/SM0/无计算app，持续1GiB余量。没有实测当前资源或求解耗时，不能预报60次/802维可在600s完成。

精确源版本、检查回执、独立审查与本地包hash将在 `preparation_receipt.json` 和 `independent_review.md` 指向，不用未实现的占位承诺授予运行权限。

完整结束必须同时看到 `completion.json` 与manifest SHA匹配、无watchdog停止、outer returncode=0。计算结束只标为待最终化；hash/manifest/归档/最终guard/关闭异常都会标记停止、保留原异常，并去掉完成标记。不能单看中途receipt推断完成。SHA使用with管理的流式实现，不要求Python3.11的file_digest。
