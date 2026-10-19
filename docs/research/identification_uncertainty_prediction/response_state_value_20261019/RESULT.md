# R002 response-state grouped comparison completed — 2026-10-19

Run IU-RESPONSE-STATE-20261019-R002. Exact executed source commit 5ea77160e8bb72a1b3b7a2d91d9bcf09282f5011. One CPU thread, 0 GPU, 236 seconds including rendering, exit 0, no model retry. Bounds 4h / 8GiB unchanged. 19 development-exposed groups, 1144 origins / 2288 horizon-cases.

Current response NMAE 0.880348 improves span+progress 0.982246 by 10.37% (15/19 groups) and persistence 1.036092 by 15.03% (16/19). Full raw response history is worse at 0.921586 (4/19 wins against current). Centered history has lowest aggregate mean 0.873625: 11.06% lower than span+progress (17/19), 15.68% lower than persistence (15/19). Global means alone 0.983595 provide no aggregate net gain, although 14/19 improve; do not discard heterogeneity.

Centered history vs current raw response is only a 0.76% mean improvement, with 8/19 wins and a positive paired-group median difference. Do not claim a universal winner or indispensability of history: current-centered-only was not evaluated. Centered vs raw blocks also change ridge penalty geometry. These are feature contributions, not physical motion correction or a camera-noise identification result.

15 local and producer checks pass. All 27456 saved scores rescored using a separately written direct error formula: maximum difference 0.0. Three original-arm replays each reproduce all 2288 R001 scores exactly. Full 405977117-byte archive retrieved and verified; 342 prediction NPZ identities verified locally, 38 original field figures retrieved. Supplementary centered-field plots cover every group at fixed midpoint H40 on producer; alphabetical first/middle/last copies retrieved for visual inspection, including clear failures. No new fits for plotting.

Common native-current output anchor, 10/40 release stages, unverified physical group independence and no independent crack reference remain. Early persistence remains stronger; release thirds are descriptive, not physical lifetime or an operational selection rule. No physical UQ / untouched-asset / road validation claim.

Disposition: retain current response as a simpler strong baseline and centered statistics as a candidate; focus subsequent design on relative-state representation, temporal necessity and independent reference, rather than raw-history/UQ/architecture expansion. No new run or mailbox action; user sends SCB personally.

[Full scientific interpretation and visual evidence](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-RESPONSE-STATE-20261019-R002/README_analysis.md>). [Run / retrieval receipt](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-RESPONSE-STATE-20261019-R002/final_package.json>). Analysis and plot scripts take optional first argument pointing to this evidence directory; they never fit a model.
