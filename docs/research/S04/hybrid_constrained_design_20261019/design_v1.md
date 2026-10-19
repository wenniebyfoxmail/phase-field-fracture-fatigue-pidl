# 受约束增量变分＋FEM—神经混合求解：完整设计 v1

日期：2026-10-19。Owner：本对话S04场一致性主线；当前D6=完整方法设计与独立复审。用户明确选择本路线，要求方案与复审，不训练、不新增FEM。本文件为概念/算法设计，不是已实现代码、运行卡或实测收益；旧E011/PC16/W0/W25/E032/E033结果及其判据不改。来源：沿用D1及四源报告，补查真实FEM/PIDL/QP源码。

## 1. 核心假设与成功的含义

**假设H**：把任意神经参数更新替换为“网络给受约束增量的好初值＋全自由度FEM/损伤数值校正”，可绕开神经切空间假驻点和软罚可行性缺口；经过多加载步复用后，若网络能减少昂贵的耦合迭代，才可能在同等场质量下比直接FEM节省总成本。

质量和加速是两个独立结论。数值校正使质量不必依赖NN输出已经精确；它不保证加速，也不保证非凸问题选择与旧FEM完全相同的分支。若校正量、外迭代、失败/回退开销与FEM相当，必须报告“学习初值/候选能力，未证明实际加速”。

主实现是**学习增量初值的受约束FEM求解器**：NN每个物理子步调用一次，预测下一接受态damage候选；机械位移与最终damage由完整空间的数值算子求解。网络不替代最终平衡/KKT审查，也不固定其预测的活跃集。

## 2. 三个比较对象，防止改变了问题却误称同方法

| 对象 | 数学/算法身份 | 在比较中的角色 |
|---|---|---|
| 历史PIDL（含C/W0） | 共享NN、log能量＋参数正则、GP有限不可逆罚、committed-f优化、既有状态更新 | 历史方法差距和计算开销；不伪装为同一受约束问题 |
| 历史GRIPHFiTH FEM | native Q4、GP recovery/irreversibility软罚、trial-fatigue及原staggered停止 | 已有数值参照；旧字段差照报，但不要求新硬约束解逐位复制其有限罚/未闭合端点 |
| **直接受约束FEM（强基线）** | 与新方法同mesh/能量/节点约束、trial状态map、完整残差/停止、求解后端；关闭NN，采用前态/经典外推初值 | 主质量及成本对照。用于隔离NN是否在同一问题上有附加价值 |

新主可行域明确选择**节点不可逆＋节点box＋原硬预裂纹线**：

\[
K_n=\{d\in\mathbb R^{N_d}:d^n_i\le d_i\le1,\quad d_i=1\ (i\in C_0)\}.
\]

这里lower是上一个接受子步的完整二维damage，不在内迭代滚动。它比“0≤节点d≤1且GP插值d≥GP前态”更强。原QP文件`source/native_q4_damage_qp.py:155–159`采用后者；原Fortran `at1_penalty_fatigue.f90:98–115`是GP软罚。**不能把任何一个原实现直接称为新K的已实现版本。** 新节点K是本设计的显式方法改变，不覆盖旧实验结论或偷换历史FEM参照。

对于有效Q4且N_i≥0、ΣN_i=1，节点K保证整个单元双线性d不低于插值前态，且0≤d≤1；几何取向/积分正性须通过已有契约。GP统计仍逐点保存，不靠裁剪掩盖违约。历史GP约束模式只用于既有结果复用，不在本设计中另开一个候选臂。

## 3. 空间、材料及离散能量

第一版保持Hard5已有模型家族：平面应变、AT1、Amor拉压分解、E=1、ν=.3、Gc=.01、ell=.01、残余刚度eta=0、Carrara alpha_T=.5、p=2，native Q4 86756节点/86408单元/2×2GP。目标不是再引入新的材料退化函数或对称项。精确dimensional/nondimensional系数由已有核统一适配，不能混用Gc/ell与w1标度。

在固定疲劳系数f的子问题上，用

