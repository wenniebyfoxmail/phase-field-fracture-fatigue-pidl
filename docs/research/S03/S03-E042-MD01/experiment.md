# E042 — frozen cached geometry to relative-stage prediction

2026-10-18; lightweight exploratory development replay, one trajectory.
User accepts current identification quality and requests advancing downstream.
No new segmentation, training, data acquisition or D01 duplication.

Question: does area extrapolation offer usable signal beyond persistence when
the already-exposed five-frame sequence is used, without error-selected settings?

Use E038 R001 cached v1 masks/metrics for stages18,19,21,22,23. Check E041's
accepted Step19 mask is identical to v1 inside the original E037 common image
band; if not, stop rather than silently mix definitions. Do not use full-ROI
area for forecasting because visible/excluded support differs by stage.

Primary observable: candidate area in frozen E037 forecast_roi_xyxy, pixel².
Other saved length and median 2xEDT mask thickness are descriptive only, not
old half-depth width. No physical-aperture/material-position claim.

All windows, fixed before computation: (18,19)->21, (19,21)->22,
(21,22)->23. Horizon is specified relative-stage difference, not time or kN.
Prediction origin=second history stage. Inputs=two cached preceding areas plus
known requested stage index. Persistence=b; secant=max(0,b+(b-a)*(t-bStage)/
(bStage-aStage)). Show unclipped predictions too. No target-based fitting.

Comparison=absolute error, per window and mean, descriptive only. All three
windows overlap in one development-exposed trajectory, not independent trials.
Third window is the existing E037 query, reproduced not new validation.
Report coverage as calculable windows/three, not segmentation accuracy.

Reuse all nine already-saved E038 settings for area sensitivity with same
setting applied to every stage. Never promote best setting. These are alternative
observation definitions, not independent replicates, truth or confidence bands.
Check original exclusions in common band and report row occupancy (candidate
row presence, not recall). Read only the same five raw crops for source overlays.

Cap: one local cached analysis <=60s CPU/wall; no GPU, new extraction, parameter
sweep or retries of numerical analysis. Save hashes, outputs and figures; preserve
old v1/half-depth/scoring artifacts. If calculation fails, retain receipt.
