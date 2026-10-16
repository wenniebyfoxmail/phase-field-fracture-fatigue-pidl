# S03-E030-D01 — fixed background centre half-depth profile comparison

2026-10-16; S03; protocol `T1-fixed-background-sampling-v1`; base d4dd8cc.
C2 optical-measurement diagnostic, controlled-experiment/viewed-development.
User authorises saving the three E029 primary positions BEFORE width access,
then comparing 30/40/50kN T1 profiles, widths and remaining conditional-query
error. No new independent specimen, physical reference or forecast validation.

## Frozen decision and information

Use exactly [fixed_positions.json](fixed_positions.json): E029 all17 affine
centre n/t vectors at all3stages, additive to the original-H centre. The file
is saved before E030 opens any width/profile/image. Researcher has seen earlier
E026/E028 widths/errors; this is NOT blind selection. No LOO, flags-clear,
best-anchor, offset search, registration, fit or alternative correction.

Single descriptive question: how does this ONE background-only estimate change
the existing half-depth observable and the remaining signed T1 Q50 error
relative to oldFIT? Primary output is signed error change, with stage-width
decomposition. No physical/scientific pass threshold: report decrease, increase
or unavailable without calling the entire route a success/failure.

Three fixed arms: original_H=(0,0), oldFIT from E019, fixed_background from E029.
Exactly9profiles from3existing E012 CRC/size-verified JPEGs (B4 stage1/2/3).
Use E018 safe geometry/H, original normal/centre, offsets -60:0.25:60,
five parallel lines at tangent -2,-1,0,1,2 and median; unchanged 1/32float32
bilinear, shoulder medians |s|>=45, core peak |s|<=15, half-depth crossings,
depth/noise/resolution/censoring QC. Unit native first-frame px, not physical mm.
Do not change width definition, old scores, E025 interface or any earlier file.

Check primary position/source identity before any image or width access.
Reproduce both original_H and oldFIT3widths plus query values against E026
nominal results to1e-8px software tolerance before interpreting new differences.
Mismatch stops interpretation; no adjustment to force agreement.
Invalid new measurements retain null/reason; do not move to a valid neighbour.
Both baseline3/3 and new3/3 coverage are reported, no unsupported zero fill.

For each available3stage arm: supplied nominal Q50, rawsecant=2*w40-w30,
prediction=clip(rawsecant,0,120), error=prediction-w50; also persistence=w40.
These are diagnostic recomputations, not overwriting any original score.
Separate prediction change (history widths) from reference change (w50).
Against oldFIT, delta_error=-delta_w30+2*delta_w40-delta_w50+delta_clip;
keep all terms. Stage increments distinguish retained down/up trend from change
of apparent optical trend, not physical narrowing/reopening or proven causality.

## Execution and minimum evidence

One Mac lightweight CPU R001,60s wall/CPU cap,3existing JPEGs, noGPU/network.
No training, acquisition, sealed target access, eight-case replay or tuning.
Code synthetic tests and independent read-only admission before image sampling;
review exact commit/protocol/position lock and data paths. Record identity,
command/host/PID/runtime/source receipts, hashes for the fixed external input
snapshot and oldscore files; verify oldscore content unchanged after execution.

Save9profile records/arrays,9measurements with QC,3query summaries, exact
decomposition and input/source identities. R002 saved-output-only renderer:
(1) all3stage deficits/half-levels/crossings for all3arms;
(2) width trajectories and supplied-Q50 residual comparison;
(3) same-scale original-image local strips and fixed sampling-band overlays,
plus stage contributions. All examples fixedT1/all3stages, no error ranking.
PNG/PDF/grayscale, figure-set README and same-stem notes; programmatic and
actual visual QA. Independent evidence calculation/visual review before closure.

If residual decreases: retain this candidate for subsequent measurement checks,
not declare correct physical coordinates or improved generalisation. If stays
similar/increases: record that this stable background estimator does not remove
the local mismatch; do not replace it by an error-minimising alternative.
Either outcome next separates background-transfer validity from optical-trend
modelling; no new model or width-definition change automatically follows.

Obsidian: reuse one existing task note, route/result milestones and oneRoadmap
status; canonical S03 track then frontier/navigation. Registration: prepared;
fixed position file saved, no E030 width sampling yet.

## Outcome — 2026-10-16

