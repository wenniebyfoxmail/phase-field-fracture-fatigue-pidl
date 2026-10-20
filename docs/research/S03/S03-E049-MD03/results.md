# E049 results — MD03 frozen-observer triplet, 2026-10-18

目的：用另一根梁打通固定选图、历史预测、目标评价，检查冻结识别的迁移。
本轮：固定19.2%梁第87/130/173张（文件89/132/175），先保存预测再下载目标；
只读原文／像素后发现16位输入和密集散斑，目标开放前分别记录解码、几何探针修订。
结论：候选面积外推比保持少57px²误差（5.81%），但掩膜明显受喷涂散斑影响，
支持流程与候选输出连续性，不支持已验证的裂缝演化预测。D3选择观测语义核查。

## Acquisition/order finding

Official dataset and associated paper section2.3 confirm one DIC beam per
19.2/33.7% group, black speckles/white face, Canon EOS6D/100mm macro, four-point
bending. Publisher text now available via Jina, unlike the earlier abstract-only
receipt; relevant methods saved locally. Repository Jina PDF request returned403,
no PDF/figure images fetched. Search/full-page text includes result descriptions,
so this is not a globally untouched/blind dataset. No new results attachment read.

Neither retrieved methods nor any of the three TIFF headers gives acquisition
timestamps, trigger interval or filename-to-load mapping. Native images are
5496×3670 unsigned16-bit single-channel. Equal filename gaps43 remain an explicit
**file-order continuation diagnostic**, not seconds/cycles/kN or confirmed future.
No image, interval or ROI was replaced after scoring. Other33.7% beam unopened.

