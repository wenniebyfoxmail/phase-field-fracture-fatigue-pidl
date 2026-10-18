---
storyline_id: S04
experiment_id: S04-E030
protocol_revision: v1-fixed-physical-UV0-damage-isolation-20261018
status: preparation
---
# E030：固定自身零步物理UV，隔离damage学习

目的：判别E029在物理UV/raw不漂移时，原可微damage表示与相同优化设置能否改善实际FEM active场及damage增长拟合。当前D5，沿用既有D1复用结论；独立新试验，旧E027/28/29及原判据完整保留。证据域synthetic、C2单个已暴露c20s4/horizon0/seed1，不是物理演化或泛化检验。

## 先有证据，后选择干预

E029第k行LA是更新前；完整原生GP/Z active项不随采样变化，所以下一行LA对应本次更新后的模型，step200由保存终态补齐。工具`tools/analyze_s04_e029_update_timing.py`将全部200次对齐，并与0/10/50/100/200里程碑逐一匹配1e-10：196/200个更新后状态劣于自身零步，前150步全劣；第一步误差.772727→74.3109，后段也多次突跳。故不只是最后一步异常，但未保存每步UV/d场、参数实际位移或Adam更新范数，不能断言每次突跳都来自UV或Adam实际步过大。

已存10/50/100/200 UV误差均高于零步；终态代数交换新UV+零步d为2.98721、零步UV+新d为.892955，原零步.772727，支持优先隔离UV/raw。补充零步UV+精确FEM d的代数误差为.611447（global d/zone d误差0），说明固定当前UV仍有active方向改善空间，但这是场代入参照，不是NN表示上界、物理接受解或训练效果。完整对齐证据在parent_timing.json及本地preparation；不以最低trace或临时checkpoint改写E029。

只选择**固定物理UV0**这一因素，不同时限制真实参数步、不改Adam/学习率/目标/梯度控制或damage映射。现有证据不足以校准真实步限；本次记录实际参数步范数用于观察，绝不裁剪或据此重试。

## 唯一新干预与相同起点

起点仍为精确E027 S1500，9009653B、SHA ef2be905167b6e26be3de5778a42e5043ddebd96610e06b1f39f4106ffca8f0b。模型26-key/float64/8×400/TrainableReLU不变；同一空Adam(lr1e-4, betas.9/.999, eps1e-8, wd0)，CPU采样generator seed1、每步2048global+2048Z。

先复放原S及E029 smooth0。把**原S1500的物理u/v**保存成冻结buffer，在所有新场中返回同一物理UV；不是冻结两个输出头就假定共享层不影响UV，也不是使用FEM目标UV。模型仍输出raw damage，经原样复用E029 BoundedIncrement、同一raw_origin/logitseed/EPS1e-4/真实c20s3 lower与预裂纹得到d。所有地图buffer及UVbuffer不可变并序列化。新fixedUV0必须与旧smooth0的全量指标匹配1e-10，节点UV逐位相同，初始d扰动仍只是原声明EPS，不新重锚。

目标原样复用E028/E029 `L_U+L_D+w_A L_active`、wA=stopgrad(min(1,.25||grad Lsup||/||grad LA||))，机械权重0。固定UV使L_U在参数方向为常数、其梯度为0；同一控制公式会自然变成以damage监督梯度决定active权重，这是固定UV的结果，不另调控制器。没有STE、target作lower、运行投影、额外可训练参数或激活/权重扫描。NN共享参数可以变，物理UV及其原生Q4梯度/raw驱动必须不变。

## 200步及判读

仅一个新R，200步；冻结E029联合训练作为隔离对照，不重跑。**唯一探索主读数：R200/本次fixedUV0的Z active相对L2 <1−1e-8**，分母<=1e-12为NA。沿用相同方向容差，不预设未校准的大百分比；精确d代入.611447给出可改善空间，无独立重复或CI。

必须同时报告全部global/Z u/v/UV/d/raw/active、force/reaction、节点/GP bounds/healing/precrack；4115目标增长节点mass加权d误差及相对零步的实际d变化（排除EPS seed），不能以“UV没退化”或仅loss降低称成功。对照须含原initial/S/C、E028_R、E029_R、新fixedUV0和R200。固定UV即使改善damage/active也只支持组件隔离，不宣称已解决联合训练、正确UV或完整物理状态。

0/10/50/100/200保存完整分量、真实导数比例、UV逐位与raw不变检查；0/50/200保存NNraw/相对origin/真实dd/draw及物理场。每步保存更新前LU/LD/LA/梯度范数及角度，另存**实际参数更新L2/相对L2、更新后完整active误差**，直接对齐更新时序。终态保存MLP/Adam/RNG/映射及UVbuffer，检查lower/fatigue/buffer不变；不更新history或求FEM。

输出同色标完整u/v/d/raw/active及有符号误差、全部更新后active曲线，原生Q4加权均值；固定几何近尖端窗口仅辅助显示、不替代原GP4 Z打分。文件大小/SHA、CPU数组重算、五图目视与必要独立焦点核验后才交接实际结论。

## 授权、成本与首停

直接人方既有继续最小修复授权保持；HQ本轮明确选择D5并授权一个<=.5GPU小时新小试，沿本线唯一owner，不新开HQ。此前三Run receipt合计.95643GPU小时，本次最多.5后累计<=1.45643，仍不越原2GPU小时总限。

一张允许GPU、实际UUID，初始free>=20GiB、allocator<=free−1GiB并留1GiBheadroom、RSS32GiB、输出2GiB；**1800秒含准入/预检/训练/评估/保存**，外部1790秒TERM+5秒KILL。3次实际backward无step成本预检，1.5×200步估计+300秒保存余量必须装入限额。不占用/杀别人的进程，不落大盘以外。

精确模型/数据/旧输出/clean source/host/UUID/零步复放不符、UV改变或raw变化>1e-12、物理界/预裂纹>1e-10、非有限值/梯度/参数、全部变量真实damage导数数值归零、时间/显存/RSS/存储触限，整次立即停止。新Run失败不重试、不恢复、不替代权重或扩预算；固定200步，不挑低loss中间态救主判据。

若主读数改善且damage代价可解释，保留组件进展、由HQ选择联合更新的下一必要设计；若未改善，冻结结果并区分damage拟合能力与固定UV参照局限，不再把同一联合/固定设置重复计算。
