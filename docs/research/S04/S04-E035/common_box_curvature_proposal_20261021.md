# R015后下一决定：用原能量曲率控制初始步长，仅准备

目的不变：共同有界模型全部24态至U=.4，再原PIDL，45°后置。R015的一次真实科学启动已消费，首次失败停止，本文不创建新RunID、不部署、不增加回溯/迭代上限或求解。依据原授权的“scientificLaunchesMax:1”和“first genuine science/control/IOfailure”，再运行须新的具体执行批准；原剩余预算不是自动重试。

## 保存量已经解释的停止

R015的7态至U=.21独立核验通过；U=.24第1次外层、第1次PF迭代的完整步和12次减半均被能量Armijo拒绝。原点alpha恰好等于accepted history，最后实际trial在box内。固定driver沿可行线段，negative-alpha罚项为0，history负分支对正步长符号固定，能量沿该方向恰为二次函数。

使用保存的最后梯度与位移点积，以及日志记录的原点梯度点积：Q_last=R_last·δ−g_origin·δ=5.5349533634e-8；S_full=-4.01488239245e-5，Q_full=.928611081279。重建全部13个能量与日志最大差3.91354e-14。最后实际步2^-12=.000244140625使能量增加1.78728e-8，而Armijo要求减少9.80196e-13；同向二次模型允许lambda≤8.64620503706e-5。第14次二分仅为数学预测，未实际试过、未接受，也不证明能完成24态。最后原生残差与独立能量梯度差2.38014e-15，不支持把这次停止归因于原能量/梯度符号不一致。

这比“把12改14”更有依据的改变是：直接从已知固定driver/history的能量曲率选择首步，保留后续12次减半。不是盲增试探次数。

## 同模型算法候选

候选文件在scripts/shear/proposals/box_q4_ray_curvature.m、box_phase_curvature.m和run_manav_static_fem_box_curvature.m；test_box_phase_curvature.m准备同批软历史与Q=0小数组检查，未执行。未执行，原R015部署文件和负结果不变。

当前可行alpha、投影PDAS或既定正对角fallback得到可行目标q，s=q−alpha，S=gᵀs<0。在alpha+t*s、0≤t≤1上，以每个Gauss点可到达的最大分支Hessian构成Q上界：

`Q = sum_G w [ (2ψ + γir*I(healing reachable) + γrec*I(negative reachable))*(N*s)^2 + (3Gc ell/4)*|B*s|² ]`。

healing reachable：min(Nalpha−Nold,N(alpha+s)−Nold)<0；negative reachable：min(Nalpha,N(alpha+s))<0。可行Q4场后者为假，但保留原罚项表达。所有系数来自原材料/罚项，无调参和新装配/因子分解。固定driver必须非负；Q有限非负，否则停止。

首步`lambda0=min(1,(1−c1)*(-S)/Q)`，Q=0取1，c1保持1e-4；后续lambda=lambda0*2^-j、j0..12。根据Taylor上界E(alpha+λs)≤E(alpha)+λS+λ²Q/2，这一首步留有充分下降裕量，满足原Armijo的理论充分条件。实际仍每个trial重新组装、核验真实能量和同点原梯度单位KKT；不能用曲率预测替代接受证书。数值舍入、条件性、原机械失败或500次迭代仍可能导致整体失败。

除这一首步选择外，原物理能量/盒约束/软历史/BC/mesh/U/500更新/12减半/KKT1e-6/耦合1e-4及愈合.005全部保持。新runner采用nested phase_curvature引用本次动态driver和previous，避免匿名函数在初始恢复时捕获旧history/driver。

## 一次完整计算合同与预算

若新具体批准：独审候选及必要同批轻量fixtures后，仅从初态一次完整24态FEM，全部合格才原GPU一次PIDL。不拼R015/R012前缀。FEM仍原CITPC12、4CPU/16GiB/10GiB、step1800/recovery600，cap=min6000,最新原3h累计余量,原截止减1800s。费用包含R008/9/11/12、R015本次189.666520s、全部准备/准入/取回等；不创建新的3小时。精确剩余额度要在新准入前用费用账本重算并冻结绝对终点。

原截止2026-10-22T00:20Z（UK01:20），科学最迟23:50Z，PIDL保留至少7200秒完整轨迹机会且实际资源可用才启动；这不是测得的运行时间保证。原6单GPUh、固定GPU UUID/资源上限不变。45°只有主比较完整且原余量覆盖才运行。首个真正科学/控制/IO失败仍停止，不连续调初步系数或隐式再试。

当前仅做已有保存量归约、源码准备/独审和收尾，无新增科学运行或PIDL。
