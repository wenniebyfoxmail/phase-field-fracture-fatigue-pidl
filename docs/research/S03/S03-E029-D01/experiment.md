# S03-E029-D01 — background-only T1 centre estimate and tangent LOO influence

2026-10-16; S03; protocol `T1-background-center-LOO-v1`; C1 diagnostic,
controlled-experiment/viewed-development. Baseaeb6065. User approves one fixed
background-only position estimate, tangent leave-one-out check, figures and
Obsidian. No image, width, forecast/error, E028 numeric or sealed input allowed
in the new computation. Researcher has seen earlier results; not a blind study.

## Fixed estimator and single question

Primary: E027 all17 origin-accepted near-background points, unchanged ordinary
least-squares affine vector field in fixed basis[1,n/55,t/36], evaluated atT1
centre n=t=0. Reuse this exact estimator, not a new fit family or best-error point.
Fit bothn/t as E027 did; focus stability reporting on t. Compare primary full
centres with E027 field_diagnostics.csv to1e-10px software tolerance before
interpreting LOO. E027 source code65e424d; no old widths/scores overwritten.

Question: how much can deleting a SINGLE background observation change this
T1-centre estimate, especially cross-stage tangential correspondence? NOT:
is that centre physically accurate or reliably transferred across the dark band?
E027 already reported held-out-anchor prediction error; THIS test instead
reports the change in the T1-centre prediction after a deletion.

Source: E027-R001 correspondences.csv, field_diagnostics.csv and runtime receipt
only. Frozen20source IDs/stage,17accepted N01..N20 excludingN05/N09/N10,
stages1/2/3=30/40/50kN, fixed native first-frame n/t units. The source has no
crack widths. All17candidate matches retained as primary, including flags.
Secondary: same E027 predeclared flags-clear8/6/5 supports, NEVER replace the
primary estimator or choose support by resulting centre or any width/error.

## Deletion contract, validity and output

Full6fields (3stages×2supports), then every single deletion within each support:
51primary and19secondary=70LOO opportunities. Each remaining set must have>=4,
rank3, condition<=100 and T1centre inside the convex hull. Preserve insufficient,
degenerate or outside-hull results as unavailable/null, not extrapolated centre0.
Geometry/hull rules inherited from E027, not physical-accuracy cutoffs.

Retain fullvector centre, oldFIT comparator from E027, each LOO centre and
delta_n/delta_t=(LOO-full). Primary descriptive quantity perstage: finite
maxabs(delta_t), min/maxLOO_t, median signedchange and support; no acceptance
threshold, CI, calibrated error bound or new score. Record full-fit centre
weights/leverage/background residuals for influence explanation; for available
LOO verify delta_t=-weight_i*residual_t_i/(1-leverage_i), except undefined
denominator, which remains unavailable. This identity checks arithmetic only.

Cross-stage comparisons30→40 and40→50 use the SAME left-outID at both ends;
report fullcentre displacement difference, LOO difference and change
delta_t_b-delta_t_a. Primary17pairs per transition; secondary only common IDs
in its two fixed stage supports, no independently chosen most favourable points.
Missing/invalid end retains an unavailable pair. Record pairwise support and
maxabschange; no Cartesian expansion, Gaussian noise model or interpolation.

## Budget, decision and figures

One table-only Mac CPU R001 (60s wall/CPU cap), noGPU/network. Synthetic tests
and independent read-only code admission before execution. Record exact source
hashes, receipts/commit, command/host/PID/python/start/end and all opportunities.
R002 render-only from saved outputs; no new numerical diagnostic to make plots.

If single-deletion movements are small -> supports deletion stability within
this fixed background affine model, not accuracy/physical transfer. If large
or unavailable -> preserve candidate but expose dependence on specific points
or support geometry; do not delete influential points to improve results.
Sharedimage/H/sampler, correlated/weak-texture matches and affine continuity
across a crack-like band can bias all fits together, beyond LOO's ability to
detect. Even zero LOOchange could coexist with arbitrary common bias.

Next discriminator if numerically stable: separately approved diagnostic
sampling at this single predeclared centre, compare against oldFIT without
selecting positions using width/error. If unstable: investigate background
texture/support correspondence before sampling or new growth models. No actual
width sampling, correction application, rescoring or eight-case replay here.

