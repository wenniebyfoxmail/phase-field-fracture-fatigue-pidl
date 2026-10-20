# 现有真实/公开实验数据：匹配历史对照可行性审计

2026-10-20；只读本地公开/development证据。没有读取新holdout像素、没有拟合/模型/求解/SSH/外发。本轮读取实际CSV头、ZIP成员、工作簿XML、现有manifest及作者loader；统计只是字段/行数/键的盘点。一次ZIP元数据读取因误把__MACOSX资源叉当UTF-8中断，修正为排除该元数据后完成；不是科学运行。

## 结论

没有一份现有真实数据已经证明存在足够的“当前物理状态相似、历史不同、同一未来加载、独立未来参考”的成组匹配对。现成资料可支持的是较弱的、仍有价值的观察性问题：在相同名义工况/当前压缩观测后，过去响应是否增加对未来发布观测的预测信息。它不等于物理状态充分，也不等于因果加载历史试验。

要区分两种“历史不同”：
1. 响应历史不同：当前观测近似相同，但过去场/几何变化不同；恒幅试验可以出现，需实测匹配共同支持。
2. 加载路径不同：高低载顺序、过载/停载等历史不同，匹配时点后施加相同未来加载；现有候选库没有已经验证的这种受控对照。跨载荷水平的两条恒幅轨迹不能替代它，因为未来驱动也不同。

## Mendeley 19 DIC

### 本轮直接核验
- `local_archive/open_data/mendeley_full_displacement_20261017/pt_frame_inventory.csv`：17,897行/19组。头为 `group,stage,cycle_from_readme,pt_member,list_index,ch0_min,ch0_max,ch1_min,ch1_max,both_zero_pixels,nonfinite_values`，没有force、phase、actual timestamp、reference ID或独立裂长。
- `csv_samples/E_0Deg_20%_#1__early.csv`实际头：`# Stage: 阶段 702`；`# Units: length:mm angle:deg time:s`；字段 `id x y z displacement_x displacement_y displacement_z`。头有单位但无实际time列。
- 官方633B `local_archive/open_data/mendeley_optical_method_audit_20261018/Readme.txt`：C/E为中心/边裂，角度0/15/30，15/17.5/20%为ultimate strength比例，#为specimen id，N=30*(figure id−1)。
- 直接读 `mendeley_four_specimen_audit_20261013/4. Cycles vs Crack Length.xlsx` XML：四sheet分别42/38/41/35行，合计156标签；表头 `Figure ID,Cycles,Crack Length (Ground Truth),Crack Length (Predicted)`。四sheet只有 `E_0_175_1` 与 `C_15_20_1` 两个编码，无裂长单位列；不要读Predicted当参考。
- 同几何同名义载荷可选三重复：E0/20三组PT为1019/800/557帧，stage702–1720/502–1301/402–958；C0/15、C0/20、C30/20、E0/15各三重复；C15/20及E0/17.5各二重复。这是结构性候选，未计算当前相似距离或筛选结果。

### 物理可用性
- 19个实体试件矩阵、5Hz、R=.06、每30cycle峰值保持8秒采集，有已保存的2026-10-18全文核读依据；但实际每帧周期/相位、参考连续和载荷实测未进入CSV。原19个文件夹不能单靠名称证明批次/同源板独立。
- 当前响应：有原始三分量节点位移与发布2×128×128插值场。当前几何：已查裂长表只覆盖两个编码、156行，且属于同DIC/PT链；其余17发布组连这种已查裂长表覆盖也没有。本轮19组均未核实独立光学裂长参考。原始光学序列未在审计CSV/PT包找到。
- 历史与未来加载：同条件内只有名义恒幅计划；可条件于同未来计划研究响应记忆，但不能研究不同载荷路径的因果记忆。不同载荷level不能直接配成同未来加载。
- 未来目标：可用未来发布场；156裂长来自同DIC/PT链，不能当独立几何参考。
- 匹配pair：**仅可能（响应历史）；严格物理三条件未证；加载路径干预不能现成构成。**

