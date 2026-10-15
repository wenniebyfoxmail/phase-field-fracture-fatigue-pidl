# S03-E019-D01 — Beam4 local background correspondence diagnostic

2026-10-15; Storyline S03; `background-translation-v1`; controlled-experiment
DEVELOPMENT C1 diagnostic. User authorises Beam4 background-anchor checks,
before/after position sensitivity, figures and Obsidian update. Keep all old
protocols/outputs, E015 scores, and human-annotation preparation unchanged.

## Question and admissible result

Can one shared local translation, inferred only from background near each
frozen transect, reduce residual mismatch on separate background patches?
Then what happens to half-depth width sensitivity to +/-2 native-pixel location
perturbations? Unit is ONE already-viewed Beam4, four fixed-camera stages
10/30/40/50 kN, 12 transects per stage. This is spatial patch-held-out diagnostic
support within one specimen, NOT independent physical landmarks/generalisation.
No forecast input, prediction or scoring is computed.

First bottleneck: E018 Beam4 location sensitivity median1.442 px versus observed
adjacent-stage-change median0.777 px. Small position perturbations need not
represent actual tracking error: true spatial heterogeneity may persist even
after better background correspondence. Do not demand reduced width sensitivity
as proof that alignment is correct, or fit a transform to make that metric small.

## Frozen evidence and reuse

Use answer-free E018-R001 safe_inputs Beam4 geometry/offsets/H/ordered stage
paths and original JPEGs; verify image size/CRC. Pillow EXIF transpose/L/float32.
Reuse independently checked `independent_d01_halfdepth.py` measure/sampler and
native->working->inverse H->native mapping. Original H is fixed, not re-estimated.
The baseline must reproduce E018 Beam4 width values; comparison happens only
after fitting method/code freeze. No private annotation key or AI labels.

## Anchors fixed before later-stage matching

Let n be frozen transect normal and t=(-n_y,n_x). Patch coordinates are columns
along n, rows along t, 1 native-pixel steps. For EVERY one of the12 first-frame
centres, use 31x31 patches at offsets:

- FIT: (n,t)=(-100,-24),(-100,+24),(+100,-24),(+100,+24).
- CHECK: (-100,-72),(-100,+72),(+100,-72),(+100,+72).

All anchors are outside the +/-60 normal-coordinate measurement window, with
no manual selection by target image or outcomes. FIT and CHECK patches do not
overlap within a transect model; different transect models can share nearby
material, so rows are not independent specimens. Inspect the fixed first-frame
anchor layout (solid31x31 template AND dashed47x47 search envelope, mapped
through actualH0) as an input-capability check before later-stage fitting; if it
crosses beam borders, ruler or visible crack/spall, stop this specification and
record a pre-result amendment rather than silently moving patches.

Template match each anchor in later-stage local47x47 patch after original H:
translation search +/-8 native pixels along n/t; cv2 TM_CCOEFF_NORMED with fixed
quadratic peak refinement in each axis, clipped +/-0.5 at an interior maximum.
Zero/near-constant templates (std<=1 gray level), nonfinite correlations and
search-boundary peaks are unavailable, not zero shifts. Report all NCC peaks,
second-peak separation (outside a 3x3 peak neighbourhood), template std, and
failure status. No correlation cutoff sweep or per-outcome anchor removal.
NCC texture correspondence is an algorithmic proxy, not known physical error.

For stages1..3, fit componentwise median shift from all FOUR available FIT
anchor displacements. Require all4; otherwise local correction unavailable.
Stage0 correction is exactly0 by definition and is excluded from improvement
summaries. No CHECK observations, crack profile, width or forecast value enters
this fit. Use one shared 2D translation for both sides of crack; no separate-side
warps, affine/stretch, rotation, illumination tuning or extra model arms.

## Before/after measurement and missingness

Match CHECK patches independently around the original-H positions, without
recentring their search using the fitted translation. Original residual is
norm(check shift); corrected residual is norm(check shift - FIT median).
Each plot/summary uses predeclared paired available support; report missing
patches/transects out of the original denominator. No cross-specimen CI/test.

Primary descriptive comparison: median paired change in CHECK residual
(after-before, native px) over36 later-stage/transects x4 check patches. Report
full distribution/per-stage variation and available support/144. No qualified
physical tolerance/reference repeatability exists, so no formal metrology
acceptance threshold or claim of physical accuracy. Negative change suggests
this background correspondence proxy improves; positive suggests it does not.