Disposition: retain this single background estimator as a documented optical
measurement candidate, not a replacement oldscore or a certified position.
The remaining mismatch decreases but is not removed; do not tune another
position to eliminate it. The local down/up optical trend persists.

Position lock committed8218e32 before this run; numeric codefb04eb8 admitted
independently and unchanged through render additions/currenta6c8f29. R001
clean a6c8f2945d1f412616ceae7f2f823574dd84f758 succeeded, retrieved locally,
wall.241790s/CPU.226654s,3CRC/size-verified existing JPEGs,9/9valid profiles.
Position snapshot written/closed before width/image access; no LOO/quality
support selection, fitting, matching, search, target acquisition or training.
Both original-H and oldFIT query/width fields reproduce E026 at1e-8 software
tolerance. E025 six oldscore files unchanged before/after/current content check.

| Arm | w30 (px) | w40 (px) | w50 (px) | Signed secant error (px) | Signed persistence error (px) |
|---|---:|---:|---:|---:|---:|
| Original H | 15.252448283 | 11.509941373 | 13.834022586 | -6.066588124 | -2.324081214 |
| Old FIT | 16.382909772 | 16.141970936 | 16.787658189 | -.886626089 | -.645687253 |
| Fixed background | 16.324193492 | 16.196840965 | 16.762657830 | -.693169393 | -.565816866 |

All three arms are evaluated against THEIR OWN same-definition width at50kN,
not a shared physical reference. Fixed-background minus oldFIT widths are
-.058716280,+.054870028,-.025000359px. Exact signed error-change contributions
-dw30=+.058716280,2dw40=+.109740057,-dw50=+.025000359,clipchange=0, total
+.193456696px toward zero. Of this, prediction changes+.168456337 and reference
changes-.025000359px. This is NOT all an improvement in prediction accuracy
against an unchanged target; no percentage generalisation claim follows.

Fixed history increment=-.127352528px and next increment=+.565816866px:
the down/up optical response survives this one stable background location.
Error=-.693169393 remains, and its absolute size exceeds persistence .565816866
at this local query. Do not convert a reduced miss into secant superiority,
physical crack narrowing/reopening, reliable background-to-edge transfer or
independent validation. Earlier global eight-case results remain untouched.

Eight E030 synthetic tests plus10reused E028 regression tests pass. Independent
reviewer hand-implemented inverse-H,1/32bilinear/five-line median and shoulder/
half-depth measurement without calling the new producer/oldmeasure core:
all9profile/deficit/background arrays, widths/crossings/peak/depth/noise,
3arm query values and all stage/clip/prediction/reference contributions reproduce
with maximum difference0. Input/source and unchanged oldscore identities verified.
Saved-order code plus output chronology supports the scoped saving requirement,
not process-level blindness; earlier results were already viewed.

R002 render-only clean a6c8f29 from saved R001 CSV/NPZ; no additional JPEG,
measurement or numerical rerun. Three figure sets,6PNG at300dpi/3PDF and6notes;
all3layout audits empty. Owner opened all3colour andF03gray; same axes, full
support, overlapping old/new lines expected. Sidecar validator initially only
missed literal heading 'data provenance'; heading-only patch to template and
six notes fixed it, no pixel/numeric change, no newRun. Final9formats/6notes
validation passes. [Figures and guide](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E030-D01/runs/S03-E030-D01-R002/analysis/README_analysis.md).
Independent reviewer also opened all3colour andF03gray and confirmed final
source/receipt/format/scale/wording checks, no closure blocker; [review](evidence/independent_review.md).
Execution succeeded, retrieval verified, diagnostic comparison complete;
physical accuracy and independent predictive validity remain unestablished.

### Next decision, proposal only

Stop using T1's viewed error as a position-tuning objective. Preserve this
background-only rule and the original half-depth definition as explicit
candidates, retain persistence, and prepare an independent evaluation rather
than another offset/support/window search. Smallest next action is metadata/
exposure/permission screening for a new-beam or genuinely unviewed continuation
candidate, with identity/allowed history/suppliedL*/geometry timing/missingness
fixed before target access. No eligible source is established by E030; same-beam
continuation is not independent-specimen validation. No target opening, new
run, training or old rescoring authorised by this proposal. Physical transfer
can remain an uncertainty question without erasing the measured partial gain.
