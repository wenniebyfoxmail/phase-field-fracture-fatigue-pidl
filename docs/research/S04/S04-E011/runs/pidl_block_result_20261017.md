# E011 PBD r1 — completed fixed-state PIDL plateau diagnosis

### 2026-10-17 PIDL loss平台：c1／c20峰值分块判别完成

**直接Q4 damage局部闭合；PIDL位移能量有实测改善，但尚未达到FEM平衡。当前没有证据把剩余差距认定为全网络容量上限。** 三个subagent分别处理主语、实现／输入及独立数值和图件检查；作者不独立审核自己的helper／输入构造。

**本轮FEM参照**是原生Q4的c1s4 outer9／c20s4 outer18局部收敛峰值，自由Ru约3.8e-15、可行Rd分别2.02e-6／3.15e-6；不是完整修复演化。**PIDL初态**仍为原paired-Q4的model4／99（seed1，8×400），自身前驱checkpoint3／98。保持位移bubble／lift边界；Smooth-B0是damage冻结锚点logistic，不是spline。各网络臂独立重启，不能把U、D各臂拼成新联合模型。

原PIDL float32联合目标在GPU上两点均按原阈值复现通过；换用本轮LBFGS后，保存参数与初态逐tensor相同，实际非零更新均为0。**这确认该配置没有前进，不能证明驻点或容量极限。** 旧CPU回放失败／不确定记录保留，没有修改旧阈值。另8个局部网络臂均到达预设评估预算，不能称已收敛：每臂至多200次（含试探与恢复终点核读），Direct-Q4至多800次；历史提交0，连续演化0。

|状态|PIDL U能量下降／固定FEM d|PIDL U末态自由位移残差|Smooth-B0 D可行残差|直接Q4 D可行残差|
|---|---:|---:|---:|---:|
|c1s4|47.91%|0.0171187|0.0117129|1.43776e-06|
|c20s4|51.84%|0.0159958|0.00997472|1.43388e-08|

U块固定FEM damage，仅最小化PIDL物理弹性能；D块固定FEM位移，用PIDL自身前史／committed-f，比较同一box[0,1]＋GP软罚目标。两类残差对应不同条件问题，不能横向当成同一个联合残差。Direct-Q4的c1／c20分别用了799／478次目标函数调用，另各1次末态观测；均通过预设4e-6的box残差条件。Direct-D替换damage后，FEM位移上的Ru仍为2.06e-4／5.68e-4，因此damage块通过不等于耦合通过。

PIDL U能量臂仍比同一FEM弹性能高18.22%／25.02%，全域梯度H1差为55.59%／59.13%。冻结输出头能将位移质量L2拟合误差降至1.92%／2.11%，但机械残差和能量更差；监督H1拟合也没有提供更低同物理能量的网络见证。故不能用不同拟合loss互相排名或据有限预算失败断言架构表达不可能。

**当前主残差并不集中在小导数区。** D能量臂约94.24%／93.27%节点属于小导数区，但只承载box投影残差平方的1.34%／2.28%；精确0/1饱和处仅承载0.50%／1.44%。这是本轮冻结场的新读数，不能照搬旧80.7%的饱和机制，也不改写旧Smooth-B0阴性结果。导数跨度很大，优化条件数仍是待检验假说。

**先分清目标／历史差异。** PIDL γ=16875；FEM γ=421875且严格FEM有节点不可逆硬下界。原PIDL的节点damage历史`hist_alpha_pre`（不是GP Carrara累计量`alpha_bar`）在两点均越界：最小−.000444／−.002488，最大1.000202／1.000335；对应165／238个GP历史>1，不能直接作为新box问题的硬下界。将同一收敛FEM场放入PIDL自身damage目标，box残差为.1756／.3532，远非FEM原生可行残差。c20 PIDL pre-committed-f与FEM accepted-trial-f最大差.9785，二者历史时点／演化路径不同，不能算作网络容量误差。严格FEM可行终点罚项为零，25倍γ本身不能直接解释该终点场差。

**完整联合场与条件交叉场分开比较。** 下表分母固定为各自FEM参照范数；上节MCS使用固定PIDL分母，百分比不能直接相减。

|同状态原PIDL联合场 vs 收敛FEM|c1峰值|c20峰值|
|---|---:|---:|
|位移质量加权向量relL2|3.59%|3.74%|
|damage GP加权relL2|9.80%|15.79%|
|active GP加权relL2|22.59%|39.08%|

原PIDL u与FEM d交叉组合时，active差为FEM范数的45.96／51.78倍；经过U能量优化仍为6.29／6.33倍。这说明u/d的空间配对会遮蔽单场误差，也暴露局部热点与整体能量的差别；**不是完整PIDL基准误差变成6倍**。固定FEM u配Direct-Q4 d时active差13.45%／21.98%，但使用了给定FEM位移，只是条件damage参照。当前完整PIDL基准没有被这些独立臂替换。

