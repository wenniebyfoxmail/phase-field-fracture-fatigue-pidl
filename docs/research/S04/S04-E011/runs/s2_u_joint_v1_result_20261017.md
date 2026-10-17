# c1s2：inner u与联合／外层位移停机条件分离（2026-10-17）

**后续55.90%的大active场变化主要来自联合／外层条件要求继续耦合再平衡；inner u精度对场的影响很小，但决定最后能否通过严格位移残差条件。** 严格停机的两臂在真实共有outer1–19中，只改inner u时最大场差为原始场范数的0.00336688%，出现在outer11。这是一项固定FEM c1s2的数值路径诊断。

## 固定状态与两项干预

协议：[S04-E011-S2UJ/r1](../s2_u_joint_protocol_20261017.md)。状态为FEM native Q4 c1s2、PRE-COMMIT、加载位移0.05999988，旧前驱为original c1s1已接受的O1/version1。四臂使用相同u=O1u、d=max(O1d,R1d)、KK、完整第2步预测器、lower与旧历史；没有recovery、reset、历史提交或下一子步。

网格86756节点／86408个Q4，2×2GP；E=1、nu=.3、平面应变AT1/Amor、Gc=.01、ell=.01、alphaT=.5、eta=0、原生p=2，GP罚参数421875／13781.25。fresh刷新、约束damage及inner damage容差4e-6均固定。21个复用MATLAB模块逐字节不变，约束方向、对角初始化、线搜索、边界和算子不变；mechanical仍用无正则cholmod2方向、无位移线搜索，inner u采用严格小于容差的判断。

- U只改变inner u容差：U0=1e-6，U1=1e-8；这里的U是容差因子，不是加载位移。
- J只改变两个外层门槛：J0的(joint sum, outer u)=(4e-4,4e-4)，J1=(4e-6,1e-8)。本轮未把J中的两个门再拆开。

所有臂采用相同公式max((freshRu+freshRd_feasible)/jointtol, freshRu/outerutol)≤1。初态只观察，不准在outer0接受，至少完成一个完整u/d/再评估块。每臂预算仍为20个完整outer／250u+250phase，计入所有观察与拒绝试算；controller为248／248，另有case cache一次u，共享setup一次u单列。每块预留2次mechanics与1次phase观察；未增加最少内循环次数、修改容差救场、加预算或重试。

## 四臂实际结果

|臂|inner u容差|joint / outer u容差|完整outer|u／phase调用|自身条件接受|共同严格C|
|---|---:|---|---:|---:|---|---:|
|U0J0|1e-6|4e-4 / 4e-4|1|6／4|是|29103.0488|
|U1J0|1e-8|4e-4 / 4e-4|1|6／4|是|29103.0488|
|U0J1|1e-6|4e-6 / 1e-8|20|94／59|否：完全停滞|18.504507|
|U1J1|1e-8|4e-6 / 1e-8|19|104／57|是|0.929612209|

四臂均执行，三臂按自身规则接受，**仅U1J1达到共同严格C≤1**。两个锚点U0J0／U1J1准确复现上一轮S2DJ P1J0／P1J1：u、d、history234数值差均为0，raw/r4及outer1／19一致。U0J1在outer20的u/d与outer19逐值不变，退出原因是exact_stagnation，不作为接受终点，也没有用额外求解救场。未补缺失的接受角点或计算完整四格贡献。

## 场差与分母

上一轮55.896103832%采用original S2DJ00的active场范数。本轮新00是上一轮S2DJ10；同一个00→11差向量若用新00范数，得到75.721343775%。这不是误差又从55.90%增长到75.72%。第7份输入scale_reference只用于全文预读和离线复核原始分母，不参与新求解；新／旧参考的输入SHA均保存在compact manifest中。

|比较|状态类别|相对原始S2DJ00场范数|
|---|---|---:|
|旧J下只改inner u|两个已接受outer1端点|0|
|严格J下只改inner u|真实共有outer1–19中最大值，outer11|0.003366880575%|
|严格inner u下只改J|已接受outer1→19端点|55.896103832%|
|宽松inner u下只改J|outer1接受点→outer20停滞点，仅诊断|55.896106610%|

U0J1最后完整outer20与U1J1已接受outer19的场差仅为原始范数的0.000062736867%，但这不是两个收敛解的比较。四臂首个完整outer的u/d/raw/Ru/Rd/history234均数值相同，首轮五个active条件差都为0。同outer比较只使用双方确实保存的状态，不延拓已停臂；固定参考范数也不等于一条延拓轨迹。outer是算法迭代，不是物理cycle/time，L2不能直接相加为因果百分比。

## 残差为什么停不下来

