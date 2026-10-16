# Independent evidence review — 2026-10-16

Reviewer `/root/md01_pilot_review`, separate code-admission and output-review
turns; read-only, no additional trials, geometry changes or external access.

## Numeric reproduction

Independent half-depth implementation (`independent_d01_halfdepth.measure`,
not production measure) recomputed all3saved profiles. Independently assembled
sampling grids and hand-coded1/32quantized bilinear samples from all3original
photos reconstruct every saved profile sample with maximum difference0.
All3widths, both predictions, target errors and their difference reproduce
with difference0. Source files match official byte sizes/content identities,
all decoded shape4000x6000. Geometry/history records match the closed snapshot.

| Quantity | Independent value (native px) |
|---|---:|
| w27 |38.44866535365738|
| w28 |42.677985344650466|
| w29 |47.34982708587424|
| persistence prediction |42.677985344650466|
| secant prediction |46.90730533564355|
| persistence absolute error |4.671841741223773|
| secant absolute error |0.4425217502306893|
| candidate-minus-baseline error |−4.229319990993083|

## Roles and chronology

Selection commit22d5e04 at21:36:10UTC precedes first image local file time
21:36:30. Prediction snapshot saved21:39:40.326312UTC; pre-target amendment
commit68fbc24 at21:40:21; target file time21:40:55.803618; target run begins
21:41:01.962840. This supports recorded local workflow ordering, not independent
external timing proof or cross-project never-seen status.

R001 actual cleanb4a1c7a numeric file matches admitted86e1fa5; R002 actual
clean88ee144 matches amended admission68fbc24. No history recomputation or
prediction overwrite after target access. Profile/score coverage3/3and1/1.

## Interpretation and visualization

Background residual maxima2.6452457841/4.7341532958px independently reproduced.
Left/right background displacements systematically differ; one translation is
not a complete local deformation model. Position residual is not width error:
do not subtract4.734px from4.229px gain or declare the gain either physically
validated or automatically cancelled. Supports directional gain for this fixed
one-case optical-width workflow; spatial robustness remains unresolved.

Reviewer opened finalR004 F01/F02/F03colour PNGs andF03gray: source roles,
sampling, half-depth crossings, numerical labels, relative-index units, RunIDs,
one-case limitations and ordinal-line wording clear. No clipped/overlapping
labels or missing glyphs; marker/line redundancy survives grayscale. No visual
blocker. Parent independently checked all3PDF fonts with pdffonts: CID TrueType
embedded/subset/Unicode all yes, despite generic checker's warning.

## Decision

No numerical/evidence/visual blocker for the bounded pilot. Retain the measured
directional benefit, not physical-width accuracy or independent-beam validation.
Next proposal: fixed, two-sided-background-informed position sensitivity using
these same3photos, without selecting by width error or rewriting these scores.
That diagnostic has not been executed.
