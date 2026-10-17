# FEM 合成监督增强 PIDL：唯一推荐与最小试验

2026-10-17，Europe/London；设计稿 v2，未训练、未求解、未访问新留出。
Owner：本对话 `01a14bc7-fd2a-73e1-9d0f-de457ba1dcc0`；HQ `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`。
本记录是 S04 下的方案孵化项，不占用新 Experiment ID，不改变 E011/E021/E024 或 S09 的协议与结果。

## 决定

推荐**全场 FEM 监督预训练 → 保留数据锚点的有限机械平衡微调**，直接使用当前坐标 PIDL 网络，而不是再造残差网络或算子。
先只攻克一个已有、数值闭合的 `U≈0.12 / c20s4` 状态：共同学习 `(u,v,d)`，疲劳/历史暂不学习、不提交。
首项交付是当前网络能否表达这一完整u/v/d场（history仍为给定条件）、整套监督辅助训练能否比当前条件 PINN 更好地复现该场，以及机械平衡项是否在同容量纯监督之外改善局部能量驱动。
这一步允许得到有意义的组件结果；完整历史、连续演化、跨工况和现实资格分别后置。

## 1. 已有资产能力与缺口

|资产/现有结果|本轮可使用的角色|已有能力|缺口/处理|
|---|---|---|---|
|E011 Q4/T3 四臂 production|指定算法的合成输出/形貌目标|共同 86,756 节点；Q4 86,408×4 GP；T3 172,816×3 GP；600子步与原生历史|不是整条收敛教师；Q4/T3 GP 不逐索引互换。峰值编号相同也不能混用历史更新时间|
|E011 MCS 局部重启 `pf_s04e011_mcs_20261017_v1`|最小试验的数值参照子集|10自然状态7个联合闭合；c20s4首个严格通过在outer18；已检索到该文件|每态来自各自原始前驱，未提交历史，**不是连续修复轨迹**；c60/80/83峰值未过20轮，不选作收敛标签|
|E006/008/009固定damage位移再平衡|条件UV参照与误差尺度证据|c20/c40/c76/c82/c83有位移与驱动修正量|只解位移，不能担保damage/历史。c20 UV修正0.014745%Us仍对应active场3.1360%变化，说明小UV误差会掩盖驱动偏差|
|E021/G5 四条已看过Umax轨迹|horizon0、P0归档模仿|U.11/.115/.12/.13共357周期，85,112 cells、98.6069%面积；已有因果PIN特征与原始场|不是完整原生GP状态；C0缺失；不能由s4补造s5。U.1175/.125不在本任务访问范围|
|旧单角锚定FEM7与旧PIDL|历史形貌背景|77,730单元damage/history与旧快照|BC来源绑定、相位和历史时序不完整；不混入当前Hard5监督池、不报告跨协议RMSE|
|MOOSE/Felino Hard5 v5|另一数值候选/方法背景|444 accepted states数值门通过|89峰值零事件，不能当目标疲劳行为的训练教师；本轮无需换生产器|

数字来源：E011 `experiment.md`、`runs/multicycle_stop_result_20261017.md`与compact manifest；E006/008/009 `decision.md`；E016 `g5_archive_admission_verdict_20261013.md`；当前/历史BC比较 `local_archive/bc_routes_comparison_20261017/README_analysis.md`。这些是已有结果的引用，没有重算owner结果。

**与源码相符的语义：** plane strain/AT1/Amor，E=1、nu=.3、Gc=.01、ell=.01、alpha_T=.5、Carrara p=2、eta=0。当前上下边ux=0，下边uy=0、上边uy=U；缺口FEM d=1为硬约束，原PIDL没有完全等价的硬damage输出。几何/网格相同不抹掉这一差别。
五步位移为 `.02999988,.05999988,.08999988,.11999988,0`，恢复态独立；`global_step(c,s)=5(c−1)+s`，c20s4=99。不要沿用无恢复偏移的旧索引式。
FEM trial fatigue/Picard 与 PIDL committed fatigue/联合Deep-Ritz 不同。需要分别保存不可变前驱、当前求解系数、post-commit状态，不能拿post-commit H反充pre-state。
现有 `source/fem_supervision.py` 会自动发现文件、允许时间/最近邻映射；新试验只复用字段语义，不采用其自动发现/插值作为原生节点/GP接口。

