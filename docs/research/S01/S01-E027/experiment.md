# S01-E027 v1：外部裂缝像素监督预训练源的有界能力检验

2026-10-19，S01唯一owner；基于E026闭合8bc21bb1，branch codex/s01-e027-qualified-spatial-source-20261019。当前D6=引入并验证新的裂缝空间信息；不延续像素头/平移配方。此阶段先做来源与能力准备，独立6.1 sol-Medium设计通过后实现/轻量测试；本轮不传送/推送或执行真实GPU。

## 已有证据与唯一新增信息轴

E023只用E003类别特征配区域包络，不能当真像素teacher；E024从零CNN未胜常数；E025多尺度/前景抽样/两seed控制未形成区域；E026同步平移仅弱配对响应、Dice全0。完整保留其负结论。旧YOLO受污染、SAM2 GT提示和Liu同名DeepCrack原图许可未清，均不复用为合格teacher。

唯一新候选：**Zou et al. IEEE TIP2019 DeepCrack公开发布的固定CrackTree260裂缝像素监督权重**。官方qinnzou/DeepCrack，而非Liu Neurocomputing2019 yhlleo/DeepCrack/DeepSegmentor。信息来自另一批道路图像的裂缝像素监督和已学得的空间表示；不是再拟合现有缓存压缩器/像素头，不改变E003。官方来源/论文/代码说明训练CrackTree260；公开权重文件DeepCrack_CT260_FT1.pth，但发布物无逐训练图hash，故只称作者报告训练来源，不能独立证明所有训练/微调历史。初次目标只是发展资料上的候选能力，不承诺独立测试/总体泛化。

官方commit f3988031dd2adc3d19b32d1c48a2bf90d12871ac；原网络74个float32张量/30905011参数。权重123636774bytes，SHA945239375c2b3de45abccc2dbdc374e3259b55d16298b298fb9e0cd13be5ad63，已从README指定Drive文件取得，weights_only=True CPU载入/finite/key/shape与meta网络核验，0forward/0训练。原模型代码作为锁定外部输入私有保存，不声称拥有未声明的再发布许可。

## 固定范围：来源能力与目标域描述分开

A. CFD/CrackForest已于2026-10-08 SAM2 pilot development-exposed的全部12图：049/039/105/116/082/029/079/092/115/077/102/097。只用这些，不换图或打开其他CFD图。官方仓库cuilimeng/CrackForest-dataset当前README明确non-commercial research；本任务是私有学术诊断，不公开分发原图/标签。以原MAT groundTruth.Segmentation==2作为已发布裂缝类别参考，1为背景；不用由分割派生的Boundaries、不膨胀/腐蚀/容差或阈值扫描。每图固定320×480，输入原native尺寸，不裁图/伸缩，目标完全对齐。该12图是已暴露开发资料，不是独立heldout道路地点。

B. 原E026私有16唯一PaveTrack控制RGB128/mask32/身份精确复用；0PaveTrack源RGB读取、0资格地点参考/validation/reserve/新确认/排除地点访问。不再读取原完整835图/31156bank。只作目标域描述：参考仍区域包络，外部预测可能正确指出包络外未标注裂缝，因此不把这些像素直接称假阳性或精确像素真值。PaveTrack诊断不参与CFD来源主标准、不拟合/校准/调参数。

## 固定推理与输出

只加载该一个checkpoint/原架构，strict state、eval、requires_grad=False、no_grad、float32，0optimizer/梯度/拟合；无模型/层/输出/seed选择。完全沿官方data.dataset预处理：RGB→BGR、CHW float32/255，无ImageNet标准化、无resize；输入高宽为32倍数。只取原网络tuple第0项final logits再sigmoid，不选side map、无引导滤波/CRF/NMS/GT提示。CFD480×320、PaveTrack128×128均原生满足尺寸。

两次同权重确定性推理：pass0按CFD上述12→PaveTrack16固定索引升序；pass1反向顺序。共56单图forward、batch1。只用pass0计分，pass1仅检查同输入max|P0−P1|<=1e-6、模型前后权重不变/无梯度。重复一致是工程复现，不是两seed训练成功或学习稳定性证据。

全部56map和权重身份冻结后再解封评分参考。接口predict只有RGB；训练/资格GT不进入网络。PaveTrack native128map固定4×4均值到32用于包络描述，不用GT移动输入或输出。无平移/增强配方。

## 结果标准、基线和可保留的进展

问题：固定外部像素监督源能否在多数预定道路开发图上输出有用裂缝区域，而非只有均值/位置/身份响应？评价单位为12张原图，不把像素/重复pass当独立样本。

固定阈值P>=.5，无容差，Dice=2TP/(2TP+FP+FN)，空/空=1；每图独立保存。简单基线为全0/全1、该图GT前景率的oracle常数、其他11图参考的逐格均值图（排除自身，全部在预测冻结后构建，GT知情比较而非部署模型）；另预定固定循环下一CFD图的预测作为身份错配基线，不新增forward。所有图尺寸相同，不需标签配准缩放。

**唯一来源能力主标准：12图中至少7图的正确预测Dice，比这5个简单/错配基线的逐图最大值高>1e-6。** 7是严格多数的最小整数，只支持这些预定开发图“多数有效区域”，不是总体可靠性或独立统计显著性；不设任意高绝对Dice。逐图/均值/中位数/最差与差值都保留。固定Brier、soft前背景、pixelPR、位置/错配优势为解释，不投票或救主标准。数值/身份/参考支持/工程重复性失败则inconclusive或inadmissible，不能称模型方法失败。

L0来源/数值/参考和复现有效；L1部分图或Brier/配对有益但多数区域未过；L2达到上述多数能力。没有本轮L3“PaveTrack资格”或L4“OOF净益”，来源L2也不能直接selector。PaveTrack16包络诊断报告固定区域Dice/Brier（明确不是真像素度量）、包络内/外概率及是否出现前景；不能据其目标不匹配的miss否定CFD像素能力，也不据漂亮图称目标域通过。

## 预算与后续路线

未来唯一S01-E027-R001，gpu-server/D-26-09/ad\\xw436、原physicalGPU1/UUID/桌面进程基线，CPU1，600秒墙时、RSS/GPU allocated/reserved各4GiB、结果100MiB；1checkpoint/0新模型拟合/0更新/56forward，PaveTrack源图0，CFD原图12和MAT12仅打包一次作为已暴露控制。结果包不重复装123.6MB权重，仅保存原始取得的锁定权重身份与输入收据；权重另存现有source_acquisition。首停不重试，不购买/改卡/扩桌面白名单。Mac只做元数据/安全state检查和轻量合成测试，不跑真实模型forward。

若CFD多数未过→记录分量，停止这一固定外部源，不换checkpoint/阈值/side输出；若源L2而PaveTrack弱→来源能力已成立但域/标签适配未证，下一项只冻结训练支持与独立自然地点资格，绝不直接OOF；若源和目标描述都有可用区域→仍须单独冻结原train6/qual2空间资格，再接选择器。原selector的E003前缀、容量1/image/3group、弃权、严格正面积交集和原OOF保旧净益标准不动，不扫描交集。最终决策仍看有益修正进入前三、旧检测保留与实际净收益；新确认地点持续封存。

最小证据：锁定外部source/权重/12CFD与16控制身份；56原生float32map与冻结收据；主/辅助逐图指标/基线/多数计数；单一资源/状态/输出清单；固定12CFD全部案例和16目标首例集合，不挑成功，公共0..1图及README。当前仅设计/实现测试授权，无源码/私有数据传送、公开推送、真实forward或R001执行。
