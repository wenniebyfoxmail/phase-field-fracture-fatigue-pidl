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
