# C1 v4/r4 repaired sequence completed — 2026-10-16

**原流程和修复臂均已完成完整c1加载—卸载五子步，并各保存5次accepted历史推进。修复臂5/5满足提交前联合收敛，原流程5/5不满足同一严格条件。** 原流程按新r4准入完成五步回归；旧raw检查仍完整保留，s3仍未过，没有追认v3。

两臂从同一U=0恢复后的u/d/lower/history和原缓存预测器KK分别出发；recovery共34次phase调用，只初始化/reset一次。载荷为`.02999988,.05999988,.08999988,.11999988,0`，实际末步位移有原增量累加舍入`1.39e-17`。网格86,756节点/86,408原生Q4，2×2GP；E=1、nu=.3、平面应变、AT1/Amor、Gc=.01、ell=.01、alphaT=.5、p=2、eta=0；GP罚系数421875/13781.25。其余求解、材料、r4和预算均按协议。

严格判据使用**提交前的旧lower/旧accepted历史**：`C=max((Ru+Rd_feasible)/4e-6,Ru/1e-8)≤1`。Ru是自由位移残差L2，Rd是有界damage可行方向残差L2；不要求含约束反力的原始damage残差为零。以下为离线共同算子复算值，与native值的残差分量最大差不超过`1.05e-16`。

|子步 / U|原流程 C|修复 C|修复 Ru|修复可行 Rd|修复闭环数|修复 u/d 调用|
|---|---:|---:|---:|---:|---:|---:|
|s1 / 0.02999988|1036.22|0.165322|8.900e-16|6.613e-07|3|12/12|
|s2 / 0.05999988|21809.5|0.392168|1.879e-15|1.569e-06|20|90/63|
|s3 / 0.08999988|3847.19|0.887083|2.907e-15|3.548e-06|8|40/28|
|s4 / 0.11999988|10982.1|0.813816|3.819e-15|3.255e-06|7|38/25|
|s5 / 0|2.81637|2.0427e-06|2.043e-14|0.000e+00|0|3/4|

原流程outer为2/3/9/3/1，共93次u、490次phase调用；修复臂共183次u、132次phase调用。共同recovery另计。修复臂每步均在20闭环、250u/250phase上限内，调用数包含审计/提交保留开销；**s2恰用满20闭环**，没有证明后续周期也有预算余量。卸载s5闭环数0表示预测器/初次fresh检查后无需额外闭环，仍有3u/4phase调用。

每臂accepted版本逐步0→1→2→3→4→5；每一步恰有一份durable accepted提交。修复臂先通过旧历史/旧lower下的联合条件，再计算历史proposal、只读后审计并保存，之后才推进版本。源代码、文件IO自测、原生事件与相邻状态逐项对照共同支持这一结论；内部trial反复计算历史并不算accepted提交，不能把“一次提交”说成“历史函数只调用一次”。原流程也每步只提交一次，但按原cached规则接受，**一次提交本身不能保证联合收敛**。damage处于[0,1]且不低于前一步lower，固定边界及有效历史2:4均通过复核；channel1为原生未使用通道，另行保留/报告。

**r4不是把旧raw阈值调大。** 两侧各自raw对自身u的独立Q4/Amor回放仍要求`1e-10`；随后比较实际raw差是否处于解析位移输入响应界加两侧精度预算以内。u/d节点绝对最大差、proposed历史2:4归一化最大差仍≤`1e-10`，outer次数仍须完全一致。响应界是三角不等式一致性检查，不增加独立解等价证据。

|子步|旧 raw 归一化最大差|旧 raw 判据|候选自身算子误差|参考自身算子误差|raw差/响应总预算|r4|
|---|---:|---|---:|---:|---:|---|
|s1|7.59948e-14|通过|5.105e-14|8.050e-14|0.000379974|通过|
|s2|3.22631e-13|通过|4.003e-13|3.098e-13|0.00161315|通过|
|s3|5.01220e-10|**未过**|9.210e-13|1.274e-12|0.647025|通过|
|s4|2.41986e-12|通过|2.198e-12|2.299e-12|0.0119906|通过|
|s5|5.19097e-29|通过|2.803e-44|3.083e-44|2.59549e-19|通过|

**残差改善同时改变了解路径，不能写成场差消失。** 下表以本轮原流程为分母，原生GP/Jacobian权重计算`||修复−原流程||w/||原流程||w`；alpha指提交后的疲劳累积量alpha_bar，不是damage d。active在同一子步、最终u/d与旧accepted历史下计算；无插值或跨状态替代。

|子步|damage GP相对L2|active GP相对L2|active积分变化|累积历史 GP相对L2|节点damage最大差|
|---|---:|---:|---:|---:|---:|
|s1|0.269%|2.919%|-0.0322%|2.919%|0.0069087|
|s2|8.511%|79.410%|-24.4692%|66.416%|0.152633|
|s3|4.869%|24.552%|-0.1979%|51.842%|0.182757|
|s4|4.989%|16.502%|-0.2243%|37.720%|0.185808|
|s5|4.989%|不报告：近零分母|不报告：卸载近零|37.720%|0.185808|