Sources: [official dataset](https://data.mendeley.com/datasets/wv7hvgg8c7/1),
[paper section2.3](https://www.sciencedirect.com/science/article/pii/S026412752030719X).

## Fixed observations and predictions

History-only probeROI[2260,1600,3240,2160], band[2500,1720,3000,2080] (500×360px).
Seedx2750 is from midspan layout, **not an independently traced crack**. Two
pre-target amendments are explicit in decoder_amendment.md/history_probe_amendment.md.
Frozen E045 transfer/E037 extraction, threshold100/contrast20/box101/corridor60/
near12/componentheight30 unchanged; input16bit//257 fixed range, no auto-stretch.

| File index | Candidate area A(px²) | Occupied rows L(/360) | Row mass M(px/occupied row) | Transferred guide x |
|---|---:|---:|---:|---:|
|89 history|5343|272|19.64338|2723|
|132 history|5400|272|19.85294|2723|
|175 target|6381|330|19.33636|2776|

| Saved method | Prediction(px²) | Absolute error vs6381(px²) | Gain vs hold(px²) |
|---|---:|---:|---:|
|Hold|5400|981|0|
|Area secant|5457|924|+57|
|Support-hold / mass secant (secondary)|5457|924|+57|

Readout coverage3/3, paired numerical query1/1. Independently verified crack
forecast cases0; that is absence of reference evidence, not measured0% accuracy.
L is occupied image rows, not total crack length. M and EDT thickness are mask
geometry, not half-depth aperture. Constant historicalL makes the separated
arm algebraically redundant; no extra method benefit claimed. No uncertainty
interval from a single query or from dependent skeleton points.

## What the figures show

F00 shows all3 whole-source images and fixed interiorband. F01 shows every
originalband/mask/path/row profile: cyan candidates follow separated dark
speckle clusters, not a verified continuous crack. Geometric guide moves
2723→2776px at target (53px); because the historical seed is straight, unchanged
DP max_step0 chooses a constant-x column and can switch columns across images.
An increase in measured support is therefore not established crack extension.

F02 shows slight predictive gain but both methods underpredict the observer's
last increase. Candidate area rises981px² whileL rises58rows andM falls0.51658.
This identifies coverage/selection change as a concern, not proof of a physical
mechanism or of speckles causing the entire difference. No TP/FP count possible
without a reference. Do not relabel all selected pixels as known false positives.

Minimum view diagnostic: historical ROI ORB1110/1350inliers, median residual
0.713px; origin→target946/1303inliers, residual1.090px, scale1.00462,
rotation−0.04075°. No warp applied; this is image consistency, not independent
background/material-point correspondence. No four-anchor repair imposed.

## Execution, QA and provenance

- Clean code01528c090b6c184597c597d5d9dbfec0a3f7efc4; frozen adapterSHA
  696afb5cc5fa8500435d40c1abe25cd1fbec9eed3971615b98f1d741c74c1f74.
- Predictions saved21:22:23.307UTC, target decode21:23:27.175UTC; separate start
  receipt confirms no target file before download. PredictionSHA
  667938d8939f85af6c4bb64f26bc99841d70fc6cedca509bdc0674a4b8afb67f unchanged.
- History analysis1.028s, target analysis0.799s plus27.465s target retrieval;
  all3official byte/hash identities verified,116524140source bytes, no GPU/training.
- Synthetic DP/observation/factorisation/equal-index checks and separate array
  counts/arithmetic/order/hash audit passed;373protected old inputs/results
  unchanged. Local audit is not an independent annotator/reference.
- All3final PNGs actually opened; same-stem sidecars validated. Ten PNGs including
  initial historical previews have sidecars; initial white previews retained
  as reader error, not used for ROI or measurements. No scientific rerun.
- Initial prepare used a nonexistent E048 filename, stopped before any pixels;
  corrected toinput_lock.json with failure receipt. No source/parameter change.

Full sources, history/target arrays, prediction, text/failed-access receipt,
figures, sidecars and QA:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/README_analysis.md`.
Final figure hashes inqa.json supersede the initial render manifest's sidecar
hashes after heading-only documentation validation repair; PNG bytes unchanged.

## Next smallest discriminator (proposed, not executed)

Keep current observer and this +57 result unchanged. On the same3already-open
images, first inspect whether long thin **new/opening structures** can be
distinguished from persistent sprayed texture using historical texture
correspondence/change evidence. Separate that diagnostic from this frozen
dark-candidate baseline; no error-tuned threshold, no fresh image/window and no
complex temporal model yet. A useful observation repair can advance the route;
this attempt does not make the entire identification/prediction route fail.
Acquisition/load order remains unknown and limits future-prediction wording,
not per-frame analysis. Old MD01 results, masks, half-depth definition and
scoring remain untouched. New beam is cross-material, not same-condition replication.

## 2026-10-19 D3执行小卡：纹理运动与新增结构（仅设计，未执行）

**Owner／目标锚点。** 本对话负责MD03观测接口；原问题是图像几何能否支持
裂缝演化预测，当前子问题是已有图里的散斑与疑似新增结构是否能初步分开。
`continue / repair`：补上预测所需观测，不把目标偷换成“只预测任意暗斑面积”。
E049旧候选面积收益及其限制完整保留。本卡不授权执行，也不重复D01的
16格覆盖预测或宽度工作；无新图像读取、配准、推理、下载、实验或审核。

### 输入和信息边界

- 只用E049已下载的19.2%梁89、132、175；沿用原ROI、band、16bit//257
  解码和E045/E037输出，旧掩膜、半深度定义、预测和评分均只读。
- **设计对仅89→132。** 175已经看过，不能恢复成盲测/封存目标；后续
  132→175只能是已曝光开发诊断，不报告新的预测收益或泛化性能。
- 复用`R002_history/predictions_before_target.json`内历史ROI相似变换，
  以及`R003_target/summary.json`内132→175变换；本卡仅指明文件，不读取
  原图或计算变换。将来若计算，只用已存变换，不增添光流/非刚性拟合，
  不用目标效果选择模型、观察带、位置或阈值。
- 这是图像坐标的运动补偿试探，不是已验证材料点对应。连续文件号仍不是
  实测时钟/荷载，开发残差也不是裂缝真值或物理裂宽。

### 最简单可比的观察

在同一后帧坐标和共同有效支持内，对每一对A→B同时展示：

1. 未补偿的暗化残差`D0=I_A-I_B`（同图像网格）；
2. 使用已存相似变换的残差`D1=W(I_A)-I_B`，双线性一次采样。

正值表示后图变暗、负值表示变亮，单位为固定8位解码后的灰度级，不做
直方图归一化、平滑、二值化、新阈值或裂缝mask生成。共同支持排除越界
以及双线性采样缺邻域的位置，边缘用灰色显示，不能把填充值看成结构。
暂不计算新面积/长度/宽度，也不再比较预测器。

目的不是“残差越小越成功”：如果运动补偿后散斑成对亮暗边减少，而局部
细长暗化仍保留，就有可供下一步检查的结构证据；全部残差消失也可能是
信号不足，未消失可能是非刚性表面变形/光照/插值，并不自动是真裂缝。

### 最小产物与叠图规格（待执行时）

- 一张两行诊断图：第一行89→132设计对；第二行132→175已曝光开发对。
  四列依次为A/B灰度叠图（两图不同色通道）、D0、D1、B原图叠加旧E049
  候选轮廓及固定中心线x2750。画整个既定band，不按残差/旧误差挑局部。
- D0/D1共用零中心`RdBu_r`、固定[-255,255]灰度级色标；原图同一解码
  量程。固定中心线不是裂缝注释，旧轮廓不是残差法新预测。
- 一个小判读表：逐对记“纹理边缘是否减弱／是否仍有局部细长残差／支持
  是否有效／不能解释的部分”。允许“部分／未知”，不强加完美独立真值。
  原始变换、输入哈希与共同支持留在该次新输出目录；每图带同名说明。
- 未执行预算建议：一个固定双帧比较器、仅上述两对、无参数扫描，CPU
  分析120秒内、无训练/GPU；正式执行前仍须保持当前授权和冻结边界。

### 预期判读与推进／返回条件

| 将来看到的模式 | 可保留的组件进展 | 下一决定 |
|---|---|---|
| 纹理亮暗边减弱，局部细长暗化在原图可定位 | 运动补偿具有可视区分力，残留结构是候选而非真值 | 推进固定候选结构核查；不立即恢复预测器竞赛 |
| 纹理减弱，但没有可定位细长残差 | 可解释纹理运动，裂缝信号仍可能低于当前观测能力 | 明确“未辨识”，先补观测依据；不把零残差当无裂缝 |
| 补偿后仍是散斑残差海，或细长结构与纹理分不开 | 已定位测量接口缺口，保留原图与失败叠图 | 暂停MD03预测器比较，先核查纹理运动/可见性；不否定MD01或整条路线 |
| 有效支持不足／变换产生明显重影或抹掉疑似结构 | 当前简单补偿不足以解释变化 | 输出不可判读区域与原因；先修观测解释，不增加拟合自由度掩盖问题 |

设计完成的交付就是本卡的输入、叠图规格和判读表；不是新增结果图。
新版入口为已安装`research-decision-core`及`road-fracture-experiment-gate`，
沿用已有D1，不重启调研；当前无子代理执行，也未发送跨对话消息。

## 2026-10-19 D3残差比较已执行：局部运动收益，裂隙仍未辨识

用户明确授权后，按上述小卡完成两对比较。没有改动正在执行的协议或换图。
复用原图、固定band和原已存相似变换，未重新配准拟合、分割或评价预测器。

| 图对 | 原始平均绝对残差 | 运动补偿后 | 相对变化 |
|---|---:|---:|---:|
|89→132，设计对|6.31617|6.79278|增加7.55%|
|132→175，已曝光开发对|13.93984|8.85141|减少36.50%|

单位为固定8位灰度级。两对共同有效支持均180000/180000像素，无填充伪影
进入比较；这不是独立样本数量。可视化按原卡共用[-255,255]色标，整带显示。
后一对总体差异减弱，但两对仍呈分散纹理边缘残差；当前图不能有把握地把
新增／张开细裂隙与散斑分离。残差下降不代表保留了真实裂缝，也不证明未见
细裂隙就是无裂缝。不能由此量化散斑误检率或给MD03新增预测收益。

结论：保留“第二对部分图像运动可解释”的组件进步；简单全局补偿尚不足以
建立裂缝测量对象。按卡暂停MD03预测器比较，不做逐阈值修补；MD01、D01及
旧5.81%候选面积结果／半深度定义／评分均保留，不判整个研究路线失败。

执行代码21d4b414，CPU1.770s、wall1.870s，425项旧输入／输出哈希不变。
方向／有效支持／暗化符号合成检查、独立逐数组算术、441点/对手算双线性
采样与保存矩阵核对通过；图已打开、同名说明校验通过。启动前字段名语法
错误和数值审核的BLAS告警另存，修复仅涉及元数据/审核坐标运算，无科学重跑。
没有新mask、面积／长度／宽度测量、训练、下载或新预测。

完整结果、判读表与图：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_20261019/README_analysis.md`。

## D3后续：观测可辨识性成组方案（仅设计，未运行）

**目标→机制。** 原目标仍为裂缝演化预测。图像可视为随材料运动的喷涂纹理
`T(phi_t^-1(x))`、照明变化`g_t`、裂隙的新增遮挡／开口对比`C_t(x)`与噪声
共同生成。只减掉一个全局相似运动，无法将连续形变、照明、插值和裂隙
分量唯一分解；绑定瓶颈是观测对象可辨识性，不是外推器容量。

**竞争解释。** H纹理：表面散斑平移/连续形变形成亮暗成对边；H光照：
亮度随空间缓变；H裂隙：局部新生细长间隙/两侧相对开口。插值也会改变
旧纹理边，不能因残差变小或细长就选H裂隙。上述是待检验解释，不是本轮新结论。

**具体干预。** 在现有同一band/共同支持上成组比较旧暗候选、已存全局运动
残差，以及“纹理对应＋局部开口一致性”的候选结构证据：以历史89→132
定义原有纹理边；检查后图中疑似细长间隙附近是否同时出现可定位的原始
灰度间隙与两侧纹理不连续/相对分离，而非只累加暗像素。若需要局部运动，
只拟合两侧平滑运动、保留中间间隙不参与拟合，防止用非刚性自由度抹掉裂隙。
这是待实现的一体化观测干预，不是当前运行新增的裂缝识别结果。

**一组成组判别，不逐项串行修补。** 只用89/132设计；175已曝光，只作
开发对照。未来一次性展示两对上的原观察器、全局补偿、结构证据三者；
同图报告(1)原有散斑/光照扰动的负控制：不应凭空形成开口；(2)带已知
细长间隙和两侧相对位移的合成注入正控制：不应被运动拟合/插值抹掉；
(3)真实原图上能否找到同位置的间隙/两侧对应证据。控制只验证方法响应，
不是人工裂缝真值；注入尺度以历史分辨率/纹理尺度预先说明，不能按175
或旧预测误差挑阈值/位置。无须先取得完美真值才能做这组开发判别。

**结果→路线。** 若扰动被抑制、注入结构保留，且真实图也给出对应开口
证据，则推进候选裂隙几何的整体开发评估，暂不称独立准确率/未来预测。
若控制能通过但真实图仍不可辨识，最关键缺失观测是至少一处可定位裂隙的
原始高分辨率/独立开口证据，或局部DIC不连续证据，而不是更多同源暗斑面积；
列明该缺口后选择是否获取，不自动开新数据。若局部纹理控制也分不开，
停止把这套直接灰度提取作为MD03裂缝测量接口，转向位移不连续观测或
更适合直接裂缝成像的数据，需另定范围；保留原数据作运动／纹理诊断。

唯一active D仍为D3观测可辨识性；本次批准的残差组件已完成，上述更强的
成组判别只是下一步方案，未启动结构提取、注入、局部拟合或新一轮调研。

## 2026-10-19 D3成组判别完成：已知扰动可分，真实开口仍待对应确认

用户随后明确授权执行上述成组方案。新增参数和所有控制在
[执行前协议](grouped_observability_protocol.md)固定；没有按175结果调阈值。
只用89/132/175既有图，89供控制、89→132作设计对、132→175仅开发诊断。

上一轮的含义：全局运动补偿只解释一部分图像差异（两对灰度残差分别
增7.55%/降36.50%），不能区分剩余信号的来源；它不是裂缝准确率提升。
本轮增加因果判别：用六个侧方纹理块、分别线性外推至中心，计算水平
位移跳量J；用中心相对侧翼的暗化Q作不同来源的外观线索。不是更换旧mask。

| 固定对照 | 已知间隙(px) | 中央J中位数(px) | 中央Q中位数(灰度) |
|---|---:|---:|---:|
|仅运动|0|−0.01023|0.00583|
|照明|0|−0.00830|−0.16250|
|平滑形变|0|−0.01420|0.00705|
|照明＋平滑形变|0|−0.01495|−0.17399|
|注入间隙1|1|0.99415|12.70080|
|注入间隙2|2|1.98977|25.42620|
|注入间隙4|4|3.98977|50.38749|
|间隙2＋照明＋平滑形变|2|1.98505|26.78628|

这是候选方法的实质组件进展：在同源散斑上，对本组照明/平滑形变响应近0，
能保留已知规则开口，不必继续只磨暗度阈值。控制是笔直、全暗、规则分离
的有利生成器，不能由近乎准确的合成恢复量宣称真实裂缝识别准确率。

真实两对均819/819探针可计算，固定x2750列21/21有效。J中位数−0.02608/
0.16394px，沿线10–90%分别−0.21579…0.05176/−0.86996…0.78823；Q中位数
0.66454/1.55757灰度。第二对在整网格上有开口样条带，但外观证据较弱、
局部响应混合，尚未把该条带和真实源图间隙/两侧材料对应联合确认。不能
拿最红位置当裂缝，固定中央汇总也不是最大裂宽。高NCC不是物理对应真值。

全819网格与全部8控制均显示；J图中宽条带/旁瓣部分来自跨度144px的
纹理窗口外推，不是精确裂缝路径。间隙4有6个离中心的搜索边界探针受限
（813/819），其余控制819/819，所有固定中心21/21；未隐藏困难点。范围
是沿线空间变化，不是置信区间，不给像素当独立试件。

执行代码1a8a89a3，wall3.829s/CPU3.776s，445项旧文件保护哈希不变；
无新图下载／全局变换拟合／新真实mask／预测评分／训练。线性形变消除、
平移/常量块/注入支持合成检查，以及10案例固定中心的独立NumPy NCC、
J/Q/旧mask足迹核对通过。3图已实际打开，同名说明验证通过。
完整数组、控制图、逐例统计、审核和图：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_grouped_20261019/README_analysis.md`。

**唯一active D3下一决定：** 保留两侧纹理开口证据作为候选观测；不要
重做同组阈值微调或直接恢复预测比较。用能定位的一小段真实开口／局部DIC
不连续参考检验候选条带，区分真实间隙与非线性形变/纹理/插值；不需要先有
整幅完美真值，但真实对应证据未闭合就不把J当物理裂宽。该参考获取/核查
尚未执行。旧识别、半深度定义和评分包括5.81%候选面积收益完整保留；
不重复D01的几何预测，也不将本轮合成能力冒充未来或独立泛化验证。

## 2026-10-19 D3源图定位核查完成：纹理跳量可复现，真实间隙未确认

用户批准推进局部对应核查。执行前固定[局部协议](local_correspondence_protocol.md)：
由上一轮175对全21行J中位数最大列选择x2782；保留x2598/2750/2902，
全部固定y1900，不按看图或误差换点。12张无增强、无算法边界原图裁切和
8组两侧六纹理块对应已全部展示；明确为算法知情的开发检查，不是盲标。

候选x2782的89→132/132→175局部J为0.20903/1.57575图像px，Q为
−1.18046/−0.45738灰度，最低NCC为0.96900/0.96543。较大J能复现，
但同点没有增强暗化支持，原图未能有把握地确认连贯新增间隙。固定x2750
后对J/Q为0.63485/5.11838，也保留而不事后替换候选。负Q不证明无裂缝；
高NCC/同图复现不证明独立材料对应，J不等于物理裂宽。

代码887ac0cd，wall2.893s/CPU2.841s；481项保护哈希不变，全部8组J与
旧场重构差0，固定选择规则核对通过；6图实看和同名说明验证完成。无新数据、
mask、评分或训练；旧识别、半深度和5.81%候选面积收益完整保留。
完整图/逐点数值/QA：父仓库
`local_archive/experiments/S03-E049-MD03/D3_local_correspondence_20261019/README_analysis.md`。

本次定位检查结束，保留结构候选组件；缺口收敛为少量可定位的真实开口／
局部DIC参考，而非先求完美整幅识别。唯一active D3下一决定是确定该参考
能否从已有资料取得及其坐标连接；新结果附件/外部获取未执行。不继续用同三图
自证或调阈值，不据此恢复MD03裂缝预测评分；D01几何预测owner不受阻断。

## 2026-10-20 D3已有参考清点完成（仅文件目录／既存文字）

[完整清单与坐标链核查](reference_inventory_20261020.md)。复核2026-10-18缓存，
不是在线刷新：173＋100张TIFF、2个根目录ZIP；已知E049本地原图只有89/132/175。
未找到单列DIC数值场／人工裂缝标注／开口表。论文既存文字§3.3明确OpteCAL
及Fig.7应变场—荷载曲线关联，故不能说作者没做DIC；但没有IMG文件名→DIC
状态、DIC网格→原图像素、局部开口定义或逐图加载连接。ZIP内部仍未知。

全275条元数据和10项文字源哈希归档于父仓库
`local_archive/experiments/S03-E049-MD03/reference_inventory_20261020/`。
零网络／下载／新附件打开／图像解码／新测量计算或评分；旧识别、半深度定义和
评分不变。局部参考尚未取得，不将作者应变结果的文字存在等同可用裂宽真值。

当前清点结束；下一建议包为图7＋四点弯曲ZIP目录／说明／表头的限定联合核查，
一次确认试件、帧状态和坐标连接，不开新TIFF或调参；下载／开附件未执行，
待用户限定批准。若只有全局挠度，则仅作加载背景，仍缺局部开口参考。
保留MD03结构候选组件，D01独立路线不受阻断。

## 2026-10-20 两ZIP＋图7已下载核查：取得DIC记录与同步线索

用户批注明确批准两ZIP和图7访问；[完整附件核查](attachment_review_20261020.md)。
两ZIP大小／发布SHA256／CRC均通过，共22实质文件。弯曲包含beamDispData.mat，
PLA3/PLA5分别222×21／248×21，均为7引伸计的伸长量及X/Y投影；有
testData.firstPhoto/present/missing/time/n、加载记录和作者按时间交集匹配代码。
这更新此前“尚未取得DIC／同步参考”的资料状态，不改写此前清点时的事实。

present→time关系在203／243项内精确满足5*(present-firstPhoto+1)。若它对应
TIFF后缀，固定89/132/175候选时间键为430/645/860，均各有1个machine时间键；
但缺显式IMG名／生成脚本，且公开目录仅157/173及97/100后缀在present中，
missing并不等于公开TIFF缺失。未作逐帧荷载连接、单位认证或预测重评分。

作者脚本用Ext1–3构造跨中挠度，Ext4–7位置用途未知。X/Y不是像素坐标；
包内没有引伸计端点、完整位移／应变网格或裂宽标注。图7已实际打开，能见
多条局部应变带，但未标IMG名或原图坐标。保留有用DIC／同步进展，同时仍不
把图7或1.576px候选跳量当数值裂宽真值。旧识别／半深度／评分不变，无新TIFF。

active D3下一建议为已有三帧的编号—时间—加载来源联合审核及引伸计端点
缺口整理，不再逐阈值修补；未执行荷载重联／重评分／外部询问。原文件与
schema记录在父仓库`local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/`。

## 2026-10-20 三帧时间—荷载与七引伸计只读核对完成

[精确映射表与全部语义缺口](three_frame_reference_map_20261020.md)。仅复用现有MAT、
作者.m及PLA3/5机器TXT。文件内单位与时间关系已核实：DATtime=round(TXT列1)，
MATload=列2×4.4482，MATdisp=列4×25.4，均全行精确；两梁7×3数据列与
Ext1–7精确一致。若IMG后缀为作者照片号，89/132/175对应时间键430/645/860，
机器行427/640/852、DIC行86/129/172，条件荷载9.64450/12.93056/14.15951kN。
三行均唯一且n匹配；这是有用的事后加载上下文，不是已知未来荷载。

不能整表盲连：n/time仅198/203和232/243项一致；所有16异常保存，不影响本三行。
missing既非公开文件缺失清单，也非可靠的机时间缺失清单；作者使用unique-time
交集而非n。未猜测补齐或改作者数据。仍缺IMG名—照片号生成约定，故表中
照片身份连接保持条件状态，不回溯升级旧预测结果。

Ext1–3用于作者跨中挠度及支点差修正，Ext4–7用途未给；每Ext只有Total/X/Y，
没有端点／参考长度／原图坐标。X/Y是伸长投影不是像素。局部裂宽参考尚未建立；
下一决定需一次性取得照片编号规则与七引伸计端点/参考图定义，不再同图微调。
本轮无新下载／TIFF解码／CV／拟合／训练／新评分；旧半深度与评分保留。
原始审核输出：父仓库`local_archive/experiments/S03-E049-MD03/reference_mapping_20261020/R001/mapping.json`。

## 2026-10-20 作者询问信准备及假设推进边界（未发送／未试跑）

用户要求合并照片编号与7引伸计端点／参考图询问、核对联系方式并给完整草稿，
不发送；另问能否在缺信息时假设推进。[完整本地草稿及联系依据](author_enquiry_draft_20261020.md)：
拟用Cambridge邮箱，收件hkt@berkeley.edu由Berkeley当前官网核对；Salazar论文
旧邮箱仅作历史信息，不默认抄送。无附件／承诺，未保存到邮箱或发送。

[第一性原理分析](assumption_continuation_20261020.md)结论：可以带明确、有依据
的照片编号假设继续图像几何／相对阶段开发；不能猜端点造独立裂宽参考。
7通道可以作为匿名辅助观测，不偷换裂缝预测目标。现有等步长外推对共同
时间起点／单位变化不变，不值得只补标签就重跑。事后荷载不自动成为起点已知
输入。不必等回信才推进全部研究，仅局部物理裂宽验证仍需真实空间参考。
本轮无新计算、CV、拟合、训练、新留出或评分修改；旧证据完整保留。

## 2026-10-20 发件身份纠正、Outlook草稿已保存与后续路线

用户明确更正研究负责人为Winnie／XW436；此前Haofan发件人来自错误的
Obsidian AGENTS记录，现已更正源文件、项目入口和记忆更新说明。实际Chrome
Outlook核验Xiaofang Wen／xw436@cam.ac.uk，署名Winnie Wen，To hkt@berkeley.edu，
无抄送／附件。草稿箱显示保存于11:03 Europe/London且“This message hasn't
been sent”；未发送，由用户自行发送。[完整正文](author_enquiry_draft_20261020.md)。
凭证在父归档reference_attachment_check_20261020/outlook_draft_proof_20261020.jpg。

用户同意不等回信；[下一实质比较已准备](assumption_continuation_20261020.md)：
仅已有三图，先按原图可见性区分少量裂隙／纹理／不确定段，再固定自主虚拟
引伸计及纹理对照，比较旧暗候选与两侧位移证据。不是恢复作者端点，也不按
预测误差挑位置；若原图分辨率不足，不造阳性参考。不重复共同时间平移试跑。
本轮完成草稿和方案更新，未执行新标注／CV／拟合／训练或新预测；旧半深度、
识别和评分不变。回信只影响作者坐标下的局部物理参考，不阻断整个主线。

## 2026-10-20 D3成组开口候选实现已准备（未运行真实图像）

HQ同范围准备指令下，复用旧六patch匹配、两既存变换及三图缓存，完成
[一次完整比较协议](controlled_opening_protocol.md)、独立新增实现
`scripts/md03_controlled_opening.py`及25项人工合成单元检查；
[精确差异复审与SHA](controlled_opening_review.md)明确为本地复审，非独立物理核验。
主动D3：中央／左侧内／右侧内同预算测量＋双向匹配＋五个配准扰动，固定84位置
各对全保留；主要看中央相对内部对照的扰动包络，不按预测误差选点或改旧评分。

输入合同只读核验9既有文件和3TIFF身份，未解码NPZ/TIFF或运行真实算法；
父归档D3_controlled_opening_20261020/preparation/contract_v2.json。25测试0.059秒，
仅人工软件检查，不是真实开口结果或producer成本。所有真实点可见性仍unknown，
不制造裂隙／无裂隙标签；数值可用不等于真实材料对应。原图可见段方案现收束为
不新增标注的固定位置成组比较，后续图像判读与其身份限制另记，不冒充独立参考。

拟单次Taobo CPU，1进程／1OpenCV线程／0GPU，600秒硬墙限，128MiB输出限，
预计<2GBRSS未实测；失败首停不重跑。尚缺精确host／root／RunID／执行决定，
未连接producer或启动。原作者信保持未发送；旧识别、半深度、5.81%及全部负结果保留。

## 2026-10-20 一次执行对象已具体化（仍未获准／未连接）

[单一完整待批卡](deployment_approval_card.md)：gpu-taobo／GPUServer8，
RunID MD03-D3-OPENING-20261020-R001，根目录
`/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001`，runtime `/usr/bin/python3`。
主机／目录不再留待批准后选择；实际runtime、依赖、CPU／内存／挂载及远端
文件状态均未核验，列为获准后的首检，不声称已有MD03数据在Taobo。

科学源3991b5cd及三项SHA不变，继承25测试；仅部署差异检查：四段Bash及
两脚本语法、九输入tar逐件哈希、最小源码快照、合同字节复制及空许可模板。
待传输入包113514186字节；无新数据解码。明确一次CPU600秒／128MiB输出，
任务局部2GiB虚拟地址限；完整首检／部署／首停／停止／取回校验命令均在卡中。
没有SSH、传输、GPU查询、真实计算或新评分；自然park，等待该精确执行决定。

## 2026-10-20 R001获准执行：首检通过，部署传输中

用户本轮明确批准完整待批卡，先准入、仅一次CPU比较、失败首停不重试。
approved_decision.json已记录直接人方原文，code／protocol／输入包SHA与待批卡
逐项一致。2026-10-20 14:18UTC观察到首次SSH检查成功，实际GPUServer8，
/usr/bin/python3 3.10.12、NumPy1.24.4、OpenCV4.10.0，Matplotlib模块存在；
CPU load1=4.309／64可用逻辑CPU，MemAvailable383169764KiB，data2剩596G。
实际Matplotlib导入仍为启动前任务内检查，不把模块存在等同完整运行成功。

独立远端目录创建成功，固定输入包的首次rsync仍在等待完成确认；当前未调用
启动命令、无新科学结果，不重传或更换连接。原九输入、识别、半深度和评分
保持不变。依据父归档deployment_20261020/first_admission_receipt.json及标准输出。
用户报告已自行发Taylor邮件，未由本助手再发；已创建只读日检
`professor-taylor-md03`，每日Europe/London09:00，仅相关新回复触发记录，
不自动回信／开附件／连接producer或重试实验。

### R001终态：输入传输超时首停，未启动科学比较

首次输入rsync报SSH read timeout／broken pipe／unexpected EOF，命令exit255。
依用户约定立刻STOPPED_NO_RETRY：不重连、不重传、不换host／RunID，不清理
远端部分文件。顺序脚本set-e阻止后续control传输和launch，科学启动次数0。
因此没有本轮测量／预测／图，不是该方法的科学负结果；不能拿旧图冒充新结果。
远端包完整性unknown，先前首检成功仍保留，不回溯改成“未取得远端shell”。

九项本地输入逐件重哈希均不变，包含原图及旧ROI/mask；半深度定义和旧评分
未改。终态观察记录14:52:03UTC，实际错误时刻未打印，未捏造传输／计算耗时。
父归档deployment_20261020/[README_execution.md](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/deployment_20261020/README_execution.md)、
first_stop_receipt.json及transfer_failure.stderr保存证据。后续远端状态／传输
排查或重启均需新的明确授权；本轮止于此，邮件只读定时任务独立继续。