Evidence:6fullcentres,70LOOrows, cross-stage paired changes, full weights,
coverage/summary/input identities/receipt/independent review. Three decision
figures: fulln/t centre versus oldFIT and secondary; all17 perID delta_t LOO at
three stages; same-ID cross-stage difference changes with full support visible.
Scatter/paired points, shared axes, no ID-connecting curves or probability bars.
PNG/PDF/grayscale+same-stem explanation, programmatic and actual visual QA.
One existing Obsidian note plus oneRoadmap link, preserve other-chat additions.

Status at registration: prepared; no E029 table fit or LOO run yet.

## Outcome — 2026-10-16

Disposition: retain the ONE fixed all17 affine-centre estimator for a later
diagnostic sampling comparison. Single-deletion sensitivity is limited within
this model/sample; no claim of physical accuracy, certified error bound or
reliable spatial transfer. No position chosen by width/forecast error; no new
width sampled, old score/operator unchanged, no eight-case replay.

R001 cleanae66b4f682512b41e7017afb623aea1ef36c7fdb succeeded, retrieval verified
local; wall.020365s/CPU.011345s. Only E027 background correspondence/fullfield/
receipt tables read; input hashes in evidence/input_identity.json. All6full
centres reproduce E027 to software tolerance; primary uses17points every stage.

| Nominal load | Fixed primary centre_n (px) | centre_t (px) | Max abs single-deletion centre_t change (px) | Available / nominal |
|---|---:|---:|---:|---:|
| 30kN | .045691738 | .493393543 | .032367612 | 17/17 |
| 40kN | -.820149595 | 1.296797379 | .034498783 | 17/17 |
| 50kN | .446623310 | .535569189 | .034081693 | 17/17 |

Shifts are native first-frame n/t coordinates relative to the original-H
mapping, not a new pixel-width definition. Absolute primary tangent LOO centre
ranges .466994–.525761 /1.262299–1.329103 /.508918–.569651px. All51primary LOO
sets retain16points, rank3 and origin within hull; no failures hidden.

Same omittedID across stages gives maxchange in relative tangent displacement
.037581138px (30→40),.031008972px (40→50), both17/17. These are changes from
the respective FULL estimator's stage differences, not absolute displacement
errors. The identity delta_b-delta_a is independently checked.

Secondary flags-clear supports8/6/5 yield maxabsolute centre changes
.054120/.107074/.295216px. Their pair-common6/5 deletion opportunities give
maxrelative changes.076890/.190625px; all19secondary LOO and11pairs available.
Fewer admitted points can be MORE deletion-sensitive; do not choose another
support after seeing centre/width. Full primary remains fixed as declared.
No thresholds or significance/coverage probabilities inferred from these values.

Independent8synthetic tests and pre-execution code review complete. Reviewer
hand-implemented normal-equation LS, monotone-chain hull and Sherman-Morrison
influence, without new fit_center/analyze_pool/summarize/inside_hull calls:
6full/70LOO/70weights/45pairs and10summary groups verified, maxdifference
1.55e-15px (roundoff, not a physical precision claim). Sourcecopy/hash checked.
Synthetic common10px bias leaves LOO unchanged: this result cannot detect
shared errors, correlated templates, weak matches or a field discontinuity
between background and crack. [Independent review](evidence/independent_review.md).

Final3figure sets R002 cleane006d84e79bcd83cb62eb9c1c2bb4979090d8834, wall
2.284024s/CPU2.262626s, saved-output-only. Owner and independent reviewer opened
all3colour PNGs plusF02gray; no critical clipping/overlap, all17IDs and secondary
pair supports explicit. Layout3entries empty;6PNG strict300dpi and9formats/
6same-stem explanations pass. No rendering repair or numerical rerun.
[Figures and guide](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E029-D01/runs/S03-E029-D01-R002/analysis/README_analysis.md).

### Next action, proposal only

Use the fixed primary all17 centre_n/t vectors above for ONE diagnostic
30/40/50kN half-depth sampling comparison against oldFIT. Keep original
centre/normal, five-line median, half-depth operator/QC and original scores;
serialize the fixed position table before any width access. Do not select a
leave-out version, quality support or offset by resulting width/error. Show
all3profiles and same-definition conditional-query effect, not a new forecast
validation. This small sampling has NOT been executed in E029; actual physical
position/width accuracy remains a separate reference question.