第1步已有可见差异，第2步active场差跃升至79.41%，active积分减少24.47%；峰值积分只减少0.2243%，但active空间场仍差16.50%、damage场差4.99%。因此单一积分相近不能代表位置/形状接近。卸载两臂active绝对L2差仅`1.61e-28`，不报近零分母下的相对百分比。峰值及卸载累积历史加权均值由`.005204634846`变为`.004927082963`（−5.33%），空间相对L2差37.72%；卸载修复damage不再增加，原流程仍增加最多`.00097509`。

**本轮的范围是一个合成c1的数值/状态转换检验。** 两臂所有GP、全部五步均`f=1`；峰值max(alpha_bar)为原流程`.39333456`、修复`.42159253`，尚未达到alphaT=.5。所以验证了历史映射/单次accepted推进和不可逆lower传播，**尚未检验f<1后的疲劳退化反馈**。该复合修复涉及约束damage、位移再平衡与fresh停机，不能把场差单独归因于历史提交，更不能证明唯一解/全局能量极小或更接近物理真值。当前c1结果不能给出多cycle误差线性/指数/突变规律，亦未新增c83或120周期轨迹、FEM/PIDL teacher资格。冻结E003/E011生产结论不变；PIDL committed-f与FEM trial-f、联合Deep-Ritz与staggered/Picard差异仍在。

## 执行与取回

实际producer为CITPC12 `AD\xw436`，R2025b CPU单线程。源码`67942510c38c420c9ebc343e88b781a018cd1c7b`，branch`codex/hard5-q4-t3-2x2-20261005`，launch时工作区干净。远端`C:\Users\xw436\jobs\E011_C1_20261016_v4_r1`；WMI19240/launcher45920/worker9464，UTC10:37:29.1058548Z启动，UTC10:47:10.2346047Z观察到正常终态和无本轮进程。16文件80,184bytes、8普通输入副本156,839,354bytes的完整SHA/大小均一致；准确manifest SHA`acf8008f10ad6a08e141bdfebeb593e6f6187886b45dca071fdf415bf6e80251`。Windows14文件静态检查、source/which/MEX身份、34自测、同进程8输入全文/几何与5参考own-u raw检查均通过，原流程五步回归后才启动修复臂。无重复启动、预算上调或其他进程干扰。

最初v4在ISCL静态提示处停止，未做原生场计算；r1仅将`numel(sys.MAT_CHAR)==1`等价改为`isscalar(sys.MAT_CHAR)`并换新目录/版本元数据，求解规则不变，已有独立差异审查。旧v4的32文件156,930,140bytes取回核验并保留。[静态记录](c1_commit_v4_static_r1_20261016.md)。按10月16日新规则与用户本轮直接执行授权推进r1，没有再请求普通SSH/代码操作审批。

新r1全部69文件1,353,725,620bytes已取回，逐份SHA/大小一致；原始数据不进Git。文件见：

- Run: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_c1_commit_20261016_v4_r1`
- `retrieval_verification.json`、`launch_receipt.json`、`upload_verification.json`、`latest_monitor.json`
- `analysis/c1_commit_analysis.json`：输入/代码SHA、10个提交、终态与离线复核。
- `analysis/commit_trace.csv`：每步残差、版本、调用数和旧raw结果。
- `analysis/paired_reductions.json`、`supplementary_reductions.json`：场差、raw新旧口径与GP极值。
- `analysis/c1_commit_decision.png`及同stem说明：已目视检查，sidecar校验通过。

## 决定

Claim verdict: supports the bounded five-substep repaired numerical/accepted-state claim; does not establish field alignment or physical validity. Research disposition: advance the mechanism diagnostic, do not promote to a qualified teacher or launch a long trajectory. Component progress: original five-state admission reproduced under prospectively approvedr4, repaired freshjoint5/5, versions/history10/10, finite/bounds/budget passed. Binding limitation: f remains1, and branch sensitivity is already material at c1s2 (20blocks). Smallest next discriminator: use saved s1/s2 states to separate incoming irreversible-state propagation from local solver-control sensitivity at the same predecessor; a new native arm is unexecuted. Do not infer unique equilibrium from smaller residuals or extend this one-cycle result to c83 onset. Local independent review of the retrieved archive is recorded in `analysis/independent_review.json` (completed and passed).

Local independent archive/numerical and final-document reviews passed. Final analysis change is a ylabel clarification only; its exact source SHA is recorded in the analysis JSON. [Compact evidence manifest](c1_commit_v4_r1_manifest_20261016.json) records immutable artifact identities and bounded verdicts; the raw payload remains in the local archive.


2026-10-16 scope clarification from [S2X](s2_factorial_v1_result_20261016.md): the earlier all-GP f=1 observation refers to the five accepted endpoints, not every internal Newton trial. New exact c1s2 restart reproduces those endpoints but measures original-solver trialf as low as2.162e-5 with temporary trialalpha_bar214.566; repaired trials stayf1. No accepted-state values or old raw verdict changed. Persistent fatigue-degradation feedback remains untested by the one-c1 endpoint result; internal trial-f influence is now observed but not causally isolated.
