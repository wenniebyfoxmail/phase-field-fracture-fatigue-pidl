# S03-E028-D01 — fixed-half-depth response to observed T1 n/t residual scenarios

2026-10-16; S03; protocol `T1-residual-propagation-v1`; C1 diagnostic,
controlled-experiment, viewed-development Beam4 last query only. Basea86ed7a.
User approves v1.1, no duplicate eight-case replay, this bounded propagation,
figures and Obsidian sync. No change to width definition, original scores,
baseline formulas, stored correction or query/case identities.

## Question, estimand and scope

Can the measured E027 near-background residual scenarios, ASSUMED transferable
to T1, generate an image-width/query-error change as large as the remaining
E026 oldFIT-aligned optical secant miss about-.887px? Not: was that miss actually
caused by location error? Reliable background-to-crack transfer is unproven.

FixedT1 original centre/normal, five parallel tangent lines -2..2, original
normal samples -60..60/.25, quantised inverse-H bilinear sampler and unchanged
half-depth operator/QC, native first-frame px. Fixed30/40/50kN; no full8case replay.
Use3existing CRC/size-verified E012 JPEGs plus E018 safe geometry/H, E019 frozen
oldFIT translations and E027-R001 primary correspondence residuals. E026-R001
aligned nominal widths/error are the baseline reproduction reference.
No fresh image, future/holdout source, fitting, matching, registration, neural
training, physical-force or plan-availability claim.

## Freeze before new sampling

Origin20candidates and17accepted IDs remain E027 selection; N05/N09/N10 excluded
before matching. Use each retained anchor's measured paired residual
r_j,a=(d_n-c_n,d_t-c_t) atstagej. Never split/recombine n/t from different
anchors, invent a Gaussian error radius, magnify residuals, optimise a shift,
or tune support to reduce error. New source rows must satisfy residual=d-oldFIT,
correct stage/load/anchor, finite values and available. Preserve all quality flags.

Three fixed coordinate modes:
- normal_only: sample at original centre + oldFIT_n*n + oldFIT_t*t + r_n*n;
- tangent_only: same oldFIT centre + r_t*t;
- joint: same oldFIT centre + r_n*n+r_t*t (equals shift by E027 d).
Positive sign is the candidate's extra target-feature displacement, not an
arbitrary symmetric plus/minus uncertainty. The other oldFIT component remains
in BOTH one-component modes. Keep normal direction and width definition fixed.

Sample3oldFIT baseline profiles and17anchors×3stages×3modes=153profiles.
No E020 t-grid interpolation/nearest rounding: n residual and true floating
position require direct sampling of the existing JPEGs. Each invalid width
retains its reason; no search for a valid nearby point, zero fill or support repair.

Primary temporal support:17 **coherent same-anchor** scenarios per mode,
using that same anchor's residual at30/40/50kN. This preserves observed temporal
pairing but ASSUMES its background drift transfers to T1; not17 material tracks
atT1 or independent specimens. Secondary support: full Cartesian17^3=4913
**independent-stage** combinations per mode using the same sampled widths;
no new pixels or fits. It deliberately discards temporal pairing, is not an
empirical confidence interval, probability or validated bound on actual errors.

All-available is primary. Separately report flags-clear at eachstage (E0278/6/5),
coherent intersection (possibly empty), and Cartesian product of those stage
supports. Do not replace coherent support by independently chosen clear points.
If a support has no valid scenario, extrema/error summaries unavailable, not0.

## Comparison, decomposition and decision

First reproduce each baseline width and postclip error against E026 within
1e-8px software tolerance; mismatch stops interpretation. For each valid triple,
fixed secant raw prediction=2*w40-w30, outputclip[0,120], signederror=prediction-w50.
Deltae relative to baseline and stagewidth changes are retained. Exact raw
decomposition: deltae_raw=-deltaw30+2*deltaw40-deltaw50; separate clip-change term
reconciles postclip error. One-component effects need not add to joint effect.

Primary descriptive output: per-mode coherent signederror min/max, deltae range,
minimum absolute error attained, sign counts and coverage; show all17ID rows
and oldFIT baseline-.887px. State whether **finite scenario extrema** straddle0,
but do not claim an exact0 scenario or intermediate-value existence. No new
scientific pass threshold, success-rate probability or physical tolerance.
Secondary independent-stage extrema/support illuminate temporal dependence,
not rescued evidence if coherent support misses. All failures and flagged rows
remain visible; same-scenario n/t comparison, no best-mode selection as score.

If finite scenarios change error enough or cross its sign -> conditional
position-sensitivity explanation is plausible at measured background residual
magnitudes, not causal attribution or a new correction. If none do -> those
finite transferred scenarios do not explain the miss; not a universal exclusion
of all localization error. If quality/transfer assumptions dominate -> explicitly
retain ambiguity rather than declaring all research failed. Continue by the
smallest discriminator of position mapping versus genuine optical trend.
No old rescoring, deletingT1, replacing definitions or new model in any outcome.

## Execution, review and evidence

One clean-commit R001 Mac CPU diagnostic,60s wall/CPU budget;3JPEGs only,
no GPU/network. Source receipts exact commits E019ac56fdb, E026991e5b0,
E02765e424d; E018 sanitized inputs as used E027. Record input hashes, source
identities, command/host/PID/python/commit/start/end/runtime and source receipts.
Synthetic tests and independent read-only code admission before JPEG sampling.
Render-only fresh R002 from saved outputs, no second numeric replay. Changes
after viewing get fresh Run/amendment, not overwrite prior archive.

