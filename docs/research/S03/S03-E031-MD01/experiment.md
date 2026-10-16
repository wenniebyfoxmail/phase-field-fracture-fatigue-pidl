# S03-E031-MD01 — three-stage relative-index half-depth pilot

2026-10-16; S03; protocol `relative-stage-halfdepth-v1`; base7a7be14.
User explicitly approves relative-stage task, rule-before-images, three-stage
minimum comparison, unchanged half-depth width, figures and Obsidian sync.
This NEW task does not relabel Step as kN or replace old L* cases/scores.
C3 exploratory image-observable continuation, controlled experiment; one
record/specimen identity across D01 unresolved, NOT independent-beam validation.

## Pre-image selection and information rule

Use the LAST THREE consecutive explicitly labelled stages with exactly three
fixed-camera IDs each:27/28/29, not the previously unapproved first-three idea.
Within each choose the smallest literal image ID:403/406/409. Later stages
are selected a priori to improve the chance of an established visible crack,
based on progressive loading only, not observed widths, clarity or errors.
No replacement frames/stages if any selected observation is invalid.

Official MD01 DOI10.17632/dns97tfdjn.1 v1, Fixed Camera folder
81a356f0-50c5-4918-94ee-f9da09867449. Fields previously verified from
Data acquisition B85:B93 and G85:G93 plus official file metadata:

| Role | Step | Filename | Official file ID |
|---|---:|---|---|
| history1 |27| IMG_0403.JPG |114a4bef-6112-4a47-8fae-c0ca3078c873|
| history2 / origin |28| IMG_0406.JPG |b0c45c2e-05be-4336-9321-ce179967f5f2|
| target |29| IMG_0409.JPG |09d14bf8-a32d-4fca-bdfd-260514384f79|

Commit this rule BEFORE any selected image acquisition/decoding. Acquire/view
ONLY403/406 initially. On403 choose the visually dominant central crack branch
at approximately mid-height of the beam face, not a scratch/ruler/annotation;
derive one normal from that branch's local tangent. This is observer-assisted
history selection, not algorithm-unexposed annotation or physical truth.
If no defensible crack is visible, retain a missing outcome; do not select a
texture peak just to obtain a width. Save centre/normal/background patch centres
before numeric history measurement. Refinement within the original +/-15px
core is allowed once on403 only; record rough and refined position.

Use one transect. On403 fix background patch centres near, but off, the crack
and annotations, preferably either side at similar beam height. Use four81px
square patches and +/-30px translation-only normalized cross-correlation;
median native dx/dy maps first-image positions into each later image. At least
three patches must fit with correlation>=.6; otherwise correspondence missing.
Report spread of patch translations and scores, no tuning to width agreement.
Later-stage background pixels can locate the reference measurement, never
change saved geometry, history widths or predicted values. Fixed-camera
translation-only correspondence remains an assumption, not physical validation.

Save numeric history, immutable geometry and BOTH predictions to a closed file
BEFORE409 is downloaded/decoded. Then acquire409, apply the SAME geometry and
background rule and score once. No target-driven normal, support or peak shift.
Widths use native first-image pixels; stage index is ordered label, not time,
kN, cycles or equal physical exposure. No response workbook data is opened.

## Measurement, comparison and attainable result

Reuse d01_crack_profile_diagnostic.sample_profile/measure: native grayscale,
offsets-60:.25:60, five tangent lines-2:-1:0:1:2 and median; straight shoulder
background through medians for |s|>=45; dominant deficit peak |s|<=15,
half-depth interpolated crossings, depth>=max(10,3*MADnoise), width>=1px,
finite uncensored support. Preserve the width definition and invalid reasons.
This is apparent optical width, not independently annotated or physical mm.

Persistence=w28. Candidate=clip(2*w28-w27,0,120) using the OLD numeric forecast
helper with indices[27,28], query29; those arguments are INDEX COORDINATES,
not kN despite the old helper's parameter names. Save raw and clipped prediction.
One primary criterion: candidate absolute error minus persistence absolute
error on the SAME valid target profile. <0 is directional development benefit,
0 tie, >0 no candidate benefit for this query. No arbitrary improvement margin,
significance or all-case victory; one opportunity is not replication evidence.
Reference noise/repeatability are unestimated: small differences stay tentative.
If history/target/correspondence missing: null score with reason, not zero or
scientific FAIL. Report valid profiles/3, predictions/2, scored opportunities/1.
Image availability and measurable history are component milestones; keep these
even if secant loses. A model miss selects a new bounded diagnostic, not tuning
the viewed result or changing the width definition.

## Execution and review

One lightweight Mac CPU image-analysis pilot, no training/GPU/remote producer.
At most3JPEGs/~60MB, one transect,2 analytic predictions; numerical passes
history and target each capped120s (downloads separately <=60s each).
No alternate stages, multiviews, old-eight replay, sweep or independent-beam claim.
Reuse tested sampler/measure/forecast. Synthetic sanity + independent read-only
review of exact new runner, protocol, data roles and timing before measurement.
Image acquisition/first-history visual geometry may precede numeric admission.
Fresh Run IDs and receipt contain host/PID/runtime/commit/dirty/command/time,
source sizes/official content identity, geometry and prediction-save chronology.

Minimum evidence: rule commit,3source identities, geometry, closed history-only
predictions,3profiles/QC/arrays, reference and both absolute errors, patch matches,
one all-three original crop/mapped sampling comparison, profile figure and
observed/predicted width points plus explicit error/coverage view. No pooled
mean bar or invented CI. All examples shown; PNG/PDF and visible figure QA.
README_analysis.md states provenance, reading order, permitted and blocked claim.
Independent saved-output review before closing. Obsidian route and outcome
milestones reuse the existing multimodal task note and one Roadmap entry.

Outcome/disposition: prepared; images not yet accessed at protocol creation.

## Pre-target amendment — history-centered-background-search-v1.1

AFTER R001 history prediction save, BEFORE target409 acquisition/viewing:
the observed background median displacement from403 to406 is approximately
(0.235,22.930)native px. The original first-position-centered +/-30 search
could censor a continued shift, even though adjacent-stage movement remains
within the original window. This is a predictable search-support limitation,
not a viewed target error. Keep the same four first-history templates,81px
patch size, +/-30 radius, NCC threshold, median estimator, geometry, width
definition and all saved predictions. For409 ONLY, centre the search window
at the frozen last-history dx/dy rounded to nearest integer: (0,23)px. Return
TOTAL first-to-target displacement, not incremental displacement. No target
feedback or width-based adjustment. Search support is now dx[-30,30],dy[-7,53]
relative to the first frame. A boundary result remains invalid. Do not rerun
R001 or rewrite its snapshot. Fresh review required for this matching delta
before409 acquisition. Original protocol/results retained as history.
