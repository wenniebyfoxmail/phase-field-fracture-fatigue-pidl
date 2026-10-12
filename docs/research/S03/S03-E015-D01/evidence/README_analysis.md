# E015-D01 profile measurement and conditional next-stage diagnostic

Question: does explicitly crack-local state reveal a stage-growth signal that
texture-averaged dark-ridge grids obscured? Controlled RC beams, development
only. This is not a road, fatigue, physical-aperture or generalisation result.

## Source and computation

Source D01 Mendeley v4, DOI 10.17632/z3yc9z84tk.4. Four/six/four verified IB
fixed-camera images reused from `S03-E012-D01-R001/raw_images`; 14 unique stages.
Original source locations are in `profile_measurements.csv`. Homographies are
replayed, NOT re-estimated. Native pixel-center resize transforms are applied.
No force-camera synchronization, final-state imputation or source rewriting.

Measurement commit `9e23d23c633f0534cb6d33eed22087b121195b43`, protocol
`development-v1`. R000 locks 12 origin-only assisted centers per beam; R001
directly samples all stages. Native grayscale, median five parallel profiles,
local shoulder background and connected half-depth crossings. No global
photometric normalization/added Gaussian filter. Half-depth width is an IMAGE
observable in first-frame native pixels, not physical width. Sample spacing
0.25 pixels does not confer subpixel physical accuracy. Normals are approximate
and fixed; irregular boundaries, texture, blur and local registration matter.

## Reading order and exact scored evidence

1. R000 `first_frame_transects.png`: all first-frame path/sample locations;
   Beam 4 right crack corrected. Green = first-frame detector QC, NOT truth.
2. `first_last_width_readout.png`: recorded half-depth crossings on original
   first/last images of ALL beams. Display choices fixed before scoring; no
   measurement refit. Cyan = algorithmic crossings, not human boundary labels.
3. `transverse_profiles.png`: ALL stages at fixed ID 6 in every beam; gray and
   local intensity deficit share scales. Crack opening/contrast are separable
   from bulk grayscale changes only diagnostically, not fully identified.
4. `crack_width_trajectories.png`: all 36 transects and stage observations;
   common color/width scales, every transect gray line and median black line.
5. `profile_forecast_comparison.png`: exact same-support MAEs for ALL eight
   origins and all three arms, common y scale. Beam 4 final secant origin is
   slightly worse than persistence; don't hide it in the equal-beam average.

`Beam*_profiles.npz`, `profile_measurements.csv`, `individual_forecasts.csv`,
`forecast_metrics.csv` and `summary.json` are authoritative. Mean across
transects within pair -> mean pairs within beam -> equal mean over three beams.
No random split; transects/pairs are NOT independent specimens. Predictions
use last two measured states and scheduled next nominal load only, not future
imagery. Future homography is used to MEASURE the target, not as predictor input.
This is observed-history one-step conditional prediction, not autonomous rollout.

## Results and limits

- 168/168 crack profiles QC-valid, 96/96 origin-eligible pair-transects scored;
  no abstention or zero-filled failures in this run.
- Equal-beam MAE: persistence 0.923453 px; secant 0.439486 px; half-secant
  0.556366 px. Secant 52.408% lower than persistence, half-secant 39.752% lower.
  All three beam means favor secant; seven/eight origins do. These are errors
  against this new image observable, NOT physical reference errors. Old E012/
  E013 targets and verdicts remain unchanged and are not numerically ranked
  against this different estimand.
- First->last width medians: Beam 4 29.10->32.17; Beam 5 6.83->10.82;
  Beam 6 12.07->14.80 native pixels. Initial states already show substantial
  cracks; do NOT imply crack initiation from pristine material.
- Background controls: 56/168 detections (20/48,32/72,4/48). Thus this threshold
  is NOT a qualified crack identifier. Across all profiles median relative
  contrast is 0.884 at guided crack locations vs 0.041 at controls; contrast
  explains a repair candidate, not a post-hoc new detector gate.
- Median max +/-2px tangential-shift width sensitivity is 1.44/0.75/0.70 px;
  median absolute stage changes 0.78/0.87/0.95 px. Beam 4 sensitivity exceeds
  its typical stage increment. These are spatial sensitivities, not independent
  repeatability estimates or calibrated error bars. Global projective alignment
  does not establish local edge displacement accuracy.
- Three development beams, no independent boundary truth, no held-out beam,
  no independently reviewed Code/Evidence Ready status. Approximate normals
  and local peak selection can select a spall/branch or textured depression.

## Interpretation / next action

Allowed: the new assisted crack-local observable preserves a load-stage signal,
and its simple history baseline beats persistence in this diagnostic. This
supports continuing this measurement/forecast chain rather than abandoning
all history-based prediction after E012/E013's texture-target negative results.

Blocked: calibrated millimeter aperture, automatic segmentation, physical
prediction accuracy improved 52%, held-out or road/fatigue forecasting, state
sufficiency, publication claim. Formal scientific verdict remains unassigned
(`DEVELOPMENT_DIAGNOSTIC_ONLY`), disposition **repair then advance**.

Next decisive test: independent first/last boundary checks on these fixed
transects plus local alignment/tangent repeatability; preserve this pilot and
freeze the reference protocol before scoring. Prefer this narrow validation
over a new temporal architecture. If confirmed, keep secant as the benchmark
and test bounded continuation on fresh qualified specimens/evidence.

QA: visually inspected all four initial figures; locked paths cross intended
crack segments, every stage loads correctly, no blank panels, common scales,
all eight origin comparisons and the Beam 4 exception visible. First/last
readout inspected after rendering: all six crops contain the intended crack,
72 cyan spans match stored measurements and point IDs, no blank panels.
Execution 6.78 seconds, local retrieval
verified; source CRCs/size rechecked. No new training or remote compute.