Width: measure SAME E018 half-depth definition at original-H and corrected
sampling points. Correction is fitted ONCE per transect/stage, then applied
unchanged to all five location variants baseline/normal+/-2/tangent+/-2. Never
refit per variant (that would artificially cancel the perturbation). Position
sensitivity is per-stage/transect maximum absolute width difference from that
arm's baseline across all4 shifts, requiring all5valid. Compare paired support
for all48 rows and later36 separately; show every missing result. Report
uncorrected stage-change scale from E018 only as descriptive context, not true
growth. Old forecasting metrics unchanged; no optimisation to preserve52.4%.

Repair map: background residual improves + sensitivity stays large -> preserve
correspondence component, investigate spatial width heterogeneity/selected
material position. Neither improves -> simple shared translation insufficient;
do not raise model freedom on these viewed results. Background proxy unavailable
or ambiguous -> request explicit human background landmarks before physical
registration claims. All outcomes retain completed source/computation work.

## Budget, tests, figures and records

R000 input preparation/first-frame-only capability checks + synthetic tests;
R001 single lightweight real diagnostic after independent read-only code review
bound to frozen commit. Reuse helpers, run synthetic known translation, identity,
constant/boundary/shape tests; verify FIT/CHECK separation and no width feedback.
120s wall AND process CPU, single-thread numerical libraries, partial retained,
fresh output only. No training, remote compute, downloads, external send/push.
Nonfinite coordinates, out-of-image support, missing source identity or malformed
patch schema stop the whole run with partial receipt and original denominators;
do not interpret partial measurements as the completed comparison. Numerical
weak templates and boundary NCC peaks are the declared per-anchor missing cases.
Prepared templates and safe mapping/input snapshot are bound by one combined
digest, verified before target access; source photographs retain size/CRC checks.

Figures: all12 anchors on first frame; all144 later CHECK paired residuals with
per-stage variation; allpaired before/after width sensitivity on same axes;
fixed T6 at allfour stages source strips/profiles before/after, regardless of
outcome. Same-stem explanations and README_analysis required, visible QA and
independent evidence review. Runtime/source/row-count receipts; compact tracked
summary and one dated S03/Obsidian milestone. No global result-level FAIL label
for an unqualified physical reference: retain descriptive component findings.

## First-frame-only amendment v1.1 (before later-stage access)

R000 layout/template inspection at code3892af8 showed T1 CHECK a5
(n=-100,t=+72) contains the curved main crack in its corner. This violates the
background-only input assumption. No later-stage matching/results existed.
Keep its location unchanged but mark it unavailable at every later stage;
retain those three CHECK rows in the original denominator144. Other95
candidates unchanged; no displacement/NCC/width/forecast criterion selected
this exclusion. Re-render first-frame layout/manifest in fresh R000A with red
exclusion before R001. This is a scoped input-capability repair, not a reduced
test denominator or a retrospective improvement of any result.

## Outcome — 2026-10-15, bounded descriptive diagnostic complete

Independent code review passed at cleanac56fdb6 before R001;7 synthetic tests.
R001 completed CPU0.543s/wall0.578s. Four original-image size/CRCs verified;
36/36 later corrections,285/288 anchors and141/144 CHECK support, allthree
missing rows from the frozen T1a5 exclusion.480/480 width variants available.

Primary paired CHECK after-before median=-0.09045px, descriptive small proxy
improvement. Separate before/after medians1.10708/0.91657px are not the primary
paired change. All48 width-sensitivity medians1.44172→1.43529px with paired
change median0; later36 medians1.53720→1.51101px but paired median+0.00976px,
15improved/21worsened. No systematic position-sensitivity reduction. Original
240 variants replayE018 exactly; no change to old forecasting scores.

R002 plot-only wrapping fix at0351bac9; numerical summaries/table unchanged.
Final3 PNG/PDF figures+same-stem notes inspected and independently reviewed.
Evidence Ready for C1 descriptive test, NOT physical registration accuracy.
Disposition: retain modest background-correspondence component; current shared
translation insufficient for width sensitivity, redirect the next observation
test toward spatial width response/material-position reference. No more warp
freedom, target change or architecture added on these results.

Next proposed discriminator (not executed): fixed tangential position-response
curve of unchanged half-depth width with raw source strips, to distinguish
smooth spatial heterogeneity from boundary switching before considering a new
short-segment robust observable. Any changed estimand needs a new protocol;
existing half-depth target remains selected.

[Full analysis and figures](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/runs/S03-E019-D01-R002/analysis/README_analysis.md),
[summary](evidence/summary.json), [independent review](evidence/independent_review.md).
