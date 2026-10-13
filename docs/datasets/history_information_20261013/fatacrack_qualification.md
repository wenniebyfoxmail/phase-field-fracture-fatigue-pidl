# FATACRACK 2329057 数据资格审计

2026-10-13；owner `history-information-audit`；controlled-experiment C1。
本次完成来源/实际文件/坐标/schema审计，未拟合、训练、预测评分或发送作者请求。
范围只限Zenodo2329057；后续多实验室3891441用于核对来源，不能替换本包的试样与误差语义。

## 决定

**固定1,000-cycle时间键与同cycle幅值响应可连接；独立试样谱系与测量误差未完全资格化，暂不冻结预测执行协议。**

数据读取正常不是预测信息充分，也不是独立标定参考。条件方案见`fatacrack_protocol_candidate.md`，状态`DRAFT_BLOCKED_QUALIFICATION`。

| 核查项 | 结果 | 依据与适用边界 |
|---|---|---|
| 来源/文件身份 | 通过文件身份检查 | 官方API列出15资产，本轮取得12 CSV+4页PDF；13/13 MD5吻合。未下载F.zip/FF.zip，也未取得原始min/max相机图像 |
| 两条记录的独立性 | 支持两个不同载荷试验；严格谱系待确认 | PDF§1–2/Fig2–3分别展示F与FF试件照片/裂纹路径；boundary网格不同，不是同一数组复制。未给独立specimen serial、原板批次、重复数或是否同试样更改载荷的明确书面说明。最保守按两个test records记录，不能认证iid或跨试样总体泛化 |
| 载荷/相位 | 名义协议与幅值定义明确 | 本包Fmax15.0/22.5kN，R0.1，10Hz；图像每1000cycles在min/max采集；响应是max减min幅值。Fmin由名义R得1.5/2.25kN，ΔF13.5/20.25kN为推导值，不是实测load trace |
| 时间键 | 通过明确数值键的结构检查 | F386、FF114裂尖rows；全四boundary通道相交385/113cycle；严格1000跨度且有3过去状态的origin379/107。两条均99001→100000为999cycles，保留原始键，不改成100001 |
| 坐标参考 | 本记录内幅值/投影坐标可解释；跨记录精确标定未证 | 单包Fig1：x左边缘0至右边缘50mm，y以孔中心高度0，孔中心x25mm，缺口尖端y6mm。CSV与此一致。多实验室Team4描述未加载初始图作DIC参考，但不能据此补出本包缺失reference图或serial |
| 裂尖测量误差 | 未给出可用定量误差模型 | 裂尖由DIC幅值场的非线性最小二乘投影提取；未给重复测量、独立显微参考、位置置信区间、偏差或分辨率测试。8.56µm/pixel是像素尺度，不是裂尖误差。不同load/裂长下的误差可能不同 |
| 输入/标签独立参考 | 未建立 | boundary响应与tip标签由同组DIC场导出；拟合误差/相机误差可能共同传播。只能预测发布的DIC-derived x，不能据此认证真实物理裂尖 |
| 可审核预测协议 | 未Run Ready | 先补谱系和误差/参考资格；不能为取得一个PASS而发明噪声下限、剔除不单调标签或重划已曝光尾段 |

## 原始证据和修正

主来源：https://zenodo.org/records/2329057 ，CC BY4.0；官方页面注明厚度应为4mm。文档正文DOI为1478472，而此次文件绑定2329057；引用时保留这一差异，不将同stem同名文件当成新的数据。

完整4页说明：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/fatacrack_qualification_20261013/Fatigue_Crack_Propagation_Benchmark.pdf`；MD5 `5e9bf325e326bdd5f42bf8f2872fec73`。
已检查Fig1几何、Fig2两种试件照片、Fig3路径、Fig4 DIC域、Fig5指标与§3字段定义。

- 本记录明确F=15kN；后续3891441汇总§1.3说316L F=16kN，Team4像素尺度8.7µm，本包为8.56µm。两者不是同一参数锁，当前以本记录15kN/8.56µm为准；不能在训练协议偷偷换成16kN。
- 3891441 Team8的±5%描述是该团队另一测量流程的误差上下文，不能移植为本Team4裂尖位置的mm误差。
- 本包§3写CGR为mm/cycle，而CSV写micron/cycle，亦存在单位差异。CGR/K1/K2不进入候选预测输入，因此此差异不通过猜测解决。
- CSV第一响应列名ux/uy，其cycle没有明确标注。尽管很可能对应首个cycle1，当前不作此假定，只用其后的数值列名，初始列不进入时间连接。

## 实际文件结果

F top/bottom各291位置，x范围0.21828–49.866mm；top y12.441mm、bottom y−10.842mm。
FF top/bottom各292位置，x范围0.20116–50mm；top y12.852mm、bottom y−10.602mm。
每条记录内部ux/uy坐标数组分别在top和bottom完全一致；所有坐标与响应entries有限；cycle列唯一；target n/x/y有限且n严格递增。
这些top/bottom是DIC分析域边缘，不是200mm长试件的端部夹具；不能当成完整试件grip边界或由其恢复完整全局载荷。
两个记录的网格与y位置不同，跨记录不得按row索引拼接；需独立固定坐标聚合，并保留实际跨度。

结构结果：`fatacrack_structure.json`；逐文件身份收据在raw archive的`acquisition_receipt.json`。本轮使用已发布位置数据作结构/坐标范围检查，没有评估任何未来预测误差。全部资料维持development-exposed状态。

## 为什么目前不能给出裂尖误差数值

图像尺度、CSV保留位数、相邻x的起伏、预测残差、跨F/FF差异及Williams拟合残差，均不能独立替代真实裂尖测量误差。不能由两条完整曲线调出平滑强度后，再将平滑残差宣告为误差分布。
若重做同图裂尖标注，只能估计同图/操作repeatability；仍不能涵盖相机漂移、DIC系统误差、独立物理准确度。公开ZIP注明为displacement-amplitude VTK，不是raw相机重复图像包，因此为误差资格盲目下载约304MB VTK并无帮助。

## 最小修复请求（未发送）

只需向数据作者确认四件事：

1. F/FF是否为两个不同物理试样；各自匿名serial/原板批次、是否有此前载荷历史、测量侧、实际载荷值及与后续16kN描述的关系。
2. 第一ux/uy响应列对应哪个cycle，99001→100000是否为真实记录键还是导出编号切换；不得在收到答复前修补数据。
3. 本包坐标原点/单位、DIC参考stage、刚体补偿方式；boundary和tip是否同一固定坐标系；nominal max−min幅值的符号与实际load trace。
4. tip-x/y重复性或独立reference误差，优先索取已有标定报告/多次提取结果；若没有，请求按早/中/后cycle由预定索引选出的少量min/max原图、标定及同cycle独立显微reference。不能按预测难度挑图。

获得serial/相位/参考说明可修复数据身份；获得误差资料方能给物理增量收益设可辩护的误差下限。无独立reference时可另行降级为“发布DIC标签的描述性预测”任务，但须显式重定claim，不默认为当前物理目标通过。

当前disposition：`repair_source_semantics_and_measurement_reference`；没有科学预测结论，没有训练授权或训练执行。
