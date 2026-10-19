# 原owner W0/W25固定200步结果复用核验（2026-10-19）

目标连续性：原问题是gamma单因素能否改善同一FEM状态的场一致性；本轮按用户指令continue，
只复用原owner已完成的各200步，不重跑、不改原准则，不执行补充FP64模型方案。
D4（本轮完成）：既有端点身份/评分核验与实际场展示；原D3补充高精度方案继续暂缓。

结论：**W0与历史C在update0/200的u/v/d逐位相同；W25综合误差高31.15698%，
u/v/d及raw/active驱动误差均增大。** W25负damage与GP回退减轻，最大节点回退却增加64.58074%。
当前已见合成c1s1、固定200步下，不选W25作为更接近FEM的设置；保留其局部可行性收益，
不宣称gamma1已满足硬约束、收敛、真实物理或泛化。

## 数据与实际核验

Run `pf_s04e011_wpair_fix_8edc762_20261018T210743Z`，producer `8edc762a99bacfa6825ed413a148fbcccd09a921`，原owner唯一产物目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_fix_8edc762_20261018T210743Z`。本对话核验输出：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/reuse_wpair_result_20261019`。

- 29份本地compact文件逐文件bytes/SHA256通过；5,257,996bytes评分压缩包SHA与原独立复核记录一致。
- 原FEM文件、native-Q4算子及全部15个已保存分析输出身份核验通过，未生成替代场数组。
- 两臂完成receipt为各200/共400更新，trace索引各0..199；新增history/FEM均0。
- 86756节点/86408 Q4的顺序、同一初始damage/own history、251个硬线节点均吻合。
  W0与C的update0/200 u/v/d逐位相同；W0/W25初态及首步字段也逐位相同。
- 本轮仅CPU从6组保存节点场重算J、各分量、raw/active、负damage和回退，与原CSV最大绝对差
  2.16840434497e-19。沿用原评分的float64积分后处理，不是FP64网络/能量重放。
- checkpoint/完整梯度向量、producer raw/active/strain GP原数组仍远端；本地是已核验无损节点子集。
  不声称全量payload已取回或重新验证远端NN权重。
- 复用原owner已完成的独立实测复核，不重复创建审核。该复核已覆盖六端点重算、九图、
  固定history语义及原点/活动Eh预检；本轮进一步复核本地数组/文件与新增显示图。

原参考：`pf_s04e011_mcs_20261017_v1/retrieved/inputs/c0001_s001_post_commit.mat`，
同c1s1/post_commit、U=.02999988，FEM只用于封存后的离线评分。
J = sqrt(sum_i m_i[((u-uF)/.12)^2+((v-vF)/.12)^2+(d-dF)^2]/(3 sum_i m_i))。
各分量是正native-Q4 lumped节点质量加权RMS，u/v除以固定Uref=.12，
**不是相对FEM向量范数误差，也不是除以本次U=.03**；raw/active列另按GP Jacobian权重计算相对L2。

| 同一FEM误差，固定200步 | C = W0 | W25 | W25增幅 |
|---|---:|---:|---:|
| 综合J | 0.001404643135 | 0.001842287484 | 31.1570% |
| u RMS/.12 | 0.001618555246 | 0.001815237103 | 12.1517% |
| v RMS/.12 | 0.001752076084 | 0.002532330886 | 44.5332% |
| damage RMS | 0.0004791401911 | 0.0006886828445 | 43.7331% |
| raw驱动相对L2 | 0.3349362186 | 0.4010552082 | 19.7408% |
| active驱动相对L2 | 0.2461717918 | 0.3337495785 | 35.5759% |


## 实际字段与误差

![FEM/C/W0/W25原字段](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_fix_8edc762_20261018T210743Z/comparison/FEM_C_W0_W25_fields.png)

**看到了什么**：同一前区、同行统一色标；C与W0重合，W25在u/v及裂尖damage分布上偏离FEM更多。
**因此**：保留C/W0，不把更强不可逆惩罚当作场一致性改善。图为前区，表为全域，二者不混作同一统计范围。

![相对FEM的有符号误差](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_wpair_fix_8edc762_20261018T210743Z/comparison/C_W0_W25_signed_errors.png)

**看到了什么**：W25的位移误差幅度和damage局部条带误差较C/W0增加。
**因此**：三通道评分退化与实际字段相符；同色标图没有借逐图归一化掩盖差异。

## 负damage与回退

回退定义max(d0-d,0)，d0是各臂相同、固定的FEM U0初始场/own lower，
不是加载后FEM参考解，也不是一次新的history提交。GP为原生2×2积分点；面积分母为**整个物理域**。
面积统计epsilon=np.finfo(float32).eps：负d为d_GP<-epsilon；正初始damage回退要求
h_GP>epsilon且h_GP-d_GP>epsilon，不能把这些面积当成损伤区内百分比。

| 物理场诊断 | C = W0 | W25 |
|---|---:|---:|
| 节点最小damage | -0.000163859615 | -5.544519809e-05 |
| GP最小damage | -0.0001575932087 | -5.253869349e-05 |
| 最大节点回退 | 0.001865923405 | 0.003070950508 |
| 最大GP回退 | 0.0005541627659 | 0.0001036526135 |
| 负damage GP加权面积/全域 | 97.70239% | 74.18591% |
| 正初始damage区回退GP加权面积/全域 | 0.0340525% | 0.02931224% |


![负damage与回退空间图](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/reuse_wpair_result_20261019/negative_damage_and_retreat.png)

**看到了什么**：W25负damage浅化，但最坏节点回退更深；两个最坏回退点位于不同位置。
**因此**：GP罚项改善不保证每个节点不可逆。色块是每个Q4单元四节点违背量的最大值，
仅供显示孤立极值；面积百分比来自GP权重，绝非色块/像素面积。

W0最大回退坐标(-.259883103,.001154196)，d0 .888352692→.886486769；
W25最大回退坐标(.002487217,.000256832)，d0 .413942337→.410871387。
这些是节点极值，不能用更小GP回退来替代。两臂均有负damage和回退，未满足严格物理界限。

## 当前判断与范围

已有两臂的gamma总效应由W25−W0识别，C只是额外历史回放对照，未拿C代替缺失W0。
同一见过的合成状态、同一初始化和固定200步下，W25对原FEM场准则为negative；
不能扩展成完整疲劳轨迹、任意gamma或所有状态的结论。
本轮没有新producer、NN forward、autograd、训练、FEM或补充FP64核验，也未激活硬下界/上界。
用户本轮要求的比较已完成。若后续调整方法，应针对位移/局部驱动误差与可行性分别设计，
不自动执行原owner建议的hard-map检查或任何新实验。

来源：[原owner结果与限制](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/S04-E011/runs/loss_weight_fixed200_result_20261018.md)、
[原独立实测复核](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/S04-E011/runs/loss_weight_fixed200_evidence_review_20261018.json)、[本轮数组/哈希核验](loss_weight_fixed200_reuse_verification_20261019.json)、
[本轮六行评分](loss_weight_fixed200_reuse_metrics_20261019.csv)。
