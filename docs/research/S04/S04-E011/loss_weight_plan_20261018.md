# 单因素 loss 权重准备：不可逆罚 ×25（2026-10-18）

状态：准备与审查，训练预算 **0**；无 producer 命令、训练 runner 或新增 FEM。
本任务独立于主对话正在执行的 A/B/C，各 200 更新、总计≤1 GPU小时的授权。
不修改、占用或复制该预算，不修改主对话工作树。

本地分支 `codex/pidl-loss-weight-prep-20261018`；base 为远端已保存的
`6274a696b0bef8b72a169c803ad06d311822e16a`。
主 owner 是 S04-E011 的后续早期状态诊断准备；本卡不改旧实验判据或旧结果，
也不注册为已执行 Run。范围只有本计划、JSON 卡和零训练审查脚本/紧凑结果。
禁止改 production loss、初始化映射或 A/B/C runner。

## 实际损失、量纲与梯度

代码依据：`source/compute_energy.py` 的 native-Q4 分支、
`source/fit.py` 的 `fit`/`fit_with_early_stopping`、
`source/pff_model.py::irrPenalty`、`source/material_properties.py`、
`tools/run_physical_symmetry_pilot.py`。不用文件顶部历史注释推定当前算法。

令 Q4 物理 Jacobian 权为 wq、N 为形状函数，d_q=N d、h_q=N h：

```
Eel = sum_q wq [((1-d_q)^2+eta) psi_plus + psi_minus]
Ed  = sum_q wq f_q (w1/(8/3)) [d_q + ell^2 |grad_Q4 d|^2]
Eh  = .5*w1*16875 sum_q wq ReLU(h_q-d_q)^2
R   = sum_(name contains 'weight') ||theta_name||^2
S_beta = Eel + Ed + beta Eh
L_beta = log10(S_beta) + 1e-5 R
```

采用启用的 `fem_gp_q4`，不是历史 element-mean 罚项。面积仅计一次；
当前/历史均在同一 GP4 插值；无抽样、空间 reweight 或 mask。
`w1=Gc/ell=1`、`ell=.01`、`E=1` 为此处归一化数值；三项均为同一
归一化能量。log 的数值隐含同一固定参考能量尺度，不解释成有量纲能量
的绝对对数。R 是参数空间正则，与场能量不同，系数依赖参数化，不能用
原始标量大小断言哪个梯度主导。AT1 的线性 d 与 soft tails 允许负值，
不暗中 clip、加 epsilon 或更改 box；S 非正或非有限则停止。

```
grad_theta L_beta =
 (grad Eel + grad Ed + beta grad Eh)/(ln(10)*S_beta) + 1e-5 grad R
gamma(tol) = 27/(64*tol^2)
gamma(.005)=16875; gamma(.001)=421875 = 25*16875
```

beta25 是缩小数值不可逆容差的有依据候选，不是已验证最优值，也不是保证
回退≤.001。固定参数与原生积分下，`hist_loss_weight=25` 与仅将
`tol_ir` 从 .005 改为 .001 的能量/梯度应等价；未来只实现前者，
保持 `PFFModel tol=.005`，**不得两处一起改导致625倍**。

log 分母会缩放所有物理分项对参数的贡献，也改变它们与 log 外 R 的相对作用；
NN 各通道共享隐藏参数，因此 Eh 也可间接改变 u/v。若暂把物理 nodal u/v
视为独立自由度，Eh 对它们的直接导数为零，但分母仍改变它们的 log 梯度。
不能把 beta 的效应解释成只动 d、或完全隔离于正则的纯不可逆作用。

RPROP 依赖各参数梯度符号及历次符号所形成的步长状态；正比例放大梯度
不自动放大更新。不得把梯度范数配平当成步幅配平或 FEM 逼近证明。
同倍能量放入 log 仅加常数；同倍 log 外缩放在存在 R 时才改变相对梯度。
Eel/Ed 相对权重则改变等效 Gc/E（ell固定），不作为同一物理模型的中性调权。
FEM 监督可另成明确的拟合路线，本次不加入；持续拉回 d0 的 loss 会抑制
正常演化，也不加入。对称系数固定0。

## 最小具体测试卡（尚未获执行预算）

