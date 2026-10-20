# C27–A25：旧15组＋新四组，完整19组结果（2026-10-20）

## 目的

完成固定alpha输出校正比较，判断分别缩放整体/中心化空间分量是否超过简单方法；同时如实保留历史响应相对当前响应的预测价值。这是已暴露公开开发组的成组比较，不是SCB物理实验或道路验证。

## 本轮

R005仅完成四个缺失外层组，304预测器＋152残差化＝456求解；旧R002十五组不重算。GPUServer8、1CPU线程、0GPU；原180文件完整身份核验和2418个原生帧finite/schema核验在首个solve前完成。旧15组82项来源绑定不变。源码 `db62655a7d69aa2dafee80e466d1ae73d23ce19a`，包 `261e76cf1cb4cba35056b37f0d741a8dacb84d03488ce317188fa7541cba656a`，授权HQ_DELEGATED/human_approved=false。新根不覆盖R001–R004。

计算生命周期344.416秒，峰值采样合并HWM 892.22MiB；三个实际PID已退出，三层回调封条和stderr核验通过。取回1241文件，gzip214075154字节，SHA `ca6a75cd2a0882e5147f52488fd38227327c7aa30c7231758f2925ee43ebe6ae`，全文件大小/哈希逐项核验通过。

本地仅以保存输出合并：19组、1144起点、H10/H40、两通道、2288外层行/16016臂评分、41184内层行/1853280候选评分、1444预测器＋722残差化＝2166个保留完整求解。16016原生评分重算最大差7.10543e-15，722套模型来源、38个选择单元核对通过；内层保存评分的聚合差0。合并耗时12.021秒，stderr0；未新增拟合或原始输入读取。

## 结论

**预先规定的主指标 C27−A25 = 0，38/38单元均为0。** U/C/A所有单元都选(1,1)，三个选择器与完整HISTORY预测完全一致。因此本轮不支持“双权重独立校准有额外价值”；不继续以更多alpha/网格/权重搜索挽救该主张。

按组和H等权的原生平衡归一化MAE（越低越好）：

| 方法 | 平均损失 |
|---|---:|
| CURRENT | 0.951101720 |
| HISTORY | 0.886550986 |
| GLOBAL_ONLY | 0.903473232 |
| SPATIAL_ONLY | 0.934686001 |
| SELECT_U | 0.886550986 |
| SELECT_C | 0.886550986 |
| SELECT_A | 0.886550986 |

**历史响应相对当前响应平均误差下降6.78694%**；H10下降2.95910%，H40下降10.78446%，两通道full/band平均均改善。34/38组×H单元、16/19组平均改善。逐组删一后的平均绝对改善仍在0.054456–0.068553，仅作描述敏感性，不作独立样本统计推断。旧15组均值改善5.3614%，新四组13.1303%；补齐后的数值不是只用新四组计算。

不利单元全部保留：

- C_0Deg_20%_#1, H40：HISTORY−CURRENT = +0.011474。
- C_30Deg_20%_#2, H10：HISTORY−CURRENT = +0.005840。
- C_30Deg_20%_#2, H40：HISTORY−CURRENT = +0.009122。
- C_30Deg_20%_#3, H40：HISTORY−CURRENT = +0.011293。

C30六单元HISTORY只比CURRENT平均下降0.2777%；固定SPATIAL_ONLY在这六单元中4/6优于HISTORY，6/6优于CURRENT，且全19组SPATIAL_ONLY在38/38单元优于CURRENT（总均值改善1.7260%）。HISTORY全19总体优于SPATIAL_ONLY，但不是每个条件都更好，不能将整体均值写成普遍优势。

## 图与边界

完整主指标热图、七方法全组×H曲线、预定义原生场失败视图均已生成并逐图视检，附同名说明。所有主指标并列时，第三图按预定义字典序选C_0Deg_15%_#1/H10/case64；它不是“历史比当前最差”的例子。新增04图仅作读数后保存标量诊断，直接展示四个历史不利单元，不改主指标或筛选数据。

组标签不等于已确认独立物理试件；H是发布序列步数，不冒称真实疲劳cycle。无显著性/新留出确认/物理因果记忆/输入可识别性/SCB或道路泛化结论。BRIDGE-PS-R003的旧警告违约、C27-R003的语法停止、R004启动前停止均保持原貌，没有被本轮成功追认。下一路线继续已有SCB加载匹配与独立裂长参考准备；已有数据缺口仍然存在，不再增加本数据集的校准搜索。

## 成本、复核与归档

已知累计producer墙钟1549.791秒（R002+R003+R005），另有R004至少504.925秒准备/传输到停止记录；旧连接/准备/取回未完整计时不填虚构总数。2166是保留完整求解数，不包含R002被中断未成组尾段的额外尝试。详见cost_ledger.json。本轮总1800秒从首次准备计时，producer600/取回读数预留180均未放宽；继续使用原更严1536MiB总存储、700MiB归档限制，低于此次新4GiB许可。

独立聚焦实现报告：[focused_review.md](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/preparations/OUTPUT-CALIBRATION-20261020-R005/focused_review.md)。本轮科学结果复核：[evidence_review.md](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-OUTPUT-CALIBRATION-C27A25-20261020-R005/evidence_review.md)。原始回执、全哈希库存、full19_assembly、full19_readout.json、cost_ledger.json均在[本地case](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-OUTPUT-CALIBRATION-C27A25-20261020-R005)；原始数据没有上传或补传。
