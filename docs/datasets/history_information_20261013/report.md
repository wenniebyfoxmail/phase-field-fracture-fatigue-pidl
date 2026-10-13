# 观测历史是否增加裂缝预测信息：可行性审计

日期：2026-10-13（Europe/London）。Owner：history-information-audit。
分支：`codex/history-information-audit-20261013`；base：`699ae7954bf445a4ee624e2eaa68b4c7cd0edc2e`。
范围：现有资格记录、文件/schema/时间键审计、官方公开来源筛选、最小验证草案。
未开展模型拟合、训练、预测评分、FEM求解、人工标注或作者通信；未打开既有封存holdout。
这是方案与数据能力审计，尚非已冻结/独立审核的预测Experiment，也不改变既有负结果。

## 决定

**找到适合进一步核验的轨迹，但没有一条现成数据路线足以直接证明道路上的历史增量预测价值。**

最小的固定跨度实验数据候选是 FATACRACK 2329057：本次实际取得两条裂尖坐标序列与两份边界位移表，循环键可连接；只有两个配置，适合数据与方法可行性诊断，不能支持总体泛化。多试样升级候选为 Mendeley dywwnjv22h 的四个有裂长标签试件，须先完成原始文件/schema和参考来源资格审查。

道路路线优先从现有 MnROAD 汇总工作簿筛选新的 cell/lane/construction episode 面板，先做标量裂长任务。该较窄问题不要求完整机制模型的全部温湿度/力学通道，也不必先解决二维地图配准。若要检验结构响应历史是否增加信息，仍需同键的受载response历史；当前未取得。

## 任务边界

区分三件事：历史缺测补全、当前状态估计、未来预测。本文目标仅为未来预测的**增量信息**。输入均截断于预测起点。不同实验材料/道路不能拼成同一轨迹。

完整的当前损伤状态通常不可观察，因此合理的问题是：在当前可部署观测、已有最近增长率、荷载/环境及时间信息相同的条件下，增加更早观测是否改善未来误差？改进仅说明对该观测表示有增量价值，不证明Takens条件、物理隐变量唯一性或因果机制。

## 决策表（非数值方法验证图；此轮没有预测结果）

| 路线 | 实际可确认的轨迹能力 | 阻塞与既有结论 | 本轮 disposition |
|---|---|---|---|
| LTPP 六路段旧面板 | 既有记录：37 states；enriched分析实际30 transitions | 原协议已负结果，二维注册路线未合格；仅5–8日期/路段且间隔多年，不适合90%缺失演示 | 保留负结果；新面板/新估计对象另行预注册，不重调旧holdout |
| MnROAD 汇总表 | 现存工作簿3593行、84列；297 SECTION_ID，其中282有至少4个不同DAY；22-D-2016有10日期 | section ID不等于独立道路；车道/重建/维修/单位、调查一致性、target误差须核对 | 首选真实道路标量数据审计；不是282条已合格自然轨迹 |
| MnROAD 22-D-2016 地图 | 既有资格记录7个Excel配对的封缝前states/6 intervals，截止2019-10-23 | 2019-10-24 crack seal；累计地图多日期/车道语义未闭合；无独立section | 有界语义修复候选；禁止跨封缝，自然链不能计作多试样 |
| PaveTrack_PD | 既有公开manifest：165位置，8918带时间戳图像，median50/位置 | 物理标尺/配准/裂缝身份与维修缺失；位置10旧注册失败；已有确认集已消耗 | 只查开发manifest；未重新读确认图像；不直接作物理长度forecast |
| AA2024 11945905 | ZIP实际存在；既有header审计342 stages→114 cycles，每cycle三load states | 一条已暴露序列；DCPD标签，记录按增长触发；同cycle三load不是三时间轨迹；已有条件gap诊断 | 接口/采样诊断参考；不重开旧forecast gate，不以gap泄漏换固定跨度预测 |
| CrackMNIST 28_S | 本轮重开HDF5核对keys/size：126598155 B；force、exp ID、DIC、mask/SIF存在 | 顶层无cycle/time/stage/frame键；增强样本不是独立轨迹；尖端窗口坐标不等于绝对裂长 | 不适合现成未来预测；需source-frame/cycle对应 |
| DCB 10895431 | 既有11有效试样、249 origins的next-observation比较 | persistence1.401mm、secant2.805mm；2/11赢，负结果；S02-E004在10-11行政暂停 | 不重试同release/estimand；不恢复正式标注或全量下载 |
| FATACRACK 2329057（新增取得） | F386、FF114裂尖states；边界ux-top数值cycle列385/113，全部与目标cycle相交 | 两条配置；DIC与裂尖同观测体系，参考误差、相位、坐标和load协议仍需核对 | 最小固定跨度development诊断候选 |
| FATACRACK 3891441（新增取得） | data.zip 119.8kB MD5匹配；74 CSV，多lab/config/side文件 | 抽查列为x–CGR、x–SIF、x–y，无cycle键；recto/verso不是独立试样 | 多lab比较背景；不能从曲线行序推时间，不能自动扩充2329057 |
| Mendeley dywwnjv22h | 官方19个位移试件、4个裂长试件；633B README本次重新取得；N=30*(figure_id-1) | CSV/PT与标签本轮未取得；裂长来自PT场，独立reference未建立 | 最优多试样固定cadence候选，条件性，不是19合格标签轨迹 |
| NASA/PHM2019 lap joint | 官方T1–T6有optical裂长、wave与load；T7/T8验证；六训练试样记录数7/3/10/8/4/11 | 原始ZIP本轮未取得；未来标签并非均公开；波形时间轴≠疲劳cycle轴；采样很少 | 稀疏传感器辅助候选；三次过去+下一目标最多25 origins/5试样（官方表推算） |
| 沥青SCB/CTOD/CrackPropNet/binder | 已有论文/来源和部分示例 | SCB/CTOD原序列需申请；CrackPropNet完整试样/time/load/terms未持有；binder获取与关联未闭合 | 道路材料匹配最好，但尚不能执行；保持现有request草稿 |
| ConTrack | 原作者页面确认相关论文与同团队公开PaveTrack | 本轮未找到可验收的独立ConTrack原始下载包；不与PaveTrack视作两个独立样本源 | 来源线索，非已取得数据 |

