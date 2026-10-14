# S03-E018-D01 — independent half-depth computation and location audit

2026-10-15; Storyline S03; protocol `independent-half-depth-v1`.
Controlled-experiment DEVELOPMENT diagnostic, C1 computation/coordinate audit;
not physical metrology or a new forecasting evaluation. User chooses to retain
the E015 half-depth observable and explicitly requests independent review.
Old E015/E016/E017 data, definitions, scores and human-preparation files are read-only.

## Question and boundaries

Does an independently written implementation recover the existing half-depth
width from the SAME stored profile, and how sensitive is that observable to
small changes in sampling position? Physical unit is beam; descriptive rows
are beam/stage/transect (14 stages, 168 profiles; three previously viewed beams).
No new generalisation, physical scale, human truth, phase-field state or future
load-availability claim. No new forecast score or predictor is calculated.

## Evidence and allowed inputs

- E015-D01-R001 `Beam{4,5,6}_profiles.npz`: stored normal offsets, profiles and
  nominal loads for implementation; widths and original CSV accessible only
  after independent implementation is frozen, for comparison.
- E015-D01-R000 `first_frame_transects_lock.json`: fixed centers/normals/shapes.
- E012-D01-R001 ordered manifest, raw 14 IB fixed images, stored homographies.
- Old E015 summary/forecast metrics may explain history ONLY, never retuned.
- No E016 private blind key or human/AI labels used. No fitted transforms,
  changed ROI, new crack detector or parameter search.

## Operational definition supplied to independent implementer

Normal offsets s=-60..60 at 0.25 native-pixel spacing. Take the pointwise median
of five tangent lines t=-2,-1,0,1,2, with tangent=(-n_y,n_x). Fit linear background
through the median intensities of left (s<=-45) and right (s>=45) shoulders at
their median s coordinates. Deficit=background-intensity. Shoulder noise is
1.4826 times median absolute deviation of deficit on both shoulders. Peak is
the first maximum in |s|<=15. Require depth>=max(10 gray levels,3*noise).
Walk left/right from peak until below half the depth; if either walk reaches
the window endpoint, report censored. Linearly interpolate crossings. Width is
right-left; width<1 pixel is resolution-limited. Invalid values remain missing.

Geometry: stored H maps stage working pixels to origin working pixels. Resize
centers obey x_work=(x_native+0.5)*scale_x-0.5 independently for y.
Native-origin sampling points must be mapped backwards to stage source pixels.
Independent path should implement this as native->working->inverse H->native,
rather than importing the old conjugation/sampler functions. Compare this
separate calculation with algebraically conjugated mapping for all sampled
points. Same-H roundtrip is a software consistency check, NOT registration
accuracy against a physical fiducial.

OpenCV INTER_LINEAR quantises fractional coordinates to 1/32 pixel. For source
profile replay, implement manual bilinear sampling at float32-coordinate/1/32
fractions and retain float32 image/profile semantics; also report unquantised
continuous bilinear sampling as an interpolation diagnostic, not a replacement
observable. Do not optimise interpolation to improve old forecasts.
Image decoding is fixed to Pillow EXIF-transpose, conversion to L, and float32
array; switching to a different JPEG/grayscale decoder would confound this test.

## Predeclared tests and outcome-to-repair map

Primary: all 168 stored-profile validities match and maximum absolute width
disagreement <=1e-8 native pixels. This tolerance is for deterministic float64
arithmetic over identical float32 input, many orders below the 0.25-pixel sample
step; it is NOT a physical accuracy requirement. If validity or width disagrees,
stop qualification and localise numerical/definition differences. This is
feasible because the input and specified functional are deterministic.

Diagnostics (do not rescue primary):

1. Per-beam max/median width differences and every-row differences.
2. Independent coordinate mapping/roundtrip residuals over all 14-stage sampling
   grids; exact/manual-quantised and continuous replay differences reported
   separately, with no physical registration-error label.
3. ALL five center variants, fixed before execution: baseline, normal +/-2,
   tangent +/-2 native pixels. Five tangent lines remain centered on each variant.
   Report missingness, per-profile max absolute width difference across all four
   shifted variants, per-beam distributions, and typical absolute adjacent-stage
   changes from the unchanged stored widths. These are position-sensitivity
   diagnostics, not confidence intervals, repeatability estimates or known noise.
   The max statistic requires all five variants valid; incomplete groups remain
   missing and are counted separately. Typical stage change is each beam's median
   absolute adjacent-stage difference over all 12 transects and all adjacent pairs.
4. Fixed image/profile examples: transect 6, first and last fixed stage of every
   beam regardless of result; show source sampling location and half-depth
   crossings together, not AI boundaries or inferred mm scale.

If source replay mismatches: isolate coordinate convention, quantisation or
image decode, without changing old stored values. If position sensitivity is
comparable to typical stage change: keep the computed observable but prioritise
local correspondence/reference checking; no architecture expansion. If all
software checks agree: computation reproducibility only, reference accuracy
still pending. Component findings are retained regardless of primary outcome.

## Independence, budget and readiness

One fresh-context implementer sees the definition and allowed inputs, not old
implementation or old widths before its code freeze. A separate read-only code
review checks exact implementation and this protocol BEFORE data execution.
After freeze, joins to original outputs are allowed. Same-model agents and
shared images/H are explicitly limited independence, not independent physical
reference. Do not call implementation replay blind annotation or AI metrology.

R000: code preparation/unit sanity and read-only review. R001: one lightweight
offline computation (budget 120 s CPU, no training/remote producer/sweeps),
fresh local archive. Stop for missing identity, sample out of bounds, definition
ambiguity, review blocker or budget limit; preserve partial outputs. Any coding
repair after execution receives fresh code identity and Run, not overwrite.
Minimum evidence: all-row tables, summary, source paths, exposure attestation,
code review, runtime receipt, computation agreement figure, all-location
sensitivity figure and fixed-source/profile examples with explanation sidecars.
Source retrieval is local; no external send/push is authorised by this request.

## Pre-execution amendment 2026-10-15 — protocol v1.1

First implementer preparation R000 was stopped BEFORE code/data execution:
it inadvertently printed raw lock metadata, exposing Beam4's 12 and Beam5's
first five `origin_qc` historical widths/crossings. Its self-report is retained;
no implementation from that context qualifies as independent. Raw containers
include answer fields, so merely instructing field selection is inadequate.

Replacement implementer gets a fresh context and only a sanitised R001 input
directory prepared by `prepare_independent_d01_inputs.py`: per-beam offsets,
profiles, nominal loads and H; geometry id/center/normal/shapes; stage image
paths/size/CRC. No origin_qc, widths, deficits, forecast arrays or scores in
these files. Raw code/outputs remain prohibited before implementation freeze.
R001 is input preparation; R002 is the one data execution after code review.
Mathematical definition, primary criterion, variants and 120s execution budget
are unchanged. No E018 numerical results existed at this amendment.