\[
\Pi_h(u,d;f)=\sum_{e,g}w_{eg}\{g(d_{eg})\psi^+(\epsilon_{eg}(u))+\psi^-(\epsilon_{eg}(u))
+\tfrac{G_c f_{eg}}{c_w}(d_{eg}/\ell+\ell|\nabla d_{eg}|^2)\}-W_{ext}(u),
\quad g(d)=(1-d)^2,\ c_w=8/3.
\]

位移Dirichlet自由度消元，裂纹线damage自由度固定1。外力势按真实加载合同保留，即使当前位移控制/无体力使部分项为0。新物理校正目标不加参数正则、对称loss或FEM场MSE，也不保留同一不可逆性的有限罚作为额外物理项。训练期正则只影响NN候选，不修改数值校正目标。

- 固定d的机械块：求`R_u=∂_uΠ_h=0`，使用同Amor离散残差及一致切线，而不是把网络u输出当最终位移。
- 固定u和f的damage块：AT1给凸二次形式`φ(d)=.5 dᵀH_d d+bᵀd+c`，在完整节点K上求解。H_d半正定，不凭空假定严格正定/唯一解；全裂纹/退化区可出现零模。
- 整体u/d耦合仍非凸。疲劳系数由当前trial场更新时，完整迭代是**固定f的局部变分问题＋疲劳演化固定点**，不是把f(u,d)直接代入Π后对所有链式项自动微分的全局极小化。

## 4. 网络、FEM与状态管理器的职责

| 组件 | 负责 | 不承担/不允许 |
|---|---|---|
| 冻结参数NN预测器 | 从上一接受态、目标载荷及其力学预测特征，给下一态d的可行初值/初始活跃集提示 | 不给最终u；不独立预测f/疲劳history/raw/active；不决定accept/commit |
| 机械FEM块 | 全机械自由度平衡、边界反力、strain/raw的统一GP重构；返回fresh残差 | 不沿用damage变更前的Kuu/force作最终证书 |
| 受约束damage数值块 | 完整K上的主动集/投影Newton/QP校正，能释放任何NN活跃集 | 不限制在NN切空间或其预测裂纹带；不将后clamp当成已解KKT |
| 疲劳纯函数 | 由固定accepted状态和当前u/d重建trial driver/累积量/f | 不按solver调用次数累计、不把inner history传给下一inner |
| 事务控制器 | fresh联合审查、状态版本、保存、一次提交、失败回滚 | 不用新lower/history的“后验通过”救旧态miss，不做部分提交 |

网络的加速角色是改变**耦合问题的起点**，不是每个节点每步再做RPROP。若只把NN用作已精确求解的固定u/f凸QP内部warm start，唯一解条件下它原则上只减少子块工作，不能据此宣称减少外层耦合迭代。本版因此预测整个下一接受damage态作初值，后续完整校正；可能改变非凸分支，必须在评价中明确检查。

## 5. 网络输入、输出、架构与训练定义

### 5.1 输入和输出

accepted状态：`S_n=(u_n,d_n,A_n,r_n,f_n,opaque_native_channels,load_index,version)`。
A为GP疲劳累积量，r为上一接受态active driver；f由A派生并保存供一致性审计。原native channel1未由AT1 penalty模块定义/使用，保留opaque而不命名为最大拉伸历史H。

先从d_n在新载荷解一个机械预测场u_pred（与强FEM基线同样的预测成本）。NN输入包含：

- 节点坐标/局部长度与网格连接、边界及预裂纹mask、d_n、u_n和u_pred；
- 从nativeGP原样重建的ψ⁺(u_pred)、A_n、r_n、f_n、d_n梯度等特征；GP→节点仅是NN特征投影，物理算子仍用原GP，不把均值替代历史；
- 目标与前态载荷、Δload、加载/卸载分支、材料无量纲参数及ell/局部h。

不输入未来FEM场、事件时间或未来裂尖。测试时输入hybrid自己的已接受状态，不做FEM teacher forcing。

NN输出一个节点标量a_i，形成

\[
\widehat d_i=d^n_i+(1-d^n_i)\,\mathrm{clip}(a_i,0,1),\quad \widehat d|_{C_0}=1.
\]

此投影只确保**初值**可行，不证明d_hat是解。coincident bounds不作自由未知量。初值可以与后续inner解相互上下移动，只要始终≥d_n；不得把d_hat或inner d变成新的不可逆lower。非有限/形状/身份错误直接放弃该NN初值，使用强FEM基线的确定性初值，并计回退成本。

