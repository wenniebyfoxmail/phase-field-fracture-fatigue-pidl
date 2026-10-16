# S03-E027-D01 — independent near-background correspondence at T1

2026-10-16; Storyline S03; protocol `near-background-v1`; C1 diagnostic,
controlled-experiment, viewed-development specimen. Base44620d7622a0fcc3421794b95a6831989c1d82e4.
User authorises near-crack correspondence check, comparison with existing
correction, figures and Obsidian sync. Half-depth definition and all old scores
immutable. No width/profile values enter selection, matching, fit or QC.

## Question and scope

Does existing E019 T1 FIT translation reduce residual displacement at NEW
near-background anchors, compared with no extra correction? Can local background
correspondences support transferring that correction to the T1 sampling band?
Reference10kN first frame; targets30/40/50kN of Beam4 fixed IB camera only.
Use E018 sanitised geometry/H and4existing CRC-verified E012 JPEGs; E019 frozen
T1 shifts as comparator. No new download, training, load/width prediction, image
warp or updated correction applied to the width pipeline.

## Freeze before target matching

20 deterministic candidates in first-frame local(n,t) coordinates:
n=-55,-35,35,55, each t=-36,-18,0,18,36. IDs N01..N20 in n-major order.
Primary template15x15 (radius7), secondary23x23(radius11), each search±6,
so search27x27/35x35. New largest search envelopes |n|<=72 do not overlap old
FIT/CHECK template footprints |n|>=85. Some new secondary footprints overlap
one another; they are correlated observations, not20 independent specimens.

R000 prepares only10kN clean local context, candidate/template/search boxes,
and23x23 clean patch atlas, templates, geometry/source receipt. A separate
context-isolated agent sees ONLY these first-frame images and fixed criteria:
exclude maximum23x23 templates touching the visible dark band or uncertain
background; retain other background templates, even weak texture (numeric QC
will expose it). Same candidate support for both template sizes. Search
envelope overlap with dark band is shown, not itself an automatic exclusion.
Accept/exclude/uncertain with reason; uncertain excluded from matching. Lock all
20 decisions before any new target matching. No manual future-based additions,
mask repair or best-result selection. AI screening is not human physical truth.

## Matching and quality information

Local grids sample original JPEGs through existing inverse H, same quantised
bilinear sampler. Forward NCC template at reference p, target search about p;
candidate displacement d=(d_n,d_t), subpixel3-point parabolic peak refinement.
Reject finite/support failures, nearly flat template(std<=1 gray), or peak at
search boundary; preserve all failures. No target-derived width enters this.
Reverse template is target patch at p+d, reference search centred at ORIGINAL p:
return displacement b should be0, so roundtrip error=|b|, NOT |d+b|.
Primary/secondary displacement difference is a repeatability proxy.

Predeclared REVIEW FLAGS (not physical acceptance thresholds): forward NCC<.8,
peak separation<.02 (excluding3x3 peak neighbourhood), roundtrip>.5px,
template-size displacement difference>.5px, or missing reverse/secondary.
Forward NCC/separation flags apply to each template; reverse checks use
availability and loop closure, with reverse NCC/separation retained for audit
but no additional reverse-NCC threshold. This clarification precedes target matching.
.5 is a reporting resolution for internal consistency, not certified accuracy.
Report all primary available matches and an explicitly separate flags-clear
subset; never tune flags after target access or use them to select old scores.

## Comparison and spatial transfer diagnostic

Primary descriptive comparator: each new anchor's d (zero-extra-correction
residual) versus d-c_oldFIT. Per stage report all points, median norm before/
after, median paired(norm_after-norm_before), and signed normal/tangent residuals.
Missing anchors retain nominal20/stage denominator and reasons. Negative paired
change supports reduced displacement on these background proxies only; no
formal physical reliability cutoff or significance test is available.

Secondary: near-anchor displacement field least-squares affine in(n/55,t/36),
no width feedback, no application to image/widths. Predict at T1 centre only if
>=4 available points, rank3, condition<=100, origin inside convex hull; otherwise
report unavailable/not-interpolated. Condition bound is numerical safety, not a
physical claim. Leave-one-out residuals report hull-interior and hull-exterior
held-out points separately (edge LOO commonly extrapolates). Do this for all
primary available and flags-clear supports, fixed in advance. Side-wise medians
also shown. Centre is interpolation across a crack and may cross a displacement
discontinuity: agreement never proves crack-edge material tracking. Lower
fit residual is not independent truth or a new correction qualification.

## Budget and outcome-to-action

R000 origin preparation, R001 matching/diagnostics, R002 rendering, each fresh
local archive directory,60s wall/CPU expectation/budget; no GPU/network.
Code synthetic tests and independent read-only review before each new producer
stage; exact source commit/host/PID/time/command and source IDs in receipts.
Origin selection independently reviewed and saved before R001.

