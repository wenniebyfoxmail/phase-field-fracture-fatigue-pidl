# ≤60秒零更新诊断：梯度差异已定量定位

本次获直接人方授权的唯一诊断使用源码
`99cad0b32eb88fcae496785f8090286e8bdfe5ea`，Run
`pf_s04e011_wpair_grad_audit_20261018_v1`。Taobo GPUServer8/GPU5，
PyTorch2.7.0+cu126；GPU准入free24077MiB、无compute进程，allocator22GiB。
外部TERM55s+KILL5s，必带`--preflight-only`，原容差不变。
receipt中继承的200步及3600/1800秒属于未进入训练的旧schema字段；本次有效授权与实际调用均为0更新、最多60秒。
UTC20:33:41至20:33:45约4秒后按原检查退出（exit1），未触及超时。
worker PID3661724、wrapper PID3661704；W0/W25目录与训练complete.json均不存在。

**目的已完成：量级和位置已查清；原逐项检查仍不通过，根因尚未确认。**
优化更新、history提交、新FEM均0；没有再次GPU调用或两臂训练。

## 比较的两个梯度

同一C原点、U=.02999988、beta1：

- `expected`：分别反传Eel/Ed/Eh/R，再在参数空间按log链式法则加权相加。
- `direct`：对完整`log10(Eel+Ed+Eh)+1e-5 R`直接反传。
- 原检查：逐分量`abs(expected-direct) <= 1e-6+1e-4*abs(direct)`，没有放宽。

Eh=0，保存的原始Eh参数梯度全部0。本次在beta1检查处记录并停止，
不能声称后续beta25、扰动检查或两臂训练已完成。

## 定量结果

| 读数 | 结果 |
|---|---:|
| 参数标量总数 | 1,125,211 |
| 原逐项容差越界数 | 9（约0.000800%） |
| 整体差异L2 / direct梯度L2 | 1.069986724e-6 |
| 差异L2 | .002558257108 |
| direct梯度L2 | 2390.924158 |
| 最大绝对差 | .0002002716064 |
| 最严重逐项容差比 | 2.531779289 |

**实际触发检查的9项**全部位于`hidden_layers.0/1/2/3.weight`，分别1/2/2/4项。
所有索引从0起；完整9项数值在
`loss_weight_no_step_audit_20261018_violations.csv`。

最严重越界位置：`hidden_layers.3.weight[1,386]`，expected=-.001491116709、
direct=-.001494026743，绝对差2.910033800e-6；该点原允许差1.149402692e-6，
因此是原容差的2.531779倍。

最大绝对差位置则为`hidden_layers.1.weight[112,95]`（global flat206495，
tensor-local flat44895）：expected=-23.80826187、direct=-23.80846214，
绝对差2.002716064e-4，但该点允许差.002381846076、比值.0840825，
**本身不越界**。不能用它代替实际触发检查的位置。

## 离线复算与解释边界

CPU分析源码`26c0da659391d2e9972fb1281e8e672fc6f3c52c`，只加载已经保存的
6组CPU梯度向量和network state_dict作布局映射，无NN forward、优化器或GPU。
原9项数量、最大绝对差、L2及索引均与producer记录一致。

将保存的float32分项梯度仅在末端改用double重算，仍有9项越界；对direct的
Linf约.0002031646212、L2约.002599515829。该描述性对照也重算了log系数并改变
末端算术顺序，**不是NN/能量双精度重放，不能确认整个差异只来自舍入**。
它也没有提供独立参考梯度来判断哪一条反传路径更准。

允许结论：整体相对差很小，但少数小梯度分量违反原逐项标准；量级和位置已知。
禁止结论：自动放宽容差、认定代码无误/根因解决、宣称gamma×25有效或无效。
训练与FEM场距离问题继续inconclusive，两臂启动仍关闭。

## 数据、图和独立复核

本地Run目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_grad_audit_20261018_v1/`。
已核验取回`retrieved/`日志、receipt/failure JSON、实际RPROP实现、退出码/起止时间；
`cpu_analysis/`含summary及全参数/9项CSV。保存向量27,008,473bytes和初始bundle
6,333,769bytes仍保留远端`/mnt/data2/drtao/pidl_archives/<Run>/readout/`，不声称全量取回。

阅读图：`analysis/gradient_discrepancy.png`（及同目录README_analysis.md/sidecar）。
左侧显示全部26个参数tensor的最大原容差比，右侧列全部9个真正越界点；
不是均值/抽样，也不是训练前后场比较。

独立Codex不仅审阅本地JSON/CSV，还通过只读SSH、隐藏CUDA设备，在CPU直接加载
远端原始向量和bundle独立复算；上述数量、位置、范数及double末端对照全部确认。
复核未使用GPU、NN forward、optimizer，也未修改远端文件或重新执行producer。

下一步如继续，应单列算术/反传路径核验来区分浮点计算顺序与实现问题；
本轮不扩展该诊断、不改容差、不自动转入训练。原权重实验判据与旧结果保留。