Evidence: all-source residual rows with flags,3baseline+153profile measurements,
profiles/deficits, coherent and Cartesian cases, per-mode/support summaries,
baseline comparison, component decomposition, receipts and independent review.
Minimum figures: (1) n/t residual and width response allanchors/stages;
(2) coherent per-ID error in3modes vs oldFIT/zero;
(3) coherent versus Cartesian ranges with flags-clear support, notCI;
(4) fixedID N01 profiles atall3stages vs baseline, not best-error example.
All plots PNG/PDF/grayscale, same-stem explanations, exact tables and visual QA.
Obsidian one existing living note, short plan/result entries, oneRoadmap link.

Registration status: prepared, no E028 raw-image sampling or diagnostic run yet.

## Outcome — 2026-10-16

Disposition: advance the **conditional position-sensitivity explanation**;
actual background-to-crack transfer and causal attribution remain unresolved.
This local diagnostic is not a repaired forecast, replacement correction or
new eight-case score. User adopts reference-interface draftv1.1; existing E025
implementation/results reused, not replayed.

NumericR001 clean848a09b52068b13e14e1574f18709fa7324c70f3 succeeded, verified
local, wall.586051s/CPU.569498s,3existing CRC-verified JPEGs, noGPU/network.
All3oldFIT baseline profiles reproduce E026 exactly: widths
16.382909772/16.141970936/16.787658189px, signed query error-.886626089269px.
All153residual profiles valid;51coherent scenarios and14739Cartesian scenarios
valid. No active clipping; stage-contribution identity holds exactly.

| Component propagated | Same-anchor17 signed-error min/max (px) | Median (px) | Min absolute sampled error (px) |
|---|---:|---:|---:|
| Normal only | -.971360 / -.779257 | -.906866 | .779257 |
| Tangent only | -2.450691 / +.959397 | -.790754 | .015106 |
| Joint | -2.343605 / +1.042131 | -.827702 | .032491 |

Thus measured background residual magnitudes, IF transferable, can generate
tangent/joint error changes large enough to reverse the original-.887px sign;
normal-only finite scenarios do not. Joint median remains-.828px, close to the
baseline: not a generally eliminated bias. No sampled coherent case is exactly0;
finite extrema bracketing0 is not proof of an intermediate exact solution.
Minimum-error scenarios are diagnostics only, never selected as a correction.

Flags-clear intersection is5IDs N02/N06/N08/N18/N19, distinct from stagewise
supports8/6/5. Their same-anchor signederror ranges normal[-.971360,-.839937],
tangent[-.985670,+.931453], joint[-1.024965,+.925305]px; joint median-.539178px.
So the sign-crossing possibility is not solely contributed by flagged matches,
but five image-background scenarios are not five material truths or new beams.

Independent-stage all4913/mode extrema normal[-1.041024,-.731104],
tangent[-4.376070,+5.043745], joint[-4.447638,+4.936225]px. Clear Cartesian240/mode
uses8x6x5, not240physical observations. These wider ranges discard temporal
pairing; near-zero Cartesian extrema must NOT be sold as prediction success.
All-source exclusions/flags remain in source_residuals.csv; small exact evidence
and source hashes in evidence/, full cases/profiles remain local archive.

### First-principles interpretation and next discriminator

Interpretation, not established cause: a small normal shift mostly moves the
coordinate origin along a similar transverse profile; subtracting the two
crossing locations cancels common translation approximately. A tangent shift
samples a DIFFERENT transverse section near the bend/junction-like dark band,
so it can change apparent width directly. Window/peak/QC, quantisation and
photometric effects prevent exact normal invariance. Secant error-change
weights width changes -1,+2,-1, so independent stage errors can amplify rather
than cancel; joint n/t effects are not required to be additive.

Next bounded repair PROPOSED, not executed: use one predeclared, background-only
spatial correspondence estimate (e.g. reuse E027 already-computed affine centre,
not choose a best-error anchor) and test its tangent-location stability under
fixed leave-one-out support before a diagnostic T1 sampling comparison. Do not
claim uncertainty certification from that model, or require a physical reference
to discuss the declared optical observable. If such an estimate is unstable,
keep location sensitivity explicit rather than fitting a growth model to absorb
it. The current experiment establishes sensitivity, not which location is right.

### Review and figures

Independent code admission:10synthetic tests, fixed nonfinite-baseline bypass
before real sampling and added residual-sign/duplicate/load/flags regression
checks. Independent evidence reviewer hand-implemented inverseH/1/32bilinear,
five-line median, shoulder/half-depth and all case/decomposition/summary formulas,
without calling new producer functions or original measure:3baseline+153profile
arrays/deficits/widths/endpoints/depth and14790cases/12summaries reproduce with
maxdifference0. [Review](evidence/independent_review.md).

FinalR003 rendererb446ee7906681dddcfd7a29ef460072709fa7663 exports4figure sets,
12PNG/PDF formats,8same-stem explanations, wall2.891197s/CPU2.874061s. R002
retained/superseded only for F01 legend/xlabel crowding, no numerical rerun.
Owner opened all4colour R002, finalF01/F02gray; final8PNG strict300dpi and
sidecar12formats/8notes checks pass. Independent final visual closure recorded
in review. [Final figures and reading guide](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E028-D01/runs/S03-E028-D01-R003/analysis/README_analysis.md).
