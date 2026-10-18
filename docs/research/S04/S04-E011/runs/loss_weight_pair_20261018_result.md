# W0/W25：GPU 零更新预检停止（2026-10-18）

**执行失败于预检；权重效果不可判定。没有开始 W0/W25 优化。**

Run `pf_s04e011_wpair_20261018T121457Z`，执行源码
`03a8f32093a96a47b0a3f31ea98b361a8b21a6d0`，Taobo `GPUServer8` GPU5，
PyTorch2.7.0+cu126。wrapper PID2839798、worker PID2839806，已退出；
资源准入时GPU5无compute进程、free24077MiB。22GiB allocator、
per-arm1800s/global3500s/internal及外部3590s watchdog均保留。

唯一 worker 命令：

```
/usr/bin/python3 -u tools/run_loss_weight_pair.py --recipe /mnt/data2/drtao/wennie/pf_s04e011_wpair_20261018T121457Z/recipe.json --out /mnt/data2/drtao/pidl_archives/pf_s04e011_wpair_20261018T121457Z/readout
```

wrapper UTC12:26:05启动；worker receipt UTC12:26:07.795321；
failure文件秒级时间12:26:08（不当作精确elapsed）。日志为：
`RuntimeError: fullNN gradient decomposition mismatch`，出现在原点
`preflight_origin_gradients.json` 的第一次完整NN分项/总梯度检查。
该版本在异常前没有保存误差量级或参数位置，因此**根因尚未识别**。

| 阶段 | 实际状态 |
|---|---|
| 精确源码、初始输入、GPU资源准入 | 已核验 |
| C full-forward、FEM d0、u/v兼容及bundle重载 | 调用顺序已越过对应断言，初始bundle已保存 |
| 完整NN梯度分解检查 | 不一致，立即停止，误差量级未保存 |
| 两beta完整初始梯度一致性、参数扰动及恢复 | 后续检查未完成，不声称通过 |
| W0/W25优化、history提交、新FEM | 全部0 |
| update200配对、FEM J与u/v/d场误差 | 无端点，不可计算 |

W0/W25目录及complete.json均不存在；worker与wrapper均已退出，GPU5回到
4MiB/0%状态。没有自动重试、换卡、加步或放宽阈值。此次不能称W25负结果，
也不能据loss或对称性作结论。原A/B/C与其他实验结果不变。

## 已保存的证据与取回状态

本地Run：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_20261018T121457Z/`。
已取回`failed_preflight.log`、`retrieved/receipt.json`、
`terminal_failure.json`与实际`Rprop_implementation.txt`；compact receipts verified。
remote初始`readout/initial_bundle.pt`6333769bytes保留，不声称全量取回。
没有可支持的训练前后场图；不把静态相同初态图冒充权重训练结果。

网络/初始history远端原档与本地副本的已有数据身份已核对，fresh目录内复制；
源代码传输从未完成的完整仓库包换成同一commit的138KiB运行依赖子集。
部分上传文件保留未使用。以上传输调整不是producer重试，worker只调用一次。

## 具体修复：先记录，不放宽

现有检查比较：分项参数梯度加权相加，与直接反传完整loss。
数学链式法则一致，但float32反传的运算/归约顺序可能不同；这只是一个
待查候选，不能从错误字符串认定是浮点误差，也不能排除实现问题。

已准备task-owned记录补丁，保持`allclose(atol=1e-6,rtol=1e-4)`原检查与停止：
失败前保存beta、能量、Linf/L2/relativeL2、超容差分量数、最大差对应参数及
原始分项/expected/direct向量。新增`--preflight-only`在所有无步检查后返回，
不允许进入训练循环；4项CPU测试通过，含故意损坏梯度时保留失败与诊断。
本补丁尚未在producer执行，不倒填本次丢失数值。

下一项建议是**一次≤60s、零optimizer step的独立诊断**，仅回答差异量级、
位置和计算路径。保留原检查，先审实际数据再判断修复；不得以调宽容差
代替原因识别。该建议不是自动重试许可，本轮不启动第二次producer。
原两臂各200的科学问题、初态与主指标继续冻结，DeltaJ200保持inconclusive。

Storyline S04/E011：本次只定位到数值预检这一工程瓶颈，不支持或否定gamma×25
的FEM场逼近效应；研究处置为先诊断修复，未扩展科学主张。