问题：固定 C 初始化/历史/表示和 200 更新预算后，较强不可逆罚是否减少
该 c1s1 状态对既有 FEM u/v/d 的联合距离？
类别：synthetic development，C1/C2 早期方法诊断；评价单元只有这一加载块，
节点、GP、额外 checkpoints 不是独立样本。不是转移/预测/收敛或物理验证。
FEM 角色是已有同状态数值比较对象，原 E011 的资格限制继续有效。

| 臂 | beta / effective gamma | 初始化、硬线、history | 其余 loss |
|---|---|---|---|
| W0 | 1 / 16875 | 固定 C | lambda_R=1e-5，sym=0，监督=0 |
| W25 | 25 / 421875 | 与 W0 完全相同 | 与 W0 完全相同 |

只作 W25−W0 配对。采用 C **不依据主对话训练结果择优挑 A/B/C**，而是固定
已有 FEM 零载场以去除可避免的初态不一致。两臂均从原 post-U0 theta_R
独立启动，原 8×400 TrainableReLU、seed1、完整节点 float32、eval/no-autocast；
目标 U=.02999988。永久线 d=1 的251节点；自由节点用已有 anchored map，
固定 d0/rR/坐标/mask buffers，完整保存与恢复，绝不在训练后重锚。
初始 hist_alpha=d0；H、hist_fat、q_prev全0，f_committed=1；当前 g(d)
随 d 变化。history commits=0。native-Q4 86756节点/86408单元/GP4。

固定 E=1、nu=.3、Gc=.01、ell=.01、w1=1、AT1/Amor、eta=0、alpha_T=.5、p=2。
同一原 u/v 边界映射，关闭所有额外 enrichments/priors/patches。
空间梯度与能量来自映射后的 Q4 节点，不能对 raw NN 坐标导数替代。
FEM 的 trial-f/staggered 与 PIDL committed-f/joint、可行域差异仍存在；
gamma 数值相等不意味着两算法/完整方程一致。

每臂 fresh RPROP lr1e-5，etas(.5,1.2)，step_sizes(1e-10,50)，恰200更新；
不改优化器、不启用 early stop、不挑 best-FEM checkpoint。
新预算提案两臂合计≤3600 GPU秒，包括输入前向、所有梯度审查、保存/读出；
未来需独立明确分配与版本授权。当前0GPU秒授权，不 SSH、不发 producer。
原则上独立配对；只有能证明主对话 C 的精确代码/runner/device、输入/anchor、
fresh optimizer、状态和端点读出完全相同，才能提出复用 W0 的新收据，
不能直接拿 C 标量替代本卡的控制，更不能再次消耗它的旧预算。

### 执行前只读检查（不是新增训练臂）

1. 未来 runner 独立审查绑定精确 commit、输入与本卡版本；复用已审主对话
   实现需要声明依赖、检查差异，不能从活动工作树随手拷贝。这里不实现 runner。
2. 在真实 device/dtype/full forward 的 theta_R 建一次 anchor，验证 W0/W25
   的 update0 输出、hist和buffer相同且 C=d0；全量导出初态后才可更新。
3. 原生小Q4非零回退测试验证 beta25 与 tol=.001 单独改动等价、无双重×25；
   验证不回退时 Eh及梯度均0，零点使用实际 ReLU平方导数。
4. NN 参数梯度诊断不得用下表的 nodal 梯度冒充：同一个参数快照上算两种 beta
   的总 grad，固定 readout k=0,1,200（端点只读、无额外更新），分项 norm/cosine、
   sign-flip/zero和nearzero比例，另报 RPROP 步长状态。nearzero阈值必须在执行卡
   固定，不能看结果改；未实现/未审不得称 producer-ready。

## 已完成的零训练检查及边界

脚本 `tools/audit_loss_weight_semantics.py`，CPU静态，无optimizer实例/循环，
只读原U0模型、checkpoint与FEM U0输入；未打开加载后的FEM目标。
本节是系数/链式法则检查，不是训练后场拟合或NN可表示能力结果。
原始输出在 parent `local_archive/experiments/S04-E011/loss_weight_preparation_20261018/static_v1/`，
紧凑 JSON 见 `runs/loss_weight_static_20261018.json`。