### 5.2 参考网络

采用原生网格条件化图预测器，而不先规则栅格化：细网格encoder，按ell尺度预计算的粗图聚合/回传，4个残差消息块、隐藏宽度64，单damage输出头。粗图只服务特征传播，最终场、积分及残差全部回到同一完整Q4网格。该结构和宽度是可实现的参考配置，不是已证明最优，也不启动架构扫描。固定图构建与GP特征投影记入setup；图覆盖半径、粗细映射和输入归一化都入模型清单。

NN可用float32推理；其输出转换为float64后进入物理校正。物理状态和最终残差float64。不能将网络浮点误差作为放宽物理可行性/残差的理由。在线每个子步一次推理，之后冻结θ，不在校正循环中优化网络权重或自训练。

### 5.3 离线训练（未来工作，不在本轮执行）

样本是一对连续接受态及其完整载荷/历史：输入上述`(S_n,load_{n+1},u_pred)`，标签是**同受约束问题、完整联合收敛**的直接FEM输出d_{n+1}。旧有限罚/未闭合FEM或PIDL endpoint不能自动充当该标签。

基础监督目标用物理尺度的damage误差：`||d_hat-d*||²_M + ell² ||∇(d_hat-d*)||²_GP`，各项用预先固定单位/归一化，强调场形状而非独立修正derived fields。训练标签仅用于训练划分；线上接受只看物理条件。训练集统计冻结；超参数和早停只用development/validation，按完整载荷/材料/轨迹分组留出测试，不能随机分节点或把相邻同轨迹子步当独立测试。

现有档案能否提供足量**新K与状态map相符**的连续合格标签尚未核查，本轮不读关闭数组或补解。若需新增标签，全部求解和存储成本计入离线成本；没有合格标签/训练模型时，默认NN-off直接求解，不把无模型占位符称为hybrid结果。

## 6. 疲劳trial及accepted更新——明确到每个变量

对任意当前trial `(u,d)`，都从不可变S_n重建：

\[
\psi^+_{eg}=\psi^+(\epsilon(u)),\quad r^*_{eg}=g(d_{eg})\psi^+_{eg},
\quad A^*_{eg}=A^n_{eg}+\max(0,r^*_{eg}-r^n_{eg}),
\]

\[
f^*_{eg}=F(A^*_{eg})=\begin{cases}1&A^*\le\alpha_T,\\ (2\alpha_T/(A^*+\alpha_T))^p&A^*>\alpha_T.\end{cases}
\]

这与当前Fortran模块有效2/3/4通道的driver/累积/f形式一致；eta=0。初态来自同一已恢复state0，A0=0/r0=0/f0=1需由初始化契约确认，而不是每次resume或每个cycle重置。

**每次trial都是`A_n + 当前正增量`，不是`A_inner + 当前正增量`。** 卸载时A可保持，r必须存当前接受态实际值，不能永久保存max r或用峰值代替。增量按已声明五子步载荷路径采样，不跨越加载/卸载拐点后只用两个端点算一次；自适应切步若未来启用须与基线相同且独立冻结。

在u/d子块求导时f固定。外层更新G并检查一致性；对f(u,d)做自动微分并引入df/dd或df/du是另一个算法/模型，不能悄悄加入。禁止把native未使用slot1、PIDL可选max tensile history及Carrara累积A混成同一个H。

## 7. 一个物理子步的完整算法