## 2. 少量路径比较

|路径|喂入/预测|优点|本项目的代价与选择|
|---|---|---|---|
|监督预训练→物理微调|坐标/已知加载，输出u/v/d；先FEM标签后有限物理项|先建立可见的表达能力，再测物理增益；可直接接现有PIDL|**首选**，微调保留标签，避免把reference不兼容误判成优化失败|
|从头数据+全物理混合|同上，同时训练历史/相场/力学|有望同时约束多变量|暂不选。trial/committed语义及多损失尺度未闭合；直接从头会混淆表示、优化和目标冲突|
|逐变量/逐阶段课程|先u/d，后history，再单步与整周期|把前一组件变成下一阶段的可用初始化|作为首选的推进方式，不另开模型。不能把FEM历史持续喂入称自主推进|
|FEM稀疏/噪声观测→反演/同化|训练时全状态作标签，推理只给预定传感器与加载|直连长期状态估计；可量化哪些观测有用|后续最有价值；当前需先证明全状态可表达与观测可辨识。噪声由预先设定观测模型生成，不称真实噪声|

E021已给出方向性raw残差改善：全周期最坏ratio .967385，但U.11 C41+恶化1.6083%；不能据此再默认需要NN/MOO。
E023/E024已测试固定damage下的UV校正/输出头：E023 c20/c60/c83 full UV RMS/Us约 `.000702665/.000890548/.001158720`；E024冻结尾段12个分区误差全部增加。故不重复固定特征头尾试验。
S09-E007固定damage位移算子在一条已看过U.125轨迹有 `Q_f=.442348,Q_u=.949860` 的限定改善；S09-E008完整状态screen的growth MAE从persistence `.000501735` 到 `.000736394`，且damage预测相关中位数约`.999537`。E009正在处理损失分配。这里补的是**当前求解网络的u/d联合表示和监督初始化**，不复制其场到场映射或计算。

## 3. 最小试验 A：固定信息、一个状态、三个对照

探索、synthetic、horizon0、单一已暴露状态的拟合/数值能力；不是泛化实验。无需用train/test节点拆分装作新样本。

### 精确目标与数据接口

根目录（绝对）：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/retrieved/`。
目标唯一指定 `output/mcs/c20_s4/outer_18.mat`；配套 `case.mat`、该case的 `result.json`、`input_manifest.json` 和其绑定的原生mesh/原始c20s3前驱。禁止选择其它outer/更好cycle、读取其它case或追加新FEM解。
本轮核查了已有MAT的HDF5字段/shape元数据和owner解码源码，没有读取科学数组值或复算场。精确映射如下；实现前仍需沿用owner解码器完成实际值/语义/残差重放，不能只凭shape宣布数据准入或Code Ready。

```text
metadata: trajectory_id, source/analysis commit, mesh_id, BC_id, material,
          cycle=20, substep=4, U=.11999988, timing='local-restart/fresh-joint/no-commit'
node: xy[N,2], connectivity[E,4], nodal_mass[N],
      uv_ref[N,2], d_ref[N], d_previous[N], prescribed_dofs/values
GP:   grad_shape[E,4,2,4], weights[E,4], final_f_ref[E,4],
      immutable_old_history (native named channels), reference residual definition
