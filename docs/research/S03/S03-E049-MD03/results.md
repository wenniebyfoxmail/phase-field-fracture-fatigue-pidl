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