```text
Input: immutable accepted S_n, prescribed next load, frozen NN/model + graph identity
1. Copy S_n as immutable transaction preimage; lower=d_n; no accepted write.
2. Compute common FEM predictor u_pred at new load with d_n; fresh trial G(S_n,u_pred,d_n).
3. NN-on: one inference -> feasible d^0; NN-off strong baseline: declared classical d^0.
   Reject malformed/nonfinite NN candidate -> baseline initial state; record fallback.
4. For outer k:
   a. Solve mechanics with d^k; return fresh u^{k+1/2}, raw and force.
      Reuse only a cache whose mesh/load/d fingerprint matches exactly.
   b. Compute q^k=G(S_n,u^{k+1/2},d^k), f^k; freeze it for this damage block.
   c. Assemble fixed-u/f damage QP on full K_n; solve from current feasible d^k.
      Active set is releasable; global primal/dual/KKT checks cover every node.
   d. Re-equilibrate mechanics at returned d^{k+1}; obtain u^{k+1}.
   e. Recompute raw/r/A/f=G(S_n,u^{k+1},d^{k+1}) from preimage, not inner history.
   f. At this identical final u/d/q and OLD lower/history:
      fresh mechanics residual + fresh damage operator and KKT + q consistency,
      feasibility/BC/finite checks; compare block-f versus final f as fixed-point residual.
      An old certificate from step c is NOT a final certificate after d/e.
   g. Joint pass -> proposal for acceptance; otherwise continue using d/u candidate,
      reusing an already-converged mechanics result only under identical fingerprints.
5. Final pass: produce accepted proposal from final u/d and G(preimage,final u/d).
   Save old-state audit, proposal, identities, work counts and version n+1 atomically.
6. Only after durable transaction success assign S_{n+1}; move to next physical load.
```

damage变化后再求u可能使damage再次不满足KKT，因此step4f必需，不以“两个子问题先后各自收敛”代替联合收敛。现有`run_native_q4_direct_reference.py`中更新u/q后沿用旧QP certificate的模式不能复用为本方案最终证书。

NN-off强基线执行相同的4a–f、状态函数、联合标准及记录；差别仅初值来源，不能把严格hybrid与宽松/过早停止的FEM作速度比较。全空间数值校正不限制为网络预测“裂纹带”，非预测区必须能释放/增长。

## 8. 可接受条件与全局化

在同一final场和preimage上定义：

- `Ru_free`：原始自由节点机械force，报告L2/Linf，并报告以固定载荷/几何/材料尺度定义的无量纲量；不能用近零外力作分母。
- damage KKT：`g_d=H_d(u_final,f_final)d+b`；对自由节点在lower处g_d≥0、interior g_d=0、upper处g_d≤0；固定/重合界按固定DOF处理。另报primal违约、dual符号、互补和质量加权投影残差。
- 可用投影残差`p_d=d-Pi_K(d-tau M^{-1}g_d)`作可重现诊断；tau与M的尺度固定，完整KKT同时保存，不能单靠调tau使数值看起来小。
- fatigue fixed point：最后damage子块使用的f与final重建f之差及trial-map身份；不能用“我把q直接赋值G了”代替对最终damage算子的检查。
- 原边界/硬线、0≤d≤1、d≥d_n、nativeGP一致、history有限/单次版本提交。

本方案不把已有不同归一化残差的1e-8/4e-6等数字生搬成跨后端通用精度，也不放宽旧判据；具体阈值、尺度、迭代/时间上限需在未来可执行卡中依据同problem FEM精度/重复性固定。没有数值卡时本设计不具备自动开跑条件。到达cap只是未接受，不能拿最后一次trial当已接受态。

机械块用一致切线、阻尼/线搜索或能量信赖域；damage固定u/f块使用受约束全局化。固定f子问题可检查能量下降；f更新改变了子问题，不能据此宣称完整疲劳外循环能量单调。若Picard振荡/停滞，保存全状态并停止，不自动更换q导数、物理eta或放松K。

eta=0时须检查约束后的线性系统兼容性与零模。无唯一性时，只有能证明是物理等价gauge的消零模才可显式固定；否则报告退化并停止。不能静默加残余刚度、pin任意节点或用伪逆选择新物理分支。线性求解器的数值阻尼不改变最终原算子残差；阻尼大小与偏差均记录。

## 9. commit、rollback、restart

最终接受状态是`u_final,d_final,A_final,r_final,f_final,load/version`的**同一次**proposal；下一lower=d_final。保存原始通道、原生GP顺序、所有operator/model hashes与输入前态版本。raw/active/f都由该场统一重建，不由不同网络独立修正。

任意子块失败、最终联合miss、身份错误、非有限、写入失败：接受态S_n、load index、cycle/event counters、NN缓存/候选、线性/active-set缓存全部回到preimage；保存失败trial只作诊断。不得部分提交d而留下旧A，或先累积A再继续同一load试别的初值。