当前MnROAD工作簿路径已变为`/Users/wenxiaofang/Downloads/MnROAD/HMA Distress All export.xlsx`。旧报告的Downloads根路径已失效，但文件未丢失。本轮只核对schema、ID与日期计数，未对裂长评分。原始表中297/282的数量仅为候选库存；同cell不同lane、construction episode及共用天气不能当成完全独立样本。

## 新取得FATACRACK文件的精确能力

来源：https://zenodo.org/records/2329057 ，CC BY4.0（官方API metadata.license核对）。
本地：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/history_information_audit_20261013/raw/`。

- 裂尖CSV字段：`n [cycle],x [mm],y [mm],CGR [micron/cycle],K1 [MPa.sqrt(m)],K2 [MPa.sqrt(m)]`。
- F：386 rows，cycle1至385000；FF：114 rows，cycle1至113000；相邻gap集合为999和1000，不宣称完全等间隔。
- F边界表291空间位置×388列；FF292×116。前3列为x/y/ux，后续列为cycle。`ux`那一列的初始时间语义尚不确定，本轮未硬指派cycle1。
- 只用明确数值cycle列，F385和FF113个时刻能按cycle连接。要求过去两次、当前、未来均存在且间隔恰为1000 cycles，可构造F379、FF107个origin。它们强烈重叠，**独立单元仍至多两个配置**。
- 读取了CSV和有限样例，全部视为development-exposed；未评分、未筛选好预测区段。不能把这批资料称作完全未曝光confirmatory holdout。
- 未使用CGR/K1/K2作预测特征：CGR可能由未来/中心差分计算，SIF依赖裂尖与场分析。先限定原始当前/过去的位移响应与直接坐标测量。
- 3891441的多lab文件与2329057的谱系关系未核实，不能把相同试验重复计数。data.zip的MD5匹配公开值`475901fa1a580a84881c644ff4c35d0f`。

## 最小验证方案：草案，未拟合，非Run Ready

### 先做数据资格，不选择模型

固定字段：`physical_specimen_id,lineage_id,cycle/time,load_phase,load,reference_id,coordinate_frame,observation,target,quality,intervention,censor_reason`。
FATACRACK先确认F/FF独立试样和载荷相位、边界坐标参考、裂尖提取协议及其repeatability。Mendeley先只取得README+四个标签试件清单/XLSX及少量对应CSV，确认30cycle索引、缺帧、重叠文件夹、absolute坐标、载荷相位及标签来源；不下载作者模型或执行pickle/PT文件。

MnROAD先筛出以前未用于预测调参的新cell/lane/construction episode，核对单位、区间长度、distress定义和维修删失。至少4日期只满足“3历史+1未来”的构造条件，不是充足功效证明。标量任务无需二维配准；空间tip/mask任务必须另行通过注册和持续身份资格。若响应历史不可得，先限定为裂长历史的增量信息，不宣称锚点传感器重建损伤。

### 冻结一个窄预测问题

候选主任务：当前起点N，预测直接记录的裂尖投影x在N+1000 cycles的增量（FATACRACK）；Mendeley若通过可改为N+30 cycles，但这是单独数据协议，不混合评分。禁止用未来anchor、未来真实gap、全轨迹归一化或双侧平滑。缺失固定目标时不从未来插值；记录coverage。

若取样本身按增长触发，现有资料最多支持“给定实际下一记录gap”的回顾性条件诊断；必须明确降级，不能报告预设跨度forecast。道路调查日期若不是起点已知的计划日期，同样不得把实际下一日期作为已知部署信息。

### 信息匹配的比较梯子

1. B0：persistence。
2. B1：最近两次裂长/裂尖坐标的时间校正secant；这是已有历史信息的强简单对照。
3. M0：当前裂长/坐标、当前固定ROI响应、cycle与已知load，另含B1的最近增长率；用一个小型固定回归器。
4. M1：在M0全部输入上，只增加更早两次响应的因果差分/延迟；回归器、容量控制、信息截断和fold完全相同。

M1–M0隔离“更早响应历史”的增量；M1还必须与B0/B1比较，避免只超过一个很弱的单点模型。选择ridge或GPR须在development阶段一次确定；不能因某个holdout结果而换模型/lag。这轮没有拟合上述任一模型。

原始force/响应同相位或明确相位校正是必需的，否则历史特征可能仅编码load变化。不要使用以已知tip为中心、窗口不断移动的crop作为固定空间响应；冻结部署可确定的ROI。材料、载荷、试样谱系与实验室分组从元数据确定，不用目标曲线筛选。

### 评估与停止

- 两配置FATACRACK仅可报告chronological development诊断，不存在可信总体显著性声明。图上显示全部合格未来段与persistence/secant，不随机抽帧或bootstrap窗口制造样本量。
- 有合格多试样后，整physical specimen留出，并保持各fold训练的目标时间早于对应预测起点；同试样多相位、两面、增强图、重叠窗口全部同fold。采样、归一化和模型选择在训练/development内完成。
- 一个主criterion：独立试样等权的未来x/裂长MAE差`MAE(M1)-MAE(M0)`。报告相同origin上的B0/B1和逐试样差；区间按独立试样/road block计算。只有2/4/5试样时区间和功效很弱，不以大量frame弥补。
- 尚无可辩护的实际改善margin或测量误差下限，因此现在**不设科学PASS阈值**。先核验目标repeatability及可分辨误差；正式criterion/margin和资源预算需在看新结果前冻结并审查。
- 时间键/参考/固定target不成立→数据inadmissible；噪声大于有意义增量或独立单元不足→inconclusive；合格正式协议下无历史增量→保留negative并停止架构扩张。不得调旧LTPP/DCB/PaveTrack消耗过的holdout。
- 后续Experiment需新ID、code/data/protocol独立只读审核与明确producer授权。当前用户仅授权审计与方案，未授权任何训练。

## 下一项决定性工作

**道路优先：对现有MnROAD工作簿做新episode的identity/maintenance/units资格清单；实验代理优先：完成FATACRACK固定cycle连接与相位/参考审查，再审Mendeley四试样标签连接。**
二者并行是工作方向而非已派发任务。当前没有作者邮件发送、数据申请提交或新模型执行。

## 证据入口

- 旧路由：`upload code/docs/real_road_trajectory_coverage_matrix.md`（2026-08-05，已过时，不能覆盖后续审计）。
- 现有LTPP负结果：`upload code/docs/experiments/ltpp_geoforecast_enriched_input_posterior_result_20260806.md`。
- MnROAD：`upload code/docs/datasets/mnroad_22d2016_trajectory_qualification_20260901/report.md`、`evidence.json`；官方https://www.dot.state.mn.us/mnroad/instrumentation/index.html 。
- AA2024：`.codex/worktrees/aa2024-value-blind-audit/docs/research/S03/S03-E012/experiment.md`，现存`local_archive/experiments/S03-E012/runs/S03-E012-R001/prepare/grouping_summary.json`。E003失败与后续E012诊断是不同协议，不能反向改旧结论。
- DCB：`upload code/docs/research/S02/S02-E003/experiment.md`、summary；E004任务分支的2026-10-11暂停说明。
- 既有沥青资料：`local_archive/open_data/dataset_literature_audit_20261012/dataset_audit_matrix.json`及`asphalt_dic_candidates_20261011/`。
- 新候选：https://zenodo.org/records/2329057 、https://zenodo.org/records/3891441 、https://data.mendeley.com/datasets/dywwnjv22h/1 、https://data.phmsociety.org/2019datachallenge/ 、https://data.nasa.gov/dataset/fatigue-crack-growth-in-aluminum-lap-joint 。
- ConTrack作者来源：https://charley33301.github.io/ （仅来源线索；未确认下载资产或独立性）。

## 复查状态

源文件/结构检查见同目录`capability_receipt.json`。无科学预测性能结果，无独立证据审核PASS。本轮只关闭可行性审计，不关闭任何预测Experiment。