### 最少补什么
可从现有文件继续补：所有组的字段/时间键表、同条件候选池、共同空间支持说明、各帧有效支持；这是既有development数据挖掘，但不凭此填造实际加载或误差。作者需补：逐试样匿名实体/批次映射，frame↔machine-cycle↔peak/hold/reference ID，实际load schedule/日志或确认同组共有计划，CSV↔PT坐标/裁剪/插值规则。物理裂长还需作者已有测量步骤及早中晚原图/独立读数和误差；六锚点只验证方法可行，不能代替全实验评分标签。若这些从未记录，必须补测/新采集。不同过去载荷而未来相同需新协议数据，不能从文件重命名得到。

主要补证原件：`.codex/worktrees/history-information-audit-20261013/docs/research/S02/S02-E006/mendeley_optical_method_audit_20261018.md`；`mendeley_full_data_report.md`。

## FATACRACK F/FF

### 本轮直接核验
- `local_archive/open_data/fatacrack_qualification_20261013/F-cracktip.csv`头：`n [cycle],x [mm],y [mm],CGR [micron/cycle],K1 [MPa.sqrt(m)],K2 [MPa.sqrt(m)]`。
- `F-ux-top.csv`头：`x [mm],y [mm],ux [mm],1001,2001,...`。第一未命名cycle的响应列与99001→100000异常均保留。
- 结构收据：F/FF裂尖386/114行；四boundary通道共有385/113cycle；能接三过去+未来严格1000cycle的起点379/107。F每边291节点、FF292节点，网格不同。
- 作者2026-10-17回复明确F/FF为两个不同物理试样，未加载图为DIC参考，边界是max−min周期幅值，裂尖为Williams投影的equivalent elastic tip。未给独立几何tip或定量重复性。

### 判断
- 两个受控金属试样，名义峰值F15kN/FF22.5kN、R=.1、10Hz；F15/16kN差异待作者原始记录。已有的是响应幅值，不是瞬时phase场。
- 历史和未来均各自恒幅，但**跨F/FF未来载荷不同**；不能把它们作为相同未来加载的历史对。单条记录中的近似几何回访也未证，测量抖动不构成复现状态。
- 独立未来标签：没有；tip和boundary同DIC链。**严格matched pair目前不能；发布DIC标签描述性历史任务已做且E005为负，不重跑。**
- 最少补法：作者已有实际load trace、此前载荷历史、定量tip重复/独立光学、第一cycle/999跳变说明；这可完善可解释性，但不能创造n=2且未来驱动不同所缺的对照。若要载荷历史干预，需要新的同未来载荷重复组。

证据：`structural_audit.json`、`author_reply_20261017.md`；`.codex/worktrees/history-information-audit-20261013/docs/datasets/history_information_20261013/fatacrack_qualification.md`。

## PHM T1–T8

### 本轮直接核验
- 实际读取 `local_archive/open_data/phm_mendeley_completeness_20261017/PHMDC2019_Data.zip`（419成员）中已有公开CSV。
- T1–T7的 `Constant Loading Profile-5 cycles.csv`均为101数值行、头 `time,loading`，从0到1秒；七文件字节相同。README规定5Hz、loading为MPa。示例首两数值行0,4.77与0.01,7.105583042。
- T8 `Variable Loading Profile-1 block-1000 cycles.csv`为20,001数值行，0–200秒；README规定重复1000cycle块直到断裂。
- 原包94个signal_1/2 CSV=47观测时点；头 `time,ch1,ch2`，ch1/ch2为激励/接收电压。每点两重复；实际ZIP没有Baseline成员（README描述Baseline存在，须保持差异）。另外检查已有 `history_candidate_selection_20261017/raw/PHM2019_crack_growth_training_data_v2.zip`，68个signal文件、同样没有Baseline成员；未据旧包覆盖NASA版本。
- `optical_records_T1_T8.csv`已在先前用户授权下全部development-exposed，56行，头 `specimen,cycle,published_crack_length_mm,load_regime,source_member,status`。
- 每试样光学标签数/信号时点数/直接数值键共享数：T1 7/7/7；T2 3/3/3；T3 9/10/9；T4 8/8/7；T5 4/4/4；T6 7/6/6；T7 8/4/4；T8 10/5/5。T4 optical7054与signal67054冲突；T7/T8后期光学标签不能假设有同步Lamb波。
- 原候选固定跨度band审计只形成5窗/4试样（T1一、T3二、T5一、T6一），每折3–4训练窗；这是原band的结果，不能说任何可能协议只有5窗，也不能为了凑数随意放宽。

