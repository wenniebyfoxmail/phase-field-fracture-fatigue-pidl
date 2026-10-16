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
