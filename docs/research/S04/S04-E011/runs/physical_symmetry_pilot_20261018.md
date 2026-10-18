# S04-E011：物理位移软约束 200 步双臂结果（2026-10-18）

完成 control / physical-u/v 各200次RPROP更新。候选对同预算control有小幅分量收益，但没有改善原始模型的主指标，不能称为上翘修复。没有追加运行。

|相对原FEM，同一原生Q4 GP4算子|原始模型|control 200|候选200|候选 vs control|
|---|---:|---:|---:|---:|
|active 相对L2|25.3202%|25.7181%|25.4570%|降低1.0153%|
|raw 相对L2|41.2138%|40.5331%|40.9380%|增加0.9989%|
|位移质量RMS/Uref|0.00162809|0.00172393|0.00169639|降低1.5974%|
|损伤质量RMS|0.00421266|0.00424659|0.00424529|降低0.0307%|

上表改善百分数以control数值为分母，并非百分点。active绝对下降0.2611个百分点；候选仍高于原始模型0.1368个百分点。原始模型及两臂使用相同已保存FEM c1s2作为数值参照，未宣称物理teacher。位移误差以固定Uref=.12归一化，不是以FEM位移范数归一化。

损伤图和剖面基本重合，前伸支撑位置在d=.25/.5/.75三阈值上两臂均未改变。x=.01处中心化宽度由.0065140降至.0064359（FEM .0038823），仍明显偏宽；x=.02处FEM损伤为零，候选正损伤尾部质量却由2.1944e-5升至2.6368e-5。该弱尾部质心从.000795升至.001240，不能作为裂尖事件。没有明确的上翘形态修复。

同一展示探针支持内，候选u/v/d/active镜像RMS均略高于control；这是辅助局部重建读数，与训练探针支持不同，不是全域物理判据。不能用“更对称”解释本次小幅active改善。

原物理总能量：control .0067646881，候选 .0067651394；自由位移力范数control .00324552，候选 .00325734，未改善。候选最小d=-.00042865，最大.993326，节点回退max .0110732（control .0113955）；仍有原软罚允许的越界/回退，不满足严格box/硬不可逆。这些是固定PIDL前史下的端点读数，FEM不能用PIDL历史下界的回退量评价可行性。

## 执行与来源

- Run `pf_s04e011_psym_f3f9742_20261018T100235Z`，精确生产/分析代码 `f3f974283636e0a184b162261efa3cb4b611521f`，工作树执行前干净；基于`ad749c8`原模型。
- Taobo GPUServer8 GPU0，worker PID2584496，watchdog PID2584495，2026-10-18 10:08:30—10:08:56 UTC，退出0。总GPU计算墙时26.3194秒（.00731小时），峰值显存2879602176 bytes。总上限3590+5秒。各200更新，历史提交0，新FEM0。
- 原模型trained_1NN_2.pt，输入history checkpoint_step_1.pt；两臂同theta0、同固定history/committed-f、各自fresh RPROP。一次初态梯度标定lambda=.12718020965483381，lambda_d=0，位移尺度.12；不属于原优化器状态的逐步续跑。
- 原网格86756节点/86408Q4；原生float64同一Q4 GP4算子复算四组场。统计为全网格；展示局部x[-.04,.08], y±.04，不能直接用图像面积推全域指标。
- 远端工作目录 `/mnt/data2/drtao/wennie/pf_s04e011_psym_f3f9742_20261018T100235Z`；归档 `/mnt/data2/drtao/pidl_archives/pf_s04e011_psym_f3f9742_20261018T100235Z/output`。完整网络/GP输出保留远端。
- 本地`retrieved/output`为无模型运算的字段子集提取（u/v/d、坐标/连接/hist_alpha及JSON日志）。`readout_derivation.json`连接源SHA与提取SHA，原完整manifest保留；压缩包SHA49153fb3cd901c508a3922c01136e7ba05713e6b1fe4e07604477fa643b3bec3，全12项提取文件逐项核验。
- FEM固定输入与既有Q4算子大小/SHA均按analysis_inputs.json重核。详见recipe.json、approval_receipt.json、code_ready_review.json、launch_receipt.json、retrieved/output/receipt.json、terminal.json、complete.json及analysis/*.csv/json。
- 16确定性检查和独立代码复审在执行前完成；结果复审另存。这些检查不替代科研结果。

## 图件与边界

![FEM/control/候选完整场图](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_psym_f3f9742_20261018T100235Z/analysis/FEM_control_candidate_fields.png)

行依次u/Uref、去边界提升后的v/Uref、d、raw、active；前三列FEM/control/候选，后两列各自减FEM。同一行物理场共色标，两误差图共对称色标。native GP统计与图中局部插值导数支持不同，不能从颜色反推主指标。

![损伤剖面](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_psym_f3f9742_20261018T100235Z/analysis/damage_profiles.png)

x=0/.01/.02，y±.04；候选绿色、control橙色、FEM蓝色。宽度是正损伤质量的中心化二阶矩，不是机械裂纹开口。

本次只有一个既有保存状态、一个seed、两个等步数臂；尚无连续历史演化或新FEM。没有严格对称要求，也没有增加damage直接对称罚。小幅active收益同时伴随raw、力残差及弱尾部退化；保留候选为已测的小幅混合结果，不替换原始模型，不扩展完整轨迹。