model conditioning: known U/material/geometry and fixed restart state
NN query: physical x,y -> u,v,d ; reference fields are losses, not NN input channels
```

源码与元数据已明确的读取映射：
- `outer_18.mat:/point/u`是MATLAB `[u_all;v_all]`、文件shape `[1,173512]`；`/point/d`为`[1,86756]`；`/point/raw`为`[4,86408]`，转置到`[E,GP]`。
- `/point/history234`文件shape `[3,4,86408]`，转为`[E,GP,3]`，owner分析将其对应alpha/active/f；final f取最后一通道，不能误当第四历史通道索引。owner coupled源码表明它来自最终u/d重新装配mechanics后的fresh phase评估：用相同不可变pre.history与当前raw得出trial history234，尚未accepted commit。不是下一子步/post-commit系数；P把此参考点trial f冻结为一次条件目标，不重新计算trial f。`/point/ru`是全位移力向量。case文件`/pre/lower`、`/pre/history`分别为`[1,N]`、`[4,4,E]`，后者转为`[E,GP,4]`。
- `inputs/common_common_initial.mat`含`node_coords [2,N]`、1-based `connectivity [4,E]`、`free_dof_u [172916,1]`和`free_dof_d [86505,1]`；只按owner规则转换索引。原生Q4 shape/梯度/物理Jacobian权重与lumped mass用现有`q4_geometry`构造，不从legacy centroids最近邻映射。
- 原前驱为`inputs/c0020_s003_post_commit.mat:/request28_snapshot`；其source identity来自既有input_manifest，case的不可变pre必须与之吻合。无需读取其它23个输入或其它case。
- PIDL初始化精确定位为NCP已有contract绑定的Q4 production archive下`best_models/trained_1NN_98.pt`的network参数（s3）；不继承它的RPROP状态。该文件在producer的receipt有确定定位，本次未远程访问或读其张量；若HQ实施时该资产不可达则停止，不换最新检查点。

所有臂允许同一原生问题/前驱与final f资料包。**机械力R_u仅依赖uv/d/材料/网格，不直接依赖f**，这一点由owner `mechanics_force`源码确认；final f只用于P的冻结断裂能目标、历史/相场背景及结果解释，不能把它误写成机械项的输入。P不使用目标u/d标签是有意的数据消融，不能声称P与S/C实际使用的信息完全相同；严格同标签/同容量的物理增益对照是S/C。当前不估计f、不更新H、不消除对完整数值restart条件的依赖。同一绑定的native Q4算子用于reference和预测：GP序为(+,+),(-,+),(+,-),(-,-)，每维坐标±1/sqrt(3)，shape按原单元节点顺序，梯度shape[E,4,2,4]；weights是正物理Jacobian行列式（2×2 Gauss每点参考权重1，厚度沿原模型）。raw为Amor正弹性能密度，active为raw*(1−d_GP)^2，不截断原始d；无f乘子。
物理加载U通过已知lifting进入，并非网络新增输入通道；本模型仍是逐状态优化的坐标网络，尚不是跨状态条件映射。

### 模型与损失

复用当前8×400 TrainableReLU、三个输出、当前物理位移lifting与nonsmooth damage映射、原生Q4/2×2GP。无额外残差头、teacher-tip坐标、对称投影、POD或图算子。
c20s3 PIDL文件**只提供网络参数初始化**；三个臂的d_previous、不可变GP历史、FEM缺口定义和冻结系数均取自同一个FEM local-restart输入包，不能用PIDL checkpoint自带或预测的旧damage/history/fatigue覆盖。三臂从**同一个c20s3原PIDL网络checkpoint**复制参数；s4 U换为精确物理值。其检查点路径由E011已有配对receipt绑定，不从目录选择最新文件。
位移lifting和damage映射在三臂一致；S严格只有L_sup，C严格只有L_sup+.1L_mech，没有隐藏附加损失；不可逆是P原目标中的penalty，未内嵌在三臂共用damage映射。三臂相对同一FEM d_previous/缺口定义报告原始误差。不要静默加hard projection使得“预训练效果”混入参数化变化。当前nonsmooth映射的尾段允许负值/超1，必须报告原始可行性，不能只截断后评分。

以native lumped mass归一权重，`Us=.11999988`固定；全域与公开几何局部区 `Z={0≤x≤.5, |y|≤3ell}` 各归一权重（Z固定，不用未来事件/teacher tip）。
`L_D = .5 mean_mass((d−d_ref)^2) + .5 mean_mass,Z((d−d_ref)^2)`；d范围尺度为1。
`L_U = .5 mean_mass(||uv−uv_ref||²)/Us² + .5 mean_mass,Z(||uv−uv_ref||²)/Us²`。
P的原生目标显式为`L_P=E_el+E_d+E_irr`，其中`E_d=sum_GP(w*f_ref*(w1/cw)*(d_GP+ell²|grad d|²))`，`E_irr=.5*w1*gamma_ir*sum_GP(w*relu(d_previous_GP−d_GP)^2)`；AT1 `w1=Gc/ell=1,cw=8/3,tol_ir=.001,gamma_ir=27/(64*tol_ir²)=421875,lambda_hist_weight=1`，elastic沿现有AMOR/eta0原式。不得另行归一或更换目标；正式源绑定若不符合这些既有配置则先回HQ修订，不假称当前PINN。
`L_sup=L_U+L_D`。全场与局部各半是避免大背景淹没裂纹区的预定探索选择，不是经结果调出的最优权重；单列每分量和梯度规模；不得用临时梯度等权或自适应权重改变本次固定.1系数。
`L_mech=(rho_u(uv_pred,d_pred)/rho_u(common_initial))²`，其中`rho_u=||R_u[free_u]||_2`是MCS同一定义的原生力向量L2（不是旧mass-normalized rho）；normalizer只从共同初始模型计算一次，若≤1e−12则本预定归一方式不可用，停止并回HQ，不作问题不可辨识的结论。damage梯度不detach，C始终称u/d联合机械残差微调；R下降可能来自damage/刚度改变，不能单独证明位移或裂纹修复。它只约束机械平衡，**不约束相场驻定、history演化或完整增量变分问题**。
在任何训练前，在reference上重放机械残差与BC，按MCS原native-vector一致性规则核验；已有c20s4 force norm为`3.7759255889e−15`，参照准入仍沿用既有`1e−8`机械屏而非要求机器零精确相等；否则属于目标/实现不兼容，不解释成学不到。机械重放不验证f/history的身份/时序，也不认证P完整目标与FEM相场约束等价；f/history仍按既有源字段/前态身份分别核对，不通过更严新标准重新否定旧结果。

|臂|预算与目标|能回答的问题|
|---|---|---|
|P 当前PINN条件对照|共同checkpoint，1500次既有原生Deep-Ritz/不可逆目标更新，固定同一final f/前态；不提交历史|当前物理目标在同问题/容量/更新数下的状态能力（不使用u/d标签）；区别于历史600步轨迹快照|
|S 纯监督|1000次L_sup，随后500次L_sup|与C同容量/同标签能力；是否增加机械项有增益|
|C 推荐候选|**复制S在1000次后的完整参数与optimizer状态**，500次 `L_sup+.1L_mech`|C/S只改变机械项；数据先学成再作有限调整|

P/S/C用同一Adam(lr=1e−4、betas=.9/.999、eps=1e−8、weight_decay=0)、float64、seed1；S和C尾段数据节点序列相同，并复制前缀终点的所有参数、Adam动量/step/buffers和随机状态。P保持既有能量公式，但optimizer/固定预算改成共同设置，故称“当前PINN目标的条件对照”，历史原RPROP结果另列，不声称重演原算法。S/P或C/P只能比较完整训练路线，不能单独归因于监督初始化；若未来要证明初始化改进原物理求解，必须另设计同一物理尾段对照，本轮不加第四臂。同更新数也不等于同FLOPs/GPU时间，三臂实际成本分别报告。Lsup节点batch4096，按预定全域/区内质量分布各2048有放回抽样，计算对应两个期望均值；该抽样不产生独立验证样本；按质量概率抽样后的损失用普通样本均值，不再重复乘mass。
mechanical term用全部native Q4装配，可按网络节点分块前向但不可把断开单元边界的局部残差冒充全局free-DOF残差；正式实现需核验梯度等价与内存。
总新optimizer updates=3500（共享监督前缀算1000一次，P1500，S尾500，C尾500）；每臂决策终点固定1500，保存0/1000/1500，不选最佳checkpoint。

### 组件criteria与路线决策

唯一预定探索主读数：`R_active = E_active(C)/E_active(S)`，`q=psi_raw(uv)*(1−d_GP)^2`，`E_active=sqrt(sum_{GP in Z}(w*(q_pred−q_ref)^2)/sum_{GP in Z}(w*q_ref^2))`；Z按实际GP坐标选择，权重为同一物理Jacobian权重；若reference范数或S误差≤1e−12，则该比值标NA、只报绝对量，不替换尺度。另存Z内未归一化`RMSE_abs=sqrt(sum(w*(q_pred−q_ref)^2)/sum(w))`和`ref_RMS=sqrt(sum(w*q_ref^2)/sum(w))`；NA检查分别作用于ref_RMS和归一化S误差E_active(S)。
`R_active<1−1e−8`是按预定容差记录的方向信号（该容差尚未认证数值误差界），**不是实际显著性阈值**；报告绝对/相对收益与所付出的u/d/反力/可行性代价。没有独立样本，不做置信区间或显著性宣传。

|观察|可保留的成果|下一步|
|---|---|---|
|S相对P降低u/d误差|在给定预算内达到所报告的拟合精度及组件进步（不据相对下降宣称完整场已准确表达，也不归因于初始化）|即使C没赢也保留该组件；不说物理无用|
|C active优于S|这一固定状态上有限机械项有增益|若无明显数据/可行性代价，提交第二个development状态/完整c1顺序试验方案|
|C只降机械残差而active变差，或u/d拟合受损|平衡改善与目标场保真存在本次权衡|不称综合修复；依据reference replay/梯度分量确定目标冲突还是权重问题，下一设计先审查，不自动扫权重|
|S学不到u或d|保留实际下降量与哪一变量受限|检查映射范围、u/d共享表示与全域/局部梯度；先做现有终态的轻量表示/优化判别，不自动加网络/预算|
|C/S/P皆几乎不动|仅否定本初始化+步数+目标的screen|报告梯度/饱和/停机，不能证明PINN容量不够或合成路线不可行|

这是探索标准，不要求一轮同时满足场误差、事件、轨迹、真实资格。若改善很小，只能支持一项便宜的辨别性后续；HQ结合实际误差和代价决定，不用任意5%/10%作为当前否决线。旧`.001`等判据完全保留于旧实验。

## 4. 后续推进：从条件场到演化与同化

1. **先完成A的实际数值和图。** 不并行重复E023/E024/S09。成功仅说明一个known-state neural solution可改进。
2. **完整c1五子步的监督课程。** 仅在owner已有一致前驱/单次提交的合格序列可用后，用相同U路径、d_old和history传播；先逐步teacher forcing，再从同一个已知初态全部用预测输出推进。后者只使用已知加载、预测的d/history和本步物理优化，**不使用任何未来FEM标签或final f**；允许逐步优化，不冒称一次前向的算子预测。逐状态reset与自主rollout分别出表。MCS孤立点不够，不能拼轨迹。
3. **完整场状态。** u/v/d继续nodal；H、alpha_bar、q_prev、f在原GP support。先按producer定义逐项核对：例如旧history slot1的raw不能直接改名为不可逆H；若H并非独立状态，不增造伪H监督头。非负量的log1p尺度只由training trajectories确定，f可由被核验Carrara关系计算而非多预测一个冗余头；前提是各历史量语义与更新时间一致。每个substep一次update，最终unload也纳入，不能只学s00→s04却宣称下一cycle可用。
4. **按完整轨迹/工况/试件划分。** 已经看过的U.11/.115/.12/.13只可用于development；所有normalizer、scaler、课程阶段选择只用训练轨迹。未来确认轨迹由HQ另行授权，本任务不命名其中任何一个为可打开测试。节点/相邻帧随机切分不能论证跨轨迹泛化。
5. **稀疏观测反演/同化。** 固定传感位置、观察变量、噪声机制和预测起点；全FEM状态只作训练标签，推理仅给观测、已知加载和估计前态。先报告从稀疏观测重建u/d/history的误差，再报告同化后未来周期推进；full-state oracle只作为上界，不能混进可部署输入。

## 5. 资源、停止与实际交付

A的提案上限：单张≥24GiB可用GPU，目标≤2 GPU-hours、host RAM≤32GiB、任务存储≤2GiB；这些是**预算上限，不是已测运行估算**。E023仅UV的三态每态约11.3分钟/10000更新，不能直接外推完整网络+Q4残差成本。
实现后先作不含optimizer更新的形状/数值/梯度/内存检查，在批准的producer分别对P、L_sup、L_sup+.1L_mech三种实际计算图各测100次纯forward+backward（此项是未来计算，不在本轮执行）。令各图含optimizer开销预留后的单步估计为t_P/t_sup/t_C，`T_est=1500*t_P+1500*t_sup+500*t_C+T_preflight+T_evaluation/save`；未知开销未给出可信预留则不启动。峰值需包含反向图、参数/梯度、Adam两组moment缓冲及临时张量；可不更新真实模型而分配等形moment缓冲作内存测量。分块前向若统一反向仍可能保留所有图，不能据此假称显存已下降。normalizer/Adam/RNG/采样起点必须隔离或完全恢复，预检与评估归档成本都计入2h。如果T_est超过2h或内存不适配，不启动训练，由HQ缩小新设计，不能运行中扩容。Mac只允许轻量检查，不训练；producer、GPU、fresh Run ID由HQ统一批准。
运行中任一不可恢复identity/shape/BC/finite/GP/单次历史语义错误或资源越界即停止受影响任务；零history commits，零FEM求解，零留出访问；不自动换机、重试、延长、换seed或扫权重。数学上允许的可行性误差作为结果报告，不能以隐藏截断掩盖。

未来最小结果包必须含：
- 三臂固定终点的u/v/d全域与Z误差、active/raw GP场误差、共同free-DOF残差、reaction、damage范围/不可逆/缺口误差、耗时/显存/更新数；保存实际预测与所有误差分子分母。
- 同一状态reference/P/S/C的u、v、d、active及误差图，原生坐标与相同每变量色标；不平均镜像/平滑/换场；profile固定x=.25/.40，展示裂纹带宽与位置。
- 0/1000/1500各臂误差/残差/损失曲线；这是优化曲线，**不是物理演化曲线**。
- 到阶段2才交同初态的5子步U/反力/d前沿/能量/history演化曲线及同状态场图，teacher-forced与自主推进分图。
- 一个从实际score表生成的`README_analysis.md`，Run/源码/配置/输入身份与资源receipt。图必须打开检查，decision-facing PNG再同步Obsidian。没有新计算结果时不造示意结果图。

## 6. 本轮状态与复用边界

本轮已完成资料/源码检查与设计；只读MAT元数据、没有科学数组值解码、重算owner结果、训练、FEM、远程访问、资产转移、新留出或新结果。
独立docs worktree `codex/fem-synthetic-augmentation-design-20261017`，base `6748b665004d703128a6143eb8e236b59b3890de`；仅新增本方案和其必要审查记录，原owner文件不改。
有界Pro设计复审已通过，范围仅为研究设计，见[fem_synthetic_augmentation_review_20261017.md](fem_synthetic_augmentation_review_20261017.md)；科学方案身份为`0a7f4daed466180b09d36a1379563bf16b3f634e`。下一步交HQ决定是否注册/实现该最小试验。正式实现仍需确切输入schema、runner、配置、预算可行性及相应独立代码审查；本设计不冒称可直接执行。


## 来源定位（只读，不要求重新遍历）

- E011：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/`，本轮owner HEAD `bc79a204`；MCS producer `0a0691ec`、analysis `31730a3f`。复用`tools/s04_e011_analysis/{analyze_multicycle_stop.py,localize_endpoint_tight.py,run_multicycle_cross_replay.py}`的字段/力/Q4约定，不执行其批量验证入口。
- UV监督与表示诊断：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/`，本轮owner HEAD `a399ef7d`；E023/E024原结果不变，本方案不接管其后续头修复。
- 残差与G5归档范围：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016/docs/research/S04/`，本轮owner HEAD `82cd0925`；仅引用其E016准入和E021结果，不运行其guard/worker或追加拟合。
- S09：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/docs/research/S09/`，本轮owner HEAD `e56fa6cc`；只读E007/E008/E009设计与紧凑结果，不读取被保护数据。
