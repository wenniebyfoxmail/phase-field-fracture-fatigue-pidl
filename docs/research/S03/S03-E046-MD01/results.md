# E046 results — 2026-10-18

Execution succeeded; retrieval verified locally. Exploration supports advancing
the simple trend as a working baseline, not a generalisation claim. Accepted
E045 recognition is frozen; no more segmentation tuning this round.

## Same observer, separate new-version score

History22/23 measured once with immutable E045 rule and stage23 anchor; accepted
24/25/26 masks reused exactly. A sequence5379/5057/5755/7361/9191px²;
L250/250/250/250/240 rows; M21.516/20.228/23.020/29.444/38.295833 pixels per
occupied row. Stage22's new observation differs from its old observer result;
old history measurements were NOT silently mixed into this new replay.

| History→target | Observed A | Hold prediction / AE | Area trend prediction / AE | Separated prediction / AE | Gain vs hold |
|---|---:|---:|---:|---:|---:|
|22,23→24|5755|5057 / 698|4735 / 1020|4735 / 1020|−322|
|23,24→25|7361|5755 / 1606|6453 / 908|6453 / 908|+698|
|24,25→26|9191|7361 / 1830|8967 / 224|8967 / 224|+1606|

All areas/errors in native pixel². Every method calculable3/3. MAE
persistence1378, area trend717.333333, separated717.333333: −47.94388% relative
to persistence. Two wins, one loss. Trend's first loss follows falling22→23
measurement then rising24; no image/parameter selection to repair it.

All origin histories have L250, so separated prediction equals area secant
algebraically (no caps active). No incremental separated-representation gain.
Raw float discrepancy at most1.819e−12px²; the producer's literal `==` boolean
is false due to roundoff, not a method difference; see QA, leave raw output intact.

## Evidence and bounds

RunR0010.9829s wall/0.9653s CPU, clean producer
`d8752569a972fd8d0cba047968008b60b0008d0b`;245 protected files unchanged,
3 target mask copies identical,3 saved-prediction-before-target-read chains.
Synthetic tests plus separate arithmetic/hash checks passed. R002 generated
two PNG/PDF figures with two valid sidecars; both actual PNGs inspected.

This is one already-exposed trajectory and3overlapping development windows.
Saving predictions first checks program flow, not retrospective blindness.
Current-image observer uses each frame only for its own measurement; stage23
anchor is available at all origins. Stage index is not actual time/load.
Pixel area/L/M are not physical aperture/length; targets are this observer's
measurements, not independent truth. Residual shadows/pores and26's10emptyrows
remain. No predicted future spatial mask was produced. E044/older scores,
half-depth definition and all prior masks are unchanged; do not compare old/new
MAE as if truth were held fixed.

All five source/mask bands and every forecast:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E046-MD01/runs/S03-E046-MD01-R001/README_analysis.md`.

## Next decision

Retain simple area trend with persistence control; retain L/M as diagnostics,
not additional predictive novelty here. Next propose metadata-fixed next3
complete consecutive stages, same observer/ROI, save each forecast before
evaluating the stage. Do not select favourable growth windows or enlarge model
first. No new-stage image opened in E046.