**下一项只选同能量的UV头部判别。** 保持隐藏特征、原位移边界和固定FEM d，对UV输出头直接最小化与本轮U能量臂完全相同的弹性能，测量可达收益、输出头梯度和场残差；这是本轮固定FEM damage的PIDL U块弹性能目标（原联合目标中的弹性能项），不重复另一对话E024的监督残差头任务。只有降到更低同能量才能作为优化机会的见证；未闭合或无改善仍不能推全网络容量上限。保留Smooth-B0和已闭合Direct-Q4路线。进入下一次加载—卸载闭环前，必须使用合法共同前史、FEM一致的phase-f／可行域，并检查damage后位移再平衡及联合收敛后单次历史提交。新增预算已汇成一张[下一判别卡](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/pidl_same_energy_head_card_20261017.md)，尚未启动新Run，交科研总部集中决策。

来源：生产`2c7c5dc6`，Taobo GPU0，PID1592991，21:07—21:21 UTC完成；400文件／148,175,737bytes全部重核，未OOM、无非有限值或合同失败。分析`bc79a204`，独立数值、实际网络重放与图件审查见[完整记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_block_result_20261017.md)。原输出头D候选存在已记录的跨设备微小差异且拟合失败，未当作容量上限。没有新的完整FEM／PIDL疲劳演化或物理teacher结论，committed-f／trial-f与联合／staggered差异仍保留。

![[e011_pbd_20261017_block_scalars.png]]

两点独立分块；D的直接Q4目标自身误差为0，log轴不画0，不代表该求解缺失。颜色为物理cycle，横轴为独立方法，不是连续演化。

![[e011_pbd_20261017_c20_joint_fields.png]]

真正同状态的收敛FEM与不变原PIDL联合场：从上至下u／v／d／active，列为FEM／PIDL／有符号差；各物理量独立色标。[c1同类图](attachments/S04/2026-10-17/e011_pbd_20261017_c1_joint_fields.png)。

![[e011_pbd_20261017_c1_U_active_maps.png]]

条件U块：固定FEM d，参照／PIDL位移块／有符号active差；不是新联合PIDL结果。[c20条件U图](attachments/S04/2026-10-17/e011_pbd_20261017_c20_U_active_maps.png)。

![[e011_pbd_20261017_c20_D_damage_maps.png]]

条件D块：直接Q4参照／Smooth-B0／有符号damage差；参照是PIDL自身条件目标，不是FEM d。[c1条件D图](attachments/S04/2026-10-17/e011_pbd_20261017_c1_D_damage_maps.png)；[独立优化曲线](attachments/S04/2026-10-17/e011_pbd_20261017_accepted_objectives.png)。

## Exact provenance and execution

Protocol [PBD r1](../pidl_block_diagnosis_protocol_20261017.md); clean producer2c7c5dc62415389da089ad522ec6c03ff33b1404, branch codex/hard5-q4-t3-2x2-20261005. Local run `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production`. Remote root `/mnt/data2/drtao/wennie/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production`, archive `/mnt/data2/drtao/pidl_archives/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production`, worker.log under root; full command/PID in launch_receipt.json. Probe separate1591524, production1592991. Newroots/caches/threads1/nice10; shared inference services untouched.

Input manifest `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/pidl_block_preparation_20261017_v1/inputs_manifest.json` SHA256 3f5bdaa5959e2efc3ea996001b196478b6786f479c7b0f3dab0112a53041da41; analysis `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production/analysis_v4/summary.json` SHA256 41283db269dd45d277312fcc603349488af439141558600b55b04e2374501a8f. Probe300files36529619bytes verified; initial recursive-SCP240s timeout retained, one immutable stream transfer resumed retrieval without numerical rerun. Production400files148175737bytes verified. Independent source fixtures5head+1Q4 passed; cached/source energy/AD-analytic/native force/FD contracts passed. Final8figures inspected, sidecars checked; v1-v4 analysis changes only observation/figure reporting, rawproducer untouched.

Independent numerical review `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/pidl_block_preparation_20261017_v1/numerical_independent_review.json` SHA256 bcee6e19d384a4748c125af73910f3d60bbf0a7f3c7f018f6d383229b3c39446. Helper/input author excluded independence for those components; separate CodeReady reviewer verified them. Actual head replay UV max<=3.77e-12; D cross-device max1.31e-7/5.67e-8, relative errors6.07e-9/1.88e-9, separately preserved; source large coefficients not deployed. Old retained NCP nodal-d gradient remains invalid/excluded. GPU-source new two-point qualification does not rewrite old CPU-source mismatch outcomes.