正常NN候选校正属于同一算法计费，不是“重新训练”；数值子步失败后的另一次baseline重解是**额外fallback工作**，本轮不自动触发。未来运行卡若允许该fallback，须从同一S_n重新开始、独立attempt标记、计入总cost，并在成功前不advance状态。restart只加载最后完整accepted transaction，不加载未审trial缓存；在线NN模型版本不随resume改变。

## 10. 相对现有PIDL的实质收益与损失

预期收益机制：u不再被NN切空间限制；d不再靠有限罚近似界；求解停止由field residual/KKT而非loss plateau决定；两场和疲劳state在同一final点一致。当前C/W0该状态J平方约96.12%来自u/v，说明机械场需要实质处理，但不能将这一比例当所有状态的固定结论。

这些是机制上的可期待改进，不是新实测准确率。hybrid不再是纯NN无网格求解；仍需完整FEM网格、稀疏求解和数值库；默认不通过整个主动集/commit过程端到端反传。若以后需要反演/灵敏度，需单独设计隐式微分与非光滑活跃集处理，不能把“用了NN”说成全流程天然可微。

## 11. 相对直接受约束FEM的收益来源与成本上限

同一数学问题/精度下，不声称hybrid比直接FEM更准确。它的附加价值只可能来自：

1. 下一态初值更接近正确局部分支，减少u/d/q耦合外迭代；
2. 初始活跃集更接近最终活跃集，减少damage线性解/因子分解；
3. 多条载荷/参数任务复用离线训练，摊薄数据与训练成本。

它不删除最终完整网格审查、不删除机械求解、不凭预测置信度跳过物理接受；若改动非凸分支，则“残差合格”仍不等于“更近既有FEM路径”。共同初态/加载离散和分支/能量/反力比较均须报告。

令每个子步直接FEM实测成本为`P`共同预测、`U`全部机械、`D`全部damage、`Q`trial状态、`A`fresh审查/IO，

\[
T_F=\sum_n(P_n+U_n^F+D_n^F+Q_n^F+A_n^F),
\]
\[
T_H^{online}=\sum_n(P_n+C_{feature,n}+C_{NN,n}+C_{transfer,n}
+U_n^H+D_n^H+Q_n^H+A_n^H+C_{fallback,n}),
\]
\[
T_H^{total}=T_{eligible\ labels}+T_{train}+T_{graph/setup}+T_H^{online}.
\]

setup中的可复用mesh/图结构与每次任务setup分开计；共同项也保留，不靠省略基线IO造加速。NN FLOPs、CPU/GPU时间、往返同步、完整矩阵装配、因子/解次数、失败trial、audit和fallback都计费。CPUh与GPUh分开给出，端到端wall time以相同硬件/并发边界测量；不能将一块GPU与任意CPU数对比后只报“训练很快”。

如果单任务NN-off成本为C_F、NN-on在线为C_H，离线成本C_0，则只有C_H<C_F才有摊销阈值`N > C_0/(C_F-C_H)`。若C_H≥C_F，任务再多也不能靠摊销训练获得加速。对单次求解必须同时给冷启动成本；模型反复使用时再给摊销成本，不以只报推理替代总成本。

若加速仅影响damage且它在baseline占比p，即使damage免费也有speedup≤1/(1-p)；例如假设p=.2、NN开销=.05 baseline、damage工作减半、其它不变，则在线时间=.95 baseline，只有1.053倍。这只是解析示例，**不是本项目实测比例或预测**。要获得更大收益，必须实际减少占主导的耦合机械工作，而不只是预测便宜的局部字段。

本轮没有profile，故不填入虚构速度/显存收益。显存/内存包括图特征、粗图、NN激活、稀疏矩阵和因子；稀疏factor fill-in可能主导内存。float32 NN与float64 FEM转换/传输可能抹平推理收益，须纳入模型选择，而非隐去。

## 12. 后续验证尺度：一次完整方法比较，而非逐开关研究主线

未来可执行方案应成套比较：历史PIDL（描述性）、历史FEM（描述性）、同问题直接受约束FEM（主基线）、同基线＋经典可行外推、同基线＋NN初值（候选）。NN-off与经典外推防止把“修好FEM停止/约束”或“任何warm start”收益归给学习。

