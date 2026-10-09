# FEM physics → PINN / PINO 对接核查（2026-10-09）

## 目的与证据

用户要求实际尝试physics，并参考FEM已有约束。核对对象是当前S09三个Hard5轨迹关联的GRIPHFiTH输入族、源文件，以及现存U012原生Q4 c76 s4导出；不把别的FEM模型混入当前路线。当前本地GRIPHFiTH b680bb0 clean；这标识本次审阅源码，不冒充历史生产器二进制身份。原生导出用应变/能量数值复核建立实际一致性。

| FEM 实际机制 | 具体形式 / 支持 | 本轮处理 |
|---|---|---|
| 小应变、平面应变弹性 | E=1, nu=.3；Q4 2x2 GP | 已实现并对原生strain核验 |
| AMOR 能量分裂 | psi+=K/2<tr eps>+²+mu eps_dev:eps_dev；压缩体积能不退化 | 已核验原生psi与g |
| 损伤退化 | g=(1-d)²+eta，Hard5 eta=0 | 使用原生节点d插值到GP，不裁剪 |
| 力学平衡 | 自由DOF的组装内力Ru=0；Dirichlet处保留反力 | 首个PINN训练项 |
| AT1裂纹正则化 | 密度3Gc/(8ell) f[d+ell²|grad d|²]，Gc=.01,ell=.01 | 代码/导数测试完成，未进入本轮训练 |
| 不可逆与非负 | FEM选PENALTY，在GP处惩罚d<d_old及d<0；不是严格节点投影 | 实现原生penalty形式；未宣称硬KKT或绝对不可逆 |
| 疲劳路径累积 | q=g psi；alpha_new=alpha_old+max(q-q_prev,0)；f=min(1,(2alphaT/(alpha+alphaT))^p) | alphaT=.5，p默认2；不可变旧状态重算测试通过，未进行疲劳滚动 |
| 位移边界 | bottom u=v=0；top u=0,v=U；侧面自然零牵引 | PINN硬编码；c76实际U=.11999988 |
| 初始裂缝/加载路径 | 预损伤裂缝；Hard5标称子步.25,.5,.75,1,0 | 本轮冻结已接受d；不重新求预裂缝、不把峰值净差当疲劳增量 |

源路径相对项目根：
- `GRIPHFiTH/Scripts/brittle_fracture/INPUT_SENS_tensile.m`
- `GRIPHFiTH/Sources/+phase_field/+init/material_characteristic.m`
- `GRIPHFiTH/Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/amor.f90`
- `GRIPHFiTH/Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90`
- `at1_history_fatigue.f90`仅用于确认它是另一个分支；当前penalty不能被H=max历史场替代。

## 为什么先做位移平衡

现有S09 GNO训练输入是单元均值，缺少相容的节点位移/损伤与真实子步状态。非线性平均不能逆推GP值，节点自由DOF平衡也不能直接在单元中心按图边平滑代替。

找到可用原生Q4快照后，先冻结其d，只学习u(x)。这是PINN的单状态边值问题；映射x→u(x)，不是本次已训练函数→函数PINO。它隔离了物理算子和优化链路。训练不使用参考u标签，不试图让损伤增长。当前GNO没有被替换，E001/E002与六臂诊断结论不变。

## 自我验核

力残差与离散能量对u的梯度一致（拉伸/压缩两种trace）。相场残差与冻结psi/f能量对d偏导一致（含两种penalty）。重复trial fatigue不更改旧状态。硬边界正确且网络末层接收非零physics梯度。

对原生c76导出：strain相对L2=2.73336e-15，psi=4.17638e-15，g=1.66480e-17；d_GP最大误差2.22045e-16，BC误差0。原生自由力RMS=5.80417e-7并非零。此PASS仅核对算子实现，不证明参考已满足严格平衡或teacher资格。

## 接入PINO还差什么

给算子添加相容的节点位移输出和FE映射，按真实子步定义状态转移；data-only与equilibrium-only共享输出/边界/初始化/数据/预算。之后才追加核对过的AT1 penalty残差与疲劳状态更新。相场求解的冻结f偏导和残差损失对网络参数求导是两件事，不能混淆。物理收益应在完整开发轨迹与相同信息基线下检验，不能由本次单状态拟合替代。
