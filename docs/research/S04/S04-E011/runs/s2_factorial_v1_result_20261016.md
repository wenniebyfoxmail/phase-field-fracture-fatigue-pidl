# c1s2 controlled solver / predecessor diagnostic — 2026-10-16

**主要差异来自本子步局部求解/停机控制，前驱lower/history差异在这次受控比较中的影响较小。** 相同前驱下换solver，active加权相对L2差为78.246%/78.238%；相同solver下换前驱lower/history，仅为0.3281%/0.0270%。热启动桥接分量L2约为原实际差D的12.21%，也不能完全忽略。该结论绑定本次共同trial起点；原流程仍未达到严格联合收敛，所以不是两个已联合收敛平衡解之间的比较。

**已完成两个已有端点重启检查与四个受控组合，全部在既定预算内完成；没有历史提交、recovery或后续子步。** OO/RR在本轮代表原/修复FEM流程；本轮没有新增PIDL训练或把原FEM当物理真值。

四组合的第2步初始u完全相同、初始d取两份s1damage的逐节点最大值，从而对两份lower都可行；每case用同一原生算子重建同值KK，并逐项断言KK及完整u/d/residual预测器完全相同。只改变“原/修复solver”与“原/修复s1的lower+history”。共同max-d是人工trial起点，未写回accepted状态。两个anchor则从各自真实s1初态重启，u/d、旧历史下的trial history、raw/r4及outer均复现原归档；两锚点先通过才计算四组合。

|case：求解器/前驱lower与历史|闭环|fresh C|u/phase调用|active积分|全部试算最小f|f<1的phase调用|终点f|
|---|---:|---:|---:|---:|---:|---:|---:|
|anchor_OO|3|21809.5|11/80|0.001653598404|2.16201e-05|19|1|
|anchor_RR|20|0.392168|90/61|0.001248976748|1|0|1|
|C_OO|2|22329|8/53|0.001697057499|2.17215e-05|11|1|
|C_RO|19|0.929612|86/58|0.001249271478|1|0|1|
|C_OR|2|22442.1|8/58|0.001696933593|2.17209e-05|11|1|
|C_RR|19|0.941389|85/58|0.001249274019|1|0|1|

C使用各case自己的**旧lower/history**、相同最终u/d重新组装，严格条件仍`max((Ru+Rd_feasible)/4e-6,Ru/1e-8)≤1`；原solver保留原cached接受规则，因此其C可大于1，不把它伪装成严格收敛。修复保持20闭环/250u+250phase上限，调用含每case一次预测器cache重建与最终fresh审计；单独的System setup初始组装另记1次。所有trial回调的f极值/次数都保存，包含未接受试算；不能把“终点f=1”写成“所有内部试算f=1”。

**如何区分来源。** 第一字母是本子步solver，第二字母是前驱lower/history。共同起点的四场为OO、RO、OR、RR。对称局部控制分量`L=[(RO−OO)+(RR−OR)]/2`，不可逆输入联合分量`P=[(OR−OO)+(RR−RO)]/2`，热启动桥接`Wb=(OO−原归档OO)+(原归档RR−RR)`。这样原有实际轨迹差`D=原归档RR−原归档OO=L+P+Wb`，GP最大重构误差5.551e-17。它保留初始化的影响，避免把热启动也算成历史效应；P仍是lower与history的联合效应，没有声称把二者在整个求解路径上完全分离。

|对原有active差D的分解|沿D的有符号投影系数|分量L2 / D的L2|积分分量|
|---|---:|---:|---:|
|相同起点与前驱下，局部求解控制 L|0.90301768|0.90599724|-0.0004477228|
|相同起点与solver下，lower+history P|-0.00031241309|0.0019007367|-6.0682159e-08|
|原实际热启动与共同试算起点之间的桥接 Wb|0.097294732|0.12207248|4.3161823e-05|

投影系数定义为`<分量,D>_GP/<D,D>_GP`，三项相加1；它可以为负或大于1，描述沿观测差方向的抵消，不是因果百分比。各分量L2与条件对照/交互项另存表中；L/P对交互作对称分配，分解依赖所声明的共同起点与这两套求解控制，不能据此推出普适因果比例。

