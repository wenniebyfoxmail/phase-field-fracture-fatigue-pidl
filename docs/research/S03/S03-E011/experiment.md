---
storyline_id: S03
experiment_id: S03-E011
protocol_revision: development-v1
status: development
started_at: 2026-10-11
primary_storyline: S03
---

# Fixed-camera loading-stage observation forecasting: first-principles baseline

## Dataset-first decision

The released IB fixed-camera images map uniquely to the non-final named load
stops in S03-E004's workbook-derived load_stop_mapping.csv. Beam 4 has 10/30/40/50
kN labels; Beam 5 has 10/20/30/40/50/60; Beam 6 has 10/20/30/40. Filename time
order and nominal load-label order agree. These are 14 states of three beams,
not independent specimens. The 6 endpoints are already available; retrieve
exactly the 8 missing intermediate images from the frozen released-v4 manifest.

Exclude all three final stop-machine frames before new pixel access: they lack
numeric scheduled-stage labels and were outside the filtered machine coverage.
Do not use the conflicting moving-camera final records. No actual force-series
join or precise seconds horizon is needed for this new ordinal/scheduled-stage
question. S03-E004's original broad synchronization verdict is retained.

## First-principles decomposition

Observed image = scene geometry + photometry + acquisition noise.
Before adding a temporal model, establish a consistent coordinate plane and
control photometry; then ask whether the last observed increment carries useful
information about the next scheduled-stage observation.

Use each beam's first (10 kN) fixed state as the canonical plane. Reuse the
existing SIFT/projective registration only to express observations in that
plane. Targets may be registered when scored; neither their pixels nor their
transforms enter the origin forecast. No common mask fitted using future images.

Select observation and control rectangles solely on the already-viewed first
state. Native-pixel boxes [x0,y0,x1,y1]:

| Beam | Visible-crack neighbourhood | Background-control beam-face patch |
|---|---|---|
| 4 | [3300,1200,4450,2750] | [1800,1400,2400,2300] |
| 5 | [3100,1350,4650,2750] | [1500,1400,2300,2400] |
| 6 | [2200,1350,3900,2900] | [1000,1400,1700,2300] |

These rectangles are observer-selected regions, not independent crack masks.
They avoid ruler/apparatus/handwriting as far as visible in the first state;
holes and texture can still respond. Keep their locations for every stage.

Normalize each registered gray image to the first state's control-patch median
and interquartile range with one affine correction, clipping to [0,255]. Apply
the existing multiscale dark-ridge response. Divide the crack-neighbourhood box
into 16x16 cells; use the mean response per cell as the explicit target.
This is an image-observable estimand, not physical crack geometry/width truth.
Also retain unnormalized response as a photometric diagnostic, not a new arm.

## Origin, information and comparisons

Origin: the current observed stage with at least one previous stage.
Horizon: the next included nominal loading stage (not seconds/cycles/RUL).
Allowed: current/past response fields and stage labels, and the next nominal
stage as a scheduled condition. Actual future measured force is never input.
One-step observed-history updates; no autonomous rollout claim.

Persistence: r_hat_next = r_current.
Secant: r_hat_next = r_current + (r_current-r_previous)*dL_next/dL_previous.
Conservative secant: same increment multiplied by 0.5, specified before results.
All predictions are clipped to the known response range [0,1]. No fit/sweep.
The conservative arm tests one noise-amplification repair; it cannot be chosen
post hoc and promoted on these viewed/development outcomes.

Evaluate 8 matched origin-target pairs (2/4/2 per beam). Report cell-mean MAE
against the future observed response and equal-beam mean losses. There is no
defensible reference-noise-based primary claim threshold yet: report diagnostic
improvement over persistence, not a confirmatory scientific PASS/FAIL.

## Necessary interpretation checks and component milestones

- Unique image/beam/stage identities; increasing filename times and load labels.
- Exact manifest CRC/size/decode; reuse rather than redownload existing pixels.
- Finite non-empty observation/control boxes; at least 99% support in each box.
- Existing fixed-camera registration admission (inliers, ratio, reprojection).
- Forecast API accepts only prefix observations; future-target permutation must
  leave forecasts unchanged. Test unequal loading increments explicitly.
- All negative/missing outcomes are retained; no score-based stage exclusion.

Registration-noise sensitivity: shift each response by +/-1 working pixel in
x/y, report cell-mean perturbation. This brackets pixel-registration sensitivity
only; it does not estimate total acquisition/annotation uncertainty.

Progress: acquisition -> origin-only ROI -> stage observations -> leak-safe
baseline prediction -> exact future comparisons -> all-beam visualization.
If secant amplifies noise, compare the preregistered conservative arm.
If both miss, identify observable changes and registration/photometric sensitivity
before any encoder expansion. This run is exploratory development, not a formal
reviewed C3 crack-forecast result; independent reference/review remain pending.

## Budget, evidence and scope

One deterministic CPU development run, <=10 minutes, 8 new JPEG acquisitions,
no training, no full archive. Stop on identity/registration/support failure;
record partial outputs and do not silently change the protocol.
Owner S03-E011; branch codex/crackmnist-tokenizer-mvp, base a51bf97.
Archive local_archive/experiments/S03-E011/runs/S03-E011-R001/.
Minimum: selection/sequence receipts, origin ROIs, all-stage image montage,
response trajectory, per-pair predictions/MAEs, all-beam comparison, NPZs,
receipt and README. Unseen specimens, road transfer, fatigue and physical crack
accuracy are outside scope. Preserve all earlier protocols and verdicts.