| 固定场 | beta | base Eh | weighted Eh | nodal grad log(S) L2 |
|---|---:|---:|---:|---:|
| C update0，d=h=d0 | 1 | 0 | 0 | .97804110 |
| 同一C update0 | 25 | 0 | 0 | .97804110 |
| 预设自由节点 d=d0−1e-4 d0，线仍1 | 1 | 2.36744384e-7 | 2.36744384e-7 | .97800886 |
| 同一预设场 | 25 | 2.36744384e-7 | 5.91860953e-6 | 1.03041769 |

初始 Eel=.00060008530、Ed=.00505913002；R=2672.091629，
1e-5R=.0267209163，单独正则参数梯度L2=.00103384556。
未计算完整 NN 物理参数梯度，不把该数与 nodal norm 比较。
log链式公式实际全场L∞差≤2.84e-8；小标量整体能量×25的梯度差2.22e-16。
预设回退场未必在现有NN表示中可达，不把它当作一次优化步或训练趋势。
本次静态系数审计不比较方法预测，决策表即最小可视摘要；未来加载结果必须
画实际评分场图。optimizer updates=0，history commits=0，FEM solves=0。

C初始 Eh与梯度均0意味着两臂初始总梯度相同。不能用初始Eh梯度做比例配平，
也不能从零初态断言整个块都无作用；首次出现回退时才可能分化。

## 离线评分、停止与后续决策

FEM c1s1只在两臂输出封存后评分，禁入损失、梯度、初始化、buffers与终点选择。
FEM U0已被用于C，是明确已知的初始信息；不宣称整个FEM都未用于建模。
锁定同一有序原生网格、状态/载荷/历史时序与reference路径后，使用已有评分：

`Jfield = sqrt(sum_i m_i[(du_i/.12)^2+(dv_i/.12)^2+(dd_i)^2]/(3 sum_i m_i))`

m为正Q4 lumped节点质量；固定三通道尺度与等权。主要读数
`DeltaJ=J_W25(update200)-J_W0(update200)`，同时报两臂update0和各自变化。
这是沿用的透明探索约定，不是物理容差，不新增正式通过阈值。
报告数值符号/大小，单seed单块不作显著性或普适因果结论；微小差异保留不确定。
端点缺失、预算未跑满200、有效性破坏则此端点对照 inconclusive/inadmissible，
保留实际更新数/有效前缀，不加步数补齐。若确定性重复性底噪尚未知，不宣称小差
足以选择更好模型，不临时加seed。

必要解释包括各u/v/d贡献、自由/硬线damage、固定前区x[0,.08],|y|≤.04、
x=-.25/0/.01/.02剖面、GP4 raw/active相对L2（零参考范数改报绝对值并标未定义）、
独立节点/GP回退与box、free-u残差、耗时。均为诊断，不投票救主读数。
不得clip、裁tails、移动ROI、以镜像残差/罚能/训练loss替代FEM场距离。
输出FEM/W0/W25的同状态u/v/d及有符号误差、共同色标、评分表与README_analysis。

日志保存base和weighted Eh、S1与Sbeta、R与加权R、实际优化L、首步能量跳升、
max物理能量、每步耗时和更新数。两臂优化loss不是同一目标，不能横向比其大小
判优；同时计算两个目标只是只读诊断，不挑checkpoint。

任何非有限、非正S、初态/节点次序/线/输入/history/buffer违约即停止；
每臂200或新总预算cap先到即停。无自动重试、加臂、加步数、改seed/优化器、
新FEM、c1s2、卸载或完整轨迹。训练runner与其版本授权均不在当前完成范围。

| 观察 | 允许结论 | 下一步 |
|---|---|---|
| DeltaJ<0且差异可分辨 | 本块/本预算/此C条件下更接近数值FEM | 决定是否另批独立状态验证 |
| 回退减少但J不改善 | 更强数值约束有效，场逼近未改善 | 保留负结果，按分项找首个瓶颈 |
| 几乎无回退、两臂等同 | 该块缺少gamma作用支持 | 停此杆；若有依据另卡测正则，不自动开跑 |
| 变差/抖动或cap前停止 | 保留结果/预算受限，不称收敛 | 不续跑；审查优化与物理场分项 |

审查收据后附；设计可审不等于 Code Ready、Run Ready 或执行授权。