### 判断
- 作者明确8铝板搭接试样；独立实体比Mendeley文件夹语义更清楚。裂纹起始位置不同：T1/T6/T8为sensor6–1，T2/T4/T7为9–4，T3为8–3，T5为10–5。位置/传感路径应作为条件，不能当可交换同几何。
- 当前几何：稀疏显微光学裂长，独立于Lamb波输入。当前响应：两次Lamb波测量；没有完整DIC/宽度/路径几何。光学误差/分辨率数值未知，裂长是独立模态参考但不是无误差真值。
- T1–T7未来恒幅计划确实可统一；可寻找相近裂长但不同先前增长/波形历史的观察性对，然而当前相似容差和足够共同支持未证，不能说已经找到matched pairs。
- T8是唯一变幅个体，且未来也变幅；不能以T8 vs T1–7构成不同过去/相同未来加载。恒幅组不同累积cycle不等于受控不同load path。
- **最接近“加载已知+独立未来标签”的现成候选，但仅可能形成少量响应历史匹配；不具足够已证的决策尺度对照。**

### 最少补法
现有ZIP可补完整谱、信号/光学索引、共同路径分组、起点可得输入；无需新模型即可形成availability表。作者/原补充包需补：T4 cycle更正证据、缺失Baseline与T7/T8后期信号、光学测量分辨率/重复、采样是在怎样的load/卸载相位、试样批次/预裂历史。若只想预测独立光学裂长，未必必须有DIC，但需足够固定物理跨度的原生标签，不能未来插值造truth；若要载荷顺序效应，需要新历史路径/共同续载的重复试验。

## D01三梁

### 本轮直接核验
- 读 `local_archive/experiments/S03-E016-D01/reference_source_trace_20261020/fourteen_stage_documentary_crosswalk.csv`：14行，三梁；B4四阶段10/30/40/50kN；B5六阶段10/20/30/40/50/60；B6四阶段10/20/30/40。字段含workbook/sheet/source_row/stop/restart/IB triplet时间。
- 读 `reference_inventory_blind_protocol_20261020/stage_reference_inventory.csv`：14/14 nominal force/piston join可得但未资格化；14/14同步误差界空；14/14独立整幅参考、同状态重新采集与独立坐标误差没有；14/14 load path/hold资格为unknown。
- 其他机位三拍在停止与恢复之间、较固定帧晚6–29秒。不同机位/有时间差不能自动当相同状态噪声。

### 判断与最少补法
- 已有固定相机几何候选及名义加载；piston displacement不是crack opening，梁间4×4相同格号不是同物理位置。
- 三梁均开发曝光；起始裂纹CAD图是重新加载前图样，不是14阶段真值。可以提出同下一名义荷载的候选比较，但当前相似几何/同步历史/独立未来参考都未证，**仅可能，不能现成matched pair**。
- 现有工作簿/日志可补停点与加载/位移历史语义，已有owner已追查；不能从nearest-time差推出同步精度。作者需补clock alignment误差/保载是否稳定/试件预裂历史；独立几何参考需已有高分辨率记录或盲审；同状态采集误差若旧图不适合只能补采。要正式跨梁结果需要未用于设计的完整新梁；不得读旧留出后称盲测试。

## SCB沥青（Yuan2020）

- 本地拥有完整论文/核读记录，**未有原始trial manifest或相机/载荷CSV**。论文3载荷水平(.2/.3/.4强度)×2疲劳样本=6样本；是否6独立母core未知。材料来自服役路面取芯，但测试域是实验室SCB。
- 论文15°C、疲劳10Hz、双目50fps；双目同步不证明与load同步。已有平移台误差不是裂长误差；晚期DIC失相关；作者damage使用最终Nf，不可作为在线状态。
- **仅是数据依赖候选；现阶段不能构成任何可审核匹配对。**同level两重复可能支持响应记忆探索，论文并未提供不同加载历史后共同续载设计。
- 最少向作者索取已有完整六试样清单+母core/层位ID，左右原图，frame/time/cycle/phase/force/displacement共同表，DIC参考/标定/有效掩膜，独立裂长/裂区读数及重复性，许可。先索取文件索引和几帧schema示例可判断是否有关键字段，不必先搬全量数据。需要载荷历史干预而原试验恒幅时仍需新采集。
- 证据：`local_archive/open_data/dataset_literature_audit_20261019/user_supplied/PAPER-20261019-FULL-SCB20.json`，对应完整论文p2–6、p9–11。现有SCB方案是设计，不是数据已到。