首轮mechanical内循环在两种inner u容差下都已达到约1.31e-15。随后严格phase更新damage／刚度，freshRu变为2.91030e-4，Rd为2.03029e-6。旧J允许以自身C=.73265直接退出，即使inner u已经很严格。因此，更精确地完成第一次机械内循环，不能代替damage更新后的联合再平衡。

严格J使两臂继续。其真实outer1–18中，joint sum与outer u两个归一化分量都大于1。严格U1在outer19得到Ru≈1.8787e-15、Rd≈3.71845e-6、C=.929612；这是后续大场变化所在的耦合过程。本轮对J是两个门槛一起干预，不能单独把55.90%归给某一个门。

宽松U0在outer19留下Ru=1.850450703e-7、Rd=3.718425818e-6。机械内循环已认为Ru<1e-6合格，phase也认为Rd<4e-6合格，下一轮两者均不改u/d。此时joint sum分量=.975867722<1，但outer u分量=18.504507>1。**最后的停滞明确卡在outer u门：inner u容差比外层要求宽，内循环已接受的残差仍过不了外层。** 场非常接近严格臂，并不能替代该残差检查；本轮也未靠放宽外层门或单纯多加outer来接受它。

已接受J场差平方的98.43345%位于x≤0初始裂纹wake，最大|gap|=.183294906，位置约(-.280812942,-.001142960)。只改inner u的最大同轮差出现在outer11，最大GP差7.73148e-5，位置约(-.265478568,.001626377)。它是wake内的小数值路径变化，量级不足以解释55.90%的大场重分布。

## 运行与复核来源

- Producer：CITPC12，AD\xw436，R2025b单CPU线程，WMI26148；2026-10-17 15:52:01.3871293 UTC启动，15:57:12.4707204 UTC观察到终态且无本任务进程。远端目录`C:\Users\xw436\jobs\E011_S2UJ_20261017_v1`。
- 实际源码为干净提交`383a77827d3f60be6bcc0326c6923451df94a96d`，分支`codex/hard5-q4-t3-2x2-20261005`。28文件101350bytes，package SHA为`20f525b94f95b9ebee8cd58e83000209212bb017407b798f88eb426353c62445`。Windows静态／source／which检查、64项自测、7份同worker全文预读／几何检查通过。
- 完整取回97文件、1,716,819,024bytes，每份大小与SHA一致。45个完整状态点／41个完整块及旧分母参考独立回放raw、Ru、Rd、history、U/J实际容差、旧前驱／初态／预测器／BC、连续d_before、计数与inner u返回残差。最大residual scaled误差5.2794e-17，history为4.1633e-15，raw为6.4269e-13；全部试算damage无越界、f=1，最大trial疲劳累积量alpha_bar=.487706<.5，历史提交0。
- 数值执行分析器SHA为`77acd3e59e612bcb2cca522992defec4c17cf0b2b9b10c80fe4e79dcdfd12e00`，保存在提交`52f96d4`。绘图补充SHA为`6b32e8eaf42ba4ea6b0299120f82d34e0399e917681acefdd96a57b884ef402a`，仅为全零首轮面板加说明、调整标题；只有decision PNG改变，CSV／JSON／判据未改。四图已目视并通过sidecar检查。独立数值／文稿复核见`analysis/independent_review.json`。

归档：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_s2uj_20261017_v1`。权威数据为`analysis/s2uj_analysis.json`与cases／completed_outers／contrasts／timing／phase_calls.csv。四图decision／fields／trajectory／inner_outer附README_analysis、figure_plan、同名sidecar、visual_qa和render_adjunct。仅将decision与fields PNG原样复制至Obsidian `attachments/S04/2026-10-17/`并嵌入结果下方，复制SHA／唯一basename解析记录见`obsidian_figure_receipt.json`；原始数据仍留项目归档。

## 决策与范围

本例保留fresh＋约束damage＋phase4e-6＋inner u1e-8＋joint4e-6／outer u1e-8。主要active变化来自J要求的继续耦合，inner u精度则影响最后严格Ru能否闭合。没有用场接近来替代残差合格，也不建议在不变的宽松inner u下单纯增加outer救场。

若继续细分，下一项最小干预是固定严格inner u／phase，再拆joint sum与outer u两个门；本轮未执行。结论限于一个FEM c1s2、旧历史、f=1，没有新PINN训练、c83／120周期、疲劳退化反馈、teacher／物理／唯一或全局极小、线性／指数多cycle误差结论。既有E003/E011/S2I/S2RA/S2DJ结果保留；空间／Carrara对齐仍不消除committed-f与FEM trial-f、联合Deep-Ritz与staggered/Picard差异。
