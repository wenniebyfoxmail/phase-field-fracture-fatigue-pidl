---
storyline_id: S03
experiment_id: S03-E013-D01
protocol_revision: development-v1
status: development_complete
started_at: 2026-10-11
primary_storyline: S03
---

# Resampling null and one-filter observation repair

## First-principles question

S03-E012-D01 acquired 14 ordered fixed-camera states and evaluated eight
one-step loading-stage forecasts. Secant and half-increment secant worsened
equal-beam MAE by 81.165% and 32.473%, respectively, versus persistence.
All three response series drop after the unwarped first image. Later images
were bilinearly warped, and the dark-ridge operator is sensitive to texture.
The observation process itself may create a misleading first increment.

C0 controlled counterfactual on existing development images: can interpolation
change an observable when the scene is fixed, and can one uniform prefilter
reduce that artifact? No new physical forecasting claim or unseen test.

## Locked null and repair

Use each beam's first fixed 10 kN image and the exact frozen E012 ROI. Compare
the original against a +0.5 working-pixel x/y translation followed by its exact
inverse, using the same bilinear warp. This geometrically reversible operation
changes only discrete resampling, not material/loading state. Evaluate mean
absolute difference of the 16x16 dark-ridge response fields.

One candidate: Gaussian sigma=1 working pixel before the existing response
operator, applied uniformly to both original and null and all 14 stage images.
This scale is a declared engineering antialiasing choice, about 2.8 native px;
it is not tuned to future scores. Do not test more sigmas or thresholds.
Keep every ROI, control correction, saved homography and predictor unchanged.

Report per-beam raw/smoothed null discrepancy and relative reduction. Then
evaluate the same three prefix-only baselines on the smoothed observable for
all eight existing pairs. The new target differs from the old raw observable;
never rank absolute MAEs across those targets as physical accuracy improvement.
Only compare each candidate with persistence on its own target.

No scientific gate is frozen without independent reference/noise calibration.
This is a tested development repair, with possible attenuation of fine crack
signal recorded as a cost. Beam 4's old ROI misses the dominant visible crack;
do not silently fix it inside this one-filter test or call it crack geometry.

## Budget and records

One lightweight CPU run, three null cases and 14 stored-transform replays,
no retrieval, registration refit, training, sigma sweep or formal claim.
Archive local_archive/experiments/S03-E013-D01/runs/S03-E013-D01-R001/.
Evidence: exact null/forecast tables, NPZs, all-three comparison figure, receipt
and README. Outcome selects observation repair/reference work before models.

## Development outcome

R001 completed at clean commit 82ec20cf44ce08afb712cff97b2592db77709d34.
The unchanged-scene roundtrip produced equal-beam raw-field MAE 0.02885560.
Uniform sigma=1 reduced this discrepancy to 0.00491874 (82.954% reduction).
Every beam improved in this null. This demonstrates resampling sensitivity
and a tested one-filter engineering mitigation; it does not prove that all
observed stage changes were caused by interpolation.

On the separately defined smoothed future observable, persistence MAE is
0.00247901, secant 0.00415189 (+67.482%), conservative secant 0.00317407
(+28.038%). All three beams still favour persistence. Absolute errors cannot
be ranked across raw and smoothed targets as physical accuracy, because
smoothing also compresses response and may attenuate thin crack signal.

Research disposition: a controllable observation artifact was identified and
mitigated, while forecast value remains unestablished. Next define a direct
visible-crack centreline/opening-profile reference with a background control.
Correct the Beam 4 ROI under that new reference design, rather than tune
temporal weights on these development outcomes.
