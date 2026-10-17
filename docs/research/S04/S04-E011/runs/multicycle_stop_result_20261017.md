### 2026-10-17 跨cycle判别完成：瓶颈随加载阶段和裂纹位置变化

**damage更新后的位移再平衡仍是峰值阶段的主要瓶颈，但不能笼统推广到所有子步。** 从每个原始s1/s3前驱独立重启，固定Q4／2×2GP、约束damage、fresh、inner u=1e-8／d=4e-6，历史不提交。另复现旧c1共同初态锚点；它与自然c1重启单列。10自然状态中7个达标，3个晚期峰值耗尽20轮预算。

S为总残差门：4e-4／4e-6；V为outer-u门：4e-4／1e-8。下面是同一严格原生路径派生的四种停机政策，**不是40次独立运行**；“—”表示20轮内未观察到通过。

|cycle|第2步 S0V0/S1V0/S0V1/S1V1 首停outer|峰值同序首停outer|峰值严格末态|
|---|---|---|---|
|1|1/19/19/19|1/9/9/9|通过（outer9）|
|20|1/1/1/1|1/18/18/18|通过（outer18）|
|60|1/1/1/1|1/—/—/—|20轮未过，Ru=0.000134|
|80|1/1/1/1|1/—/—/—|20轮未过，Ru=0.00014|
|83|1/1/1/1|1/—/—/—|20轮未过，Ru=0.000331|

所有129个完整耦合块都先将Ru降至1e-8内，damage求解后Rd仍≤4e-6；103个自然状态未达标块却重新出现过大的Ru。因此本轮直接支持“damage改动重新破坏机械平衡”，没有phase-inner失败。c1s2／c1峰值／c20峰值的两单独严格门仍选同一终点；晚期三峰值两门都未过，只能说共同拦截当前不平衡，不能断言将来同点通过或删去某门。

位置也改变：c1s2的active变化平方98.43%在左侧x≤0；c20峰值只剩0.188%在左侧，c60／80／83峰值几乎全在x>0。后三者末态机械残差最大节点约x=.287／.442／.476，残差热点向右移动。后期f已低至约.002，不再是早期f=1范围。历史单次映射误差仅约1e-12，本次没有发现历史身份的大错。

**55.90%仍是两个FEM场的变化，不是FEM–PIDL误差缩小率。** 以下才是与同一最新paired-Q4 PIDL checkpoint的实际场差：全域GP/Jacobian加权active L2／固定PIDL范数，越小越接近；精确u/d/raw/g、积分与相关系数另见数据表。

|cycle|第2步：原FEM→本轮严格FEM|峰值：原FEM→本轮严格末态|
|---|---|---|
|1|22.74%→82.42%|24.92%→22.65%|
|20|50.93%→50.93%|47.24%→39.63%|
|60|72.78%→72.78%|68.62%→55.18%（未达标）|
|80|72.36%→72.36%|58.79%→40.97%（未达标）|
|83|57.25%→57.25%|46.25%→71.26%（未达标）|

原峰值场差随c1→20→60→80→83为24.92%→47.24%→68.62%→58.79%→46.25%，并非单调增长；仅这5个采样cycle不能判定完整误差规律。这说明更充分的FEM平衡既可能接近，也可能远离PIDL，不能按两者接近程度挑FEM。后三个峰值仅诊断末态，不能作为收敛参照。此前CR-v3从已迭代峰值继续再平衡的c83通过结果仍保留（与PIDL差104.16%）；它和本轮从s3重新加载的起点／已有计算量不同，不矛盾。所有点均非一条连续修复演化，不据此拟合线性／指数误差累积。

**PIDL的loss平台不能视为已经求好。** 原600/600加载步均按相对loss平台停止，无一耗尽10000轮；本轮10点仍有共同自由位移残差.00314–.00572，且大量负damage，c83峰值最低−.010184、最高1.000854，最大不可逆下界违背.004239。3点通过原目标分量复现，参数梯度范数.848／4.241／2.688；其24次预设独立梯度方向试探全部升loss。故不能据平台或这组未下降步长证明驻点，更不能把优化器停滞与参数化限制完全分开。其余7点小罚能未过既定复现阈值，保留为不确定，不放宽门槛。独立审查还发现nodal-d梯度导出缓存污染，该指标已剔除；网络参数梯度／试探、共同位移残差及场比较不受此问题影响。

下一步以已联合闭合的完整c1修复流程作早期数值参照，保留B0的Smooth Boundary参数化与直接约束Q4 damage路线；先把PIDL位移再平衡、damage可行性和loss停机分开检查，再决定优化器调整。后期先形成一致历史的收敛轨迹，不能将局部点拼成120周期teacher。本轮没有新PIDL训练，committed-f／trial-f与联合Deep-Ritz／staggered/Picard差异仍在。

来源：S04-E011 / MCS `0a0691e`，223文件5.262GB全部核验；PIDL只读CPU run `348be4b`，21文件51.7MB核验；分析`31730a3f`。完整结论、独立复核及表见[结果记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/multicycle_stop_result_20261017.md)。

[mcs_control_reviewed.png](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/mcs_control_reviewed.png)

来源同上：真实完整outer与四政策首停点；灰格为≤20未观测，橙柱为未达标末态。场自变化分母为各自首块，与旧55.90%的分母不同。

[fem_pidl_comparison.png](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/fem_pidl_comparison.png)

来源同上：同cycle／子步下原FEM、局部FEM与不变PIDL，×为未达标；积分接近不等于场接近，连线仅原PIDL抽样趋势。

[fem_pidl_maps.png](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/fem_pidl_maps.png)

来源同上：参考／PIDL／有符号场差；晚期使用原FEM作参照，本轮严格末态另列且标MISS；同一行共用色标，不跨cycle用颜色比较幅值。

[pidl_plateau_reviewed.png](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/pidl_plateau_reviewed.png)

来源同上：原loss停机、共同位移残差、仅3个通过目标复现状态的参数梯度及其最小loss上升量；另7点不作原目标归因。不是收敛证明。

Execution and evidence records: [compact manifest](multicycle_stop_manifest_20261017.json), /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1/analysis_v2/independent_review.json. Raw outputs remain in the local archive; no PIDL training or history update. CodeReady31730a3f; actual producers0a0691e/348be4b; render-only31730a3f.