If first-frame support inadequate -> record coverage, stop centre claim, do not
shift points using targets. If NCC/roundtrip/size disagree -> uncertain
correspondence, not a reliable reference; investigate acquisition/local texture.
If old correction reduces near-background residuals but centre/LOO/side agreement
does not qualify -> background-only support, transfer unresolved. If near-field
checks disagree with old correction -> retain old width/score and select one
bounded correspondence repair. No automatic FAIL of research or new model.

Minimum evidence:20 origin decisions,120 per-template/stage opportunities and60
combined anchor opportunities, forward/reverse/QC and residuals, exact support/
affine/LOO records, raw-photo local overlays and template galleries, all stages
and signed before/after comparisons, README_analysis and independent reviews.
No claim of independent human truth, unseen specimen, physical opening accuracy,
reliable crack-edge transfer or improved prediction solely from successful NCC.

Status at registration: prepared; no new matching performed.

## Outcome — 2026-10-16

Disposition: retain old correction with **near-background corroboration**;
reliable transfer to the physical crack-edge/sampling band remains unresolved.
This is component progress, not an overall research failure or new validation.
Origin-only fresh-context agent retained17/20; N05/N09/N10 excluded for visible
band contact before targets were matched. This is AI screening, not human truth.
The new locations are disjoint from old FIT/CHECK footprints, but share original
images, H and sampler; new secondary templates overlap spatially.

R001 clean65e424d1f7b71b4080473853d246b8c14ee74669 completed in.358s wall/.341s
CPU. All17 retained primary anchors matched at each of3 stages:51/51accepted,
51/60nominal opportunities (85%). Both template sizes available at all51;
102 accepted per-template-stage records plus18origin exclusions retained.
No search/support/flat-template failure among retained anchors. Review flags
clear only8/6/5 by30/40/50kN:19/51available,19/60nominal. No threshold retuning.

| Target load | Median norm, no extra correction (px) | After old FIT (px) | Median paired change (px) | Flags clear / available |
|---|---:|---:|---:|---:|
| 30kN | .574080 | .269186 | -.262834 | 8/17 |
| 40kN | 1.471060 | .317121 | -1.219519 | 6/17 |
| 50kN | .777227 | .304064 | -.523448 | 5/17 |

Medians use the SAME17 anchors each stage; not every anchor improves. Negative
paired changes show the old correction's direction/magnitude is supported at
new near-background positions. These residuals are relative to image matches,
not certified physical displacement errors or uncertainty bounds.

All-available affine centres lie inside the support hull, rank3,condition1.727;
centre-oldFIT differences.055879/.024072/.059929px are estimator AGREEMENT,
not.02-.06px accuracy. LOO hull-interior RMS.323131/.430650/.371465px on12points
perstage, exterior.383996/.283276/.416868 on5points. Flags-clear centre-oldFIT
differences.024500/.021452/.101535px, but interior LOO counts2/0/0: later two
checks unavailable, not zero error. Exterior LOO5/6point checks can extrapolate;
50kN flags-clear exterior RMS.802254px. Crossing a crack-like band can violate
a continuous affine displacement assumption even with centre inside the hull.

Independent reviewer reran10synthetic tests and independently rebuilt inverse-H
quantised sampling/NCC/subpixel/reverse matches, without calling new match or
summary functions. All102 per-template forward/reverse outputs,60combined rows,
18stage/side summaries,6fields and70LOO records reproduce with maxdifference0.
An earlier side-denominator bug was fixed before R001. Exact review in
[independent_review.md](evidence/independent_review.md), small tables in evidence/.

Final display R003 clean3cbf8c5c0753519e5675649547fcbb2174f3869c is render-only:
4main figure sets plus3all-accepted gallery pages,21PNG/PDF formats and14
same-stem explanations. R002 retained/superseded only for missing sidecars and
gray-DPI metadata; all14PNG pixel arrays identical to R003. Owner/reviewer
opened all7colour plots and key grayscale; no data clipping/critical overlap,
all7layout audits empty, all14PNG strict300dpi checks pass, sidecars21/21 pass.
[Final figures and guide](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E027-D01/runs/S03-E027-D01-R003/analysis/README_analysis.md).

### Next discriminator, not executed here

Propagate observed near-background normal AND tangent residuals through the
UNCHANGED half-depth operator at T1: can plausible residual-position scenarios
account for the remaining E026 aligned optical-query miss about.887px? Keep
actual observed residual pairs and explicit spatial-transfer assumptions, not
a Gaussian precision/coverage claim. Freeze this bounded diagnostic before
calculation; do not tune support to rescue the score. New near-field affine
correction was NOT applied, old target/score untouched, no training/new data.
