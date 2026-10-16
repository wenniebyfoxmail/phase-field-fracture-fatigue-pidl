# E028 independent review

2026-10-16; read-only reviewer `/root/conditional_interface_review`. User asks
bounded residual propagation; experiment-gate skill requires code/evidence
review. No new agent for annotation, no outside communication. Independence
here concerns software/formula reproduction, not physical material truth.

## Before numerical execution

Reviewed first4fc282c protocol/code/tests. Confirmed plus sign: r=d-c_oldFIT,
sampling oldFIT+r equals measured d; normal-only/tangent-only retain the other
oldFIT component. E020 discrete t-cache cannot supply floating n/t sampling;
three existing CRC JPEGs and E018 sampler required, no new source or fit.
153profiles+3baseline, same-anchor primary versus Cartesian secondary, quality
supports, exact postclip contribution formula, oldscore preservation checked.

Found NaN/Inf comparator bypass in the initial abs(actual-reference)>tolerance
guard. Fixed at848a09b52068b13e14e1574f18709fa7324c70f3 with explicit finite4value
check before sampling; source residual identity and malformed-bool regression
tests added. Independently ran10synthetic tests, allpass, clean/diffcheck.
Admission bound to that exactcommit/protocol and E018safe_inputs/E019ac56fdb/
E026991e5b0/E02765e424d. No producer diagnostic before admission.

## Independent full numerical reproduction

Reviewer did not call new main/sample_shifted/scenario/summarize or original
measure. Handwrote inverseH/1/32quantised bilinear/five-line median/shoulder
background/half-depth and directly checked3authorised CRC JPEGs. All3baseline
and153residual profiles/deficits/widths/left-right/depth reproduce exactly,
maxdifference0. Source E02751paired residuals/flags and input identity hashes
checked. Independent formulas reproduce all14790scenario errors/width-change
contributions/clipchange/identity and12support summaries, maxdifference0.

Baseline-.886626089269px. Same-anchor normal[-.971360,-.779257],
tangent[-2.450691,+.959397], joint[-2.343605,+1.042131], medjoint-.827702.
Flags-clear3stage intersection N02/N06/N08/N18/N19,5; independent-stage clear
8x6x5=240/mode. No missing sampled width or clip event. All raw support/sign
counts agree. Finite t/joint scenarios change sign, not actual cause or exact0.

## Renderer admission and visual QA

Saved-output-only7413f8f4be83c9fadf8f9ecd140fec1ca230af4a admitted for R002,
noJPEG/measure/forecast calls. Counts, all17IDs, stage versus3stageclear,
finite range notCI, fixedN01/±20display versus±60operator and source bindings
reviewed. Owner found F01legend/xlabel crowding after actual render, retained
R002, fixed marginonly atb446ee7906681dddcfd7a29ef460072709fa7663, independently
admitted before R003. NumericalR001 unchanged.

Reviewer actually opened R002F02/F03/F04 and F02gray: denominators, normal
small response, tangent/joint sign changes, external4line profile legends and
markers readable, no critical clipping/occlusion. Owner reopened R003F01 and
F02gray; F01legend now separated fromxlabel. All8PNG strict300dpi,12formats/
8same-stem explanations pass. Reviewer then actually opened finalR003F01:
bottom margin fixed, xlabel/legend distinct. F02-F04colour/gray6PNG arrays
exactly equal to the already-reviewed R002 outputs. All8PNGs300dpi/4PDFs/8
sidecars, exact numeric848a09b/rendererb446ee7/R003 bindings,4empty layoutaudit
entries and README numbers confirmed. Receipt succeeded/render_only/
numerical_rerun=false, wall2.891s. Final independent review complete, no blocker.

## Bounded conclusion

Conditional on transferring background residuals to T1, measured t/joint finite
scenarios can affect the remaining miss magnitude; n-only cannot in this set.
Joint median stays near-.83px, no general correction success. Cartesian
near-zero cases are target-visible combinatorial extrema, not a selected method
or new score. First-principles translation/cross-section interpretation is
consistent with these data but not physical-cause proof. Keep old scores and
width definition; actual material correspondence, probability/error bounds and
physical crack opening remain unestablished.