覆盖需要完整加载—卸载与接受态自演化，并包含初期、稳定传播、明显f<1阶段、临界/分叉附近；按可用已存轨迹及其真实合格状态决定具体任务，不强制用一个c1状态代替疲劳方法判断。训练/验证/测试按整条载荷/材料轨迹分组。被关闭评估资料仍保持关闭，本轮不读取或启用。

评价：同state u/v/d主场误差与固定前区；全域/过程区raw与active、上边界反力与能量；nodal/GP feasibility、原始Ru与damage KKT；A/r/f演化、裂纹几何与事件（若完整路径具备）；冷启动/在线/摊销总cost。不能将raw下降而反力显著回退称为完整修复。非凸分支不一致单列，不能挑更接近FEM的best checkpoint或用参考场在线选解。

判定逻辑：
- 同problem质量/演化达到基线精度，且端到端成本更低：支持hybrid加速路线。
- 比PIDL质量明显好，但与强FEM同价/更贵：支持受约束物理校正，未证明NN附加价值；默认保留强FEM。
- NN-off也达不到联合条件：物理求解器/状态实现问题，不能靠训练修补接受标准。
- 训练case有效、整轨迹/参数留出失效或回退多：摊销与迁移主张不成立；不把同状态拟合包装成算子泛化。

未来实施可先并行准备operator接口、事务、网络及成本日志，不把研究切成必须逐个获准的微测试阶梯；工程检查针对具体风险。执行预算、数据身份、阈值和允许路径需在代码与资源明确后制定，本轮方案/复审不授权任何运行。

## 13. 实现接口、复用边界与产物

统一Python主控是参考工程选择：canonical float64 Q4数值状态＋稀疏求解后端，PyTorch仅NN推理/离线训练。原MATLAB/Fortran算子作为独立核对参照；不能把跨语言/硬件性能差归给NN。主速度基线NN-on/off必须同一后端/稀疏库/线程和停止标准。

建议接口：`mechanics_solve(d,load,state_id)->u,raw,Ru,tangent_id,work`；`trial_state(S_n,u,d)->A,r,f`纯函数；`damage_qp(u,f,lower,crack)->H,b,K`；`damage_solve(H,b,K,d_init)->d,local_certificate,work`；`audit_final(S_n,u,d)->fresh_joint_certificate`；`propose_commit`与`commit_if_version`分离。所有候选/solver调用和耗时入同一账本。

可复用：native Q4几何/积分及已验证GP顺序、AT1固定u/f装配、既有受约束phase/事务检查的数学与接口、原始场评分、现成classical predictors。必须补齐：节点lower和硬线进入QP完整K、正确最终fresh审查、统一trial固定点控制、零模/失败契约、NN输入图/离线标签及全成本账本。既有GP-QP或head模型不直接升级为新系统。

本次交付：本设计、静态合同检查清单、代价模型、独立设计复审收据和Obsidian方案摘要。无训练代码上线、无模型加载/新FEM/SSH/producer或新数值结果。

## 14. 来源与判读范围

- 延续四源第一性原理报告：`/Users/wenxiaofang/obsidian/05 Knowledge/deep research report/Deep Research - PIDL接近FEM的第一性原理重构路线.md`。完整论文和精确方法位置已存Obsidian；IFENN支持职责分工，不证明本方案AT1疲劳性能。
- `GRIPHFiTH/Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90:85–115`：有效history2/3/4、GP penalty、f进入装配但不含df/dd。
- `source/native_q4_damage_qp.py:84–159`：固定u/f的AT1装配与现GP不可逆域；不是节点lower实现。
- `tools/run_loss_weight_pair.py:90–113,216–231`：历史C/W0构造、固定f=1及共享NN loss/RPROP。
- 既有`c1_commit_protocol_20261015.md`与最终v4结果：前态不可变、trial与accepted区分、fresh joint pass与commit；一次提交不等于已平衡。
- PC16/W0/W25/E032/E033按各自已完成结果留档。本设计只是从这些实测限制选择新框架，不将其负结果转换为新框架的成功证据。
