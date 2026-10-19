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
