# 公开来源诊断：划分与代码合同 r1

2026-10-09。补充r0协议的实现选择；无模型结果，旧草案保留。状态PREPARED_NOT_RUN_READY。身份仍为HQ独立研究准备，不新建正式实验登记；不允许据本文启动训练。

## 数据与角色

METU用既有458行/392候选组清单，按SHA256('20261009:'+group_id)升序排列（相同hash按组名），前274组train、后59组validation、最后59组internal_test。组比例来自70/15/15最大余数分配。角色不依据前景比例、图像内容或模型结果平衡。具体图像数由脚本输出，不反复抽seed找好分布。validation仅选checkpoint；r0称“校准”的15%在本轮正式命名validation，不做温度校准。

这是有限组约束的设计划分；候选组不等于独立场址，不承诺无残余泄漏。METU原图EXIF解释、mask>=128与r0一致；1/250敏感性只在最终评价追加，不影响split/checkpoint。BuildCrack全部358张固定external_diagnostic；不用于训练、适配、早停、模型选择、阈值调整。输出原图级结果；3张空参考单列，355作者非空参考的ΔAURC保持唯一主比较。

发现新的身份冲突必须在训练前保守合并并显式升版，不能继续用已无效清单。不能把无跨库匹配当作独立性PASS。

## 固定最小分割器（尚未实现）

一个随机初始化U-Net，无预训练、无dropout、无batchnorm。编码通道16/32/64/128，瓶颈256；每层两个3×3、padding1卷积，后接GroupNorm(8组)和ReLU；卷积bias=False。下采样2×2maxpool共4次。解码使用bilinear interpolate(scale2,align_corners=False)，与对应skip拼接，再两次卷积/GN/ReLU，输出通道128/64/32/16。最后1×1卷积16→1、bias=True。卷积Kaiming normal fan_in/relu，bias0，GN weight1/bias0；seed20261009。输出logits；推理时sigmoid。若库无法复现实装，先修合同/审查，不换架构。

## 训练数据与损失

RGB float32 /255，不作按来源归一化或自动增强。原分辨率随机448×448 crop，每张train原图每epoch恰好4个crop，每次先均匀选合法左上角，采样有放回；小图只在右/下edge-pad，参考padding像素不参与loss。保留含背景的crop，不使用标签导向采样或前景平衡。所有crop位置由独立numpy Generator(20261009)按epoch、stem排序、crop索引顺序生成后再用同一generator打乱，workers0；一个epoch的配方完全固定。输入与标签一起裁剪，不增强、不变形。

batch4，drop_last=False；float32，不AMP。Adam(lr1e-3,betas0.9/0.999,eps1e-8,weight_decay0)，无scheduler。loss每crop=0.5×有效像素平均BCEWithLogits +0.5×[1-(2sum(p*y)+1)/(sum(p)+sum(y)+1)]，batch内crop等权平均。空crop使用同式；不得改成忽略负crop。每个参数更新零梯度、反传、step；非有限值立即停，无自动重试。

## 原始尺寸推理与重建

448窗口、224步长，横纵各覆盖到最后一个合法起点；当规则步长未到边时额外追加length-448。小于448的维度只向右/下edge-pad。模型eval、无梯度。每tile先sigmoid，再对重叠原图像素等权平均概率；padding不参与重建。先重建再以p>=0.5二值化，禁止tile先二值化、取最大、缩放标签或图像。有效输出须原图H×W、全有限、每像素覆盖至少一次且概率在[0,1]。

`reconstruction_reference.py`是纯NumPy规范参考，不是训练runner；后续torch实现必须对照其覆盖、边界和概率融合。METU已按EXIF纠正原图，不能在输出时再次旋转；BuildCrack448图只有1tile。

## Checkpoint、预算与唯一最终评价

每个完整epoch后，仅validation整图重建。选择validation图像等权平均1-Dice最小的checkpoint，严格比较原始float64误差，无四舍五入；完全相同保留最早epoch。验证不看AURC、不用外来源、不挑不确定性分数。每epoch必须完成验证才有资格成为候选checkpoint。最多40epoch或6 GPU小时，包含训练和验证（总计时从模型构建前开始）。无按效果早停。

达到时间上限时，在安全batch/tile边界停止；未完成验证的epoch不得替代此前有效checkpoint。若已有有效checkpoint，必须如实作预定最终诊断；否则inconclusive。保留最后/最优checkpoint和选择表。最终推理单独至多1 GPU小时，总预算至多7 GPU小时；这是对r0六小时含义的前瞻明确化，不是已经获准的配额。若最终推理未完整完成，结果inconclusive，不能据部分样本比较Δ。不增加seed、重启或换机，异常先留收据。

唯一最终诊断：选定checkpoint后才读取METU internal_test与BuildCrack预测；两来源分开，U_LC/U_H、Dice、空参考规则及ΔAURC按r0。每图导出概率、硬预测、stem/source/group、Dice误差与两分数；保存风险覆盖逐k表及同单位曲线。主值不由组平均/敏感性改写；候选组信息仅揭示重复权重局限。

## 代码接口、产物与仍缺事项

后续runner必须消费`metu_group_split_r1.csv`及BuildCrack原包身份；拒绝未知/重复stem、跨split同组、标签值/方向/尺寸变化、缺文件。训练dataset只接受train；validation仅checkpoint模块可读；final阶段只能载入冻结checkpoint，不能构造optimizer。预测输出写新run目录，不覆盖原始图像、标签或既有结果。

待实现模块：模型/数据读取/确定性crop/优化器与计时/验证选择/最终评价/收据。当前只提供split生成器、拼接参考和合成检查；不声称训练runner已Code Ready。数据身份：BuildCrack官方MD5和METU恢复验收收据，后续生产入口仍须重新校验对应文件；本清单hash只锁设计版本，不能替代源文件内容锁。

正式实验归属及证据域映射、完整runner、依赖版本锁、生产输入验证、独立全代码审查、Taobo资源与明确执行授权尚缺。Mac仅本地开发/轻量检查。无训练命令、SSH或GPU任务由本合同授权。