**差异发生在哪里、active怎样改变。** 旧实际s2场差的GP加权平方误差中，x≤0初始裂纹wake占99.4717%，x>0右ligament仅0.5283%；上/下wake分别55.2084%/44.2633%。最大GP差位于`(x,y)=(-0.2497626365,0.001470041928)`，原生零起始cell47807/GP3，修复−原流程active=-0.2644420916。这是已存在裂纹后方的窄带差异，不能只用全域积分看成均匀变化。

共同Q4回放`active=(1−d_GP)^2 ψ_raw(u)`的u/d对称分解：位移响应投影−4.32824、damage退化投影+5.32824，各自L2约为最终差的10.05/10.52倍，存在强烈抵消。仅更换位移而保留原damage的交叉场并非力学平衡态，不能当新的FEM解。积分下降24.47%与场相对L2差79.41%是上述两种响应叠加后的结果，不支持把active差单独归因位移或damage其中一个。

**需要修正的解释范围。** 前一轮“f全程1”依据是已接受五子步的终点GP。本次覆盖所有phase试算后，原solver确实进入f<1分支，三份原solver case均进入f<1分支；三份修复solver case全部phase试算保持f=1。原重启anchor在19次phase调用出现f<1、最低2.16201e-5，trial累积量最高214.56577；其最终max(alpha_bar)仍仅.2742003、f=1。这是临时试算历史，未accepted提交，不能称持久历史爆炸/重复累积。**终点未发生疲劳退化，不等于内部求解路径不受trial-f分支影响。** 本轮未独立冻结f、改切线或单独移除约束，因此尚不能将局部solver效应进一步唯一归因某一项。

固定旧s2终点u/d做8种lower/history回放：纯history交换在两个终点均保持f=1、相同active与phase残差；lower交换则引入不同罚项与bound-filtered残差。跨lower的混合终点可能违反新下界，表中显式给出infeasible_nodes；这些混合场不是可行收敛解。该结果支持检查lower传播的作用，不能用终点交换来否定内部历史分支的影响。

**可支持的结论仅限本次c1s2局部数值/状态敏感性。** 残差下降不是唯一解/能量全局最小或更物理；无新的c83、寿命或多cycle线性/指数增长结论。旧raw/v3失败、冻结E003/E011生产结论不改；PIDL committed-f与FEM trial-f、联合Deep-Ritz与staggered/Picard差异仍在。

## Provenance and decision

Producer clean523f0320398312557afb8df74c38d901a44abc13 / branchcodex/hard5-q4-t3-2x2-20261005; CITPC12AD\xw436 R2025b1CPUthread; WMI34708/launcher2368/worker16676, UTC12:15:55.5146225Z. FreshrootC:\Users\xw436\jobs\E011_S2X_20261016_v1.15files71729bytes/6inputcopies278959431bytes exactSHA/sizes verified; packageSHA c18a3087947ad37ab4afc9d2fd5edf7d8bcdaa942637db7bda626901c06ec67f.13MATLAB static/source/which/MEX checks,34selftests and6inputsame-workerfullread/geometrypassed. No retries/budgetincrease/processdisturbance. All48files/580688443bytes retrieved/fullSHA-sizeverified.

Raw/data endpoint: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_s2x_20261016_v1`. Required files: retrieval_verification.json; analysis/s2x_analysis.json (source/codeSHA/nativeproof); native_cases.csv; controlled_attribution.json; controlled_allocation.csv; conditional_contrasts.csv; offline_replay.json; cross_ud.csv; history_lower_cross.csv (including infeasible nodes); fixed_regions.csv. Three figures have same-stem sidecars; visual inspection and sidecar validation passed. Independent archive/numerical and final narrative reviews passed; see analysis/independent_review.json and figure_qa.json.

Claim verdict: supports bounded six-case numerical/field decomposition. Research disposition: advance mechanism localization, no long trajectory or teacher promotion. Binding residual mechanism within local control remains composite; the measured trial-f excursions select the next small lever (same-start bound/fresh-control versus explicitly frozen trialf diagnostic), not a threshold change or a newlife run. No new such native arm in this version. Exact canonical protocol: [S2Xr1](../s2_factorial_protocol_20261016.md).

[Compact exact artifact manifest](s2_factorial_v1_manifest_20261016.json) records source, native rows, allocations, hashes and bounded claims. Local independent terminal numerical and narrative reviews passed.