## ISTRUST

### 本轮直接核验
- `research_hq/identification_uncertainty_prediction_20261006/istrust_reproduction_preparation_20261020/image_manifest.csv`头：`archive_index,filename,specimen,camera,parser_rul_s,file_bytes,zip_crc32,width,height,mode,format`；没有cycle/load/phase/strain/crack geometry字段。
- 全发布包原验收2,416 TIFF、9试样×2视角；本轮只读manifest及loader，没有开新图/模型。实际dataset目录只见TIFF，无同步载荷表。
- `local_archive/open_data/istrust_20261020/ISTRUST_MODEL/istrust_model/data_gen.py`第35–42行把文件名最后两项拼为RUL，筛RUL<4000；第58–71行排序/去开头8或9帧/隔帧取图；`create_targets`使用下一索引j+7而输入止j+6。参考回放的未来label与当前图有约52秒偏移，不能随意称current-state RUL。
- 发布协议10Hz、R=.1、每500cycle暂停后近峰值拍摄（已存全文核读）；有暂停/升载，因此不能time×10造cycle。作者EOL为失去承载能力。

### 判断与最少补法
- 能研究图像前缀→RUL；当前损伤只是图像/latent，未有独立裂长。物理终点原则独立于图像，但当前文件名RUL的时间定义/生成规则尚需作者解释。
- 无逐试样实际history load trace，不知道不同过去路径且共同未来加载；相近图像不证明相同物理状态。**仅可作相邻RUL/响应历史基准；不能承担本问题的几何匹配主实验。**
- 现有文件可恢复明确图像/试样/视角序列与代码目标；不能恢复真实cycle/载荷。作者需补frame↔timestamp↔cycle↔phase/hold，load program与EOL时刻，试样批次，初始缺陷/几何及独立损伤测量。若仅RUL目标可不要求裂长标签，但主问题已经相应改变。

## 建议的决策尺度设计接口（不执行）

1. 为核心物理问题保留同一对象/材料/几何、当前独立几何+响应、历史载荷、共同续载、独立未来几何五轴。当前库优先PHM作小规模观察性补证或Mendeley作发布响应接口，不把二者升级到受控历史因果。
2. 当前相似容差必须来自参考重复性/可分辨率；先记录候选共同支持有多少实体/载荷路径/阶段，不看未来结果选pair。匹配不到就是数据不支持，不强行靠宽band/跨几何凑。
3. 同一有限模型的主基线先包含几何、当前响应、全部起点已知的过去/未来驱动与暴露量，再加入过去响应；训练侧匹配donor破坏自身历史对应但保当前接口。删去/压缩过去加载仅作另列诊断，不代替主基线。全部按完整试样分组，固定物理H，已有独立参考评分。当前观测已足够则历史无收益是可接受的结论。
4. 真正的load-history试验应预先设计不同过去加载路径，然后在当前相近可见几何/响应处进入相同继续加载，保留历史造成的内部差异；需要多组独立重复以避免材料差异冒充记忆。synthetic可先直接操控这些条件并知道隐藏状态，但真实实验验证仍不能被合成替代。

## 精简的可补回/不可补回

- 本地可补回：发布序列键、nominal condition、已有记录的load profiles（PHM最强）、共同空间支持定义、时间/标签可用性、完整开发分组；不需训练。
- 必须作者/既有外部资料：实际相位/载荷/参考映射，独立几何标签和误差，实体/批次，测量生成流程。
- 若原试验未设计就必须新采：不同过去load path汇合到共同future drive、足量独立试样、同状态重采与独立未来几何。

绝对根：以上相对路径全部在 `/Users/wenxiaofang/phase-field-fracture-with-pidl/`。本审计只写此临时文件，不改实验/Obsidian/数据。
