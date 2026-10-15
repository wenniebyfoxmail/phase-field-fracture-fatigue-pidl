# S03-E021-D01 — fixed short-support median versus original point width

2026-10-15; Storyline S03; protocol `short-support-v1`; C1 controlled-experiment
DEVELOPMENT diagnostic. User authorises this fixed-support comparison and
Obsidian/visual updates, not new training, physical metrology or forecast scores.

## Question, unit and allowed evidence

Can one FIXED short-segment median reduce tangent-location sensitivity while
retaining the observed load-stage increments? Reuse only already viewed E020
R001 cached measurements/adjacent tags and source strips. No new pixels,
registration fit, crack selection or half-depth function. All12 Beam4 transects,
four stages10/30/40/50kN, both originalH and frozen background-aligned arms.
One viewed specimen; overlapping centres/transects/arms are dependent. No
holdout or future prediction claim; stage increments are observed differences,
not independent reference truth. Ignore filename times as exposure/fatigue time.

Branch `codex/crackmnist-tokenizer-mvp`, clean base8c654a06e7021b2fb67d3f1d847193340a3e2d34;
reuse matching worktree. Scope new E021 protocol/runner/tests/results and S03
index; E015–E020 files and old scores read-only. Safe for existing producers;
no external send/push, solver or model training.

## Frozen candidate and comparator

Let w_j(t) be the unchanged E020 half-depth width at tangent position t.
Comparator P_j(c)=w_j(c). Candidate M_j(c)=median of the NINE widths at
c+{-2,-1.5,-1,-.5,0,.5,1,1.5,2} native pixels. Segment centre span4px;
the inherited five-line grayscale profile adds a further±2px footprint, so
effective raw tangential support extends±4px around c. This is median OF
widths, not width OF a median grayscale profile. Do not call it the same point
estimand or overwrite old targets. No alternative length/mean/trim/tuning sweep.
Four-pixel span matches the existing±2 location challenge and is a minimal
robust-support test, not a length selected for observed forecast performance.

Evaluate c=-2..+2 step.5 (9 centres); cached WIDTH-CENTRE union is[-4,+4],
inside E020[-10,+10]; inherited grayscale footprints make the full jitter
raw-image union[-6,+6]. At c0 the width-centre span is±2/raw footprint±4.
No padding/interpolation/shrinking windows. M valid only
if all9 original widths valid; otherwise missing. Point remains separately
valid. Matched sensitivity requires both methods valid at c=-2,0,+2; do not
zero-fill or discard a curve for bad performance. Match stage increments only
when both methods at c0 are valid in both stages. Report coverage explicitly.

## One primary criterion and stage-retention diagnostic

For each stage/transect define S_Q=max(|Q(-2)-Q(0)|,|Q(+2)-Q(0)|), native px.
Primary = median over available matched ORIGINAL-H curves (out of48) of
D=S_M-S_P; negative
means reduced typical paired tangent sensitivity. This is not E019's combined
normal-and-tangent perturbation metric. Report both separate medians as context,
never substitute their difference for median(D). Aligned arm48 is prespecified
secondary replication, not pooled with primary or used to choose an arm.
No physical/noise-qualified tolerance exists, so report a descriptive estimate
and improve/equal/worse counts (1e-8 arithmetic equality only), not scientific
PASS/FAIL. If no matched curves, inconclusive. No bootstrap independence claim.

Stage retention: all3 adjacent-stage pairs×12 transects, separately per arm,
DeltaP=P_next(0)-P_prev(0), DeltaM similarly. Report all36 signed pairs,
median absolute distortion |DeltaM-DeltaP|, median signed DeltaP/DeltaM,
max distortion, and sign agreement for nonzero DeltaP (|DeltaP|>1e-8 arithmetic
rule); separately count zero-baseline increments and candidate nonzero changes.
Show ratios DeltaM/DeltaP only for nonzero DeltaP with all raw increments;
do not use unstable ratios near zero as the decision criterion. The point
increment is the comparator, NOT physical truth, and no retention percentage
threshold is invented. Stage fidelity is a secondary tradeoff, not a rescue vote
for sensitivity. No old forecast rescoring.

## Feasibility, component findings and repair map

Analytic ceiling: an odd symmetric median on a monotone local sequence equals
its centre. Thus the candidate can suppress isolated nonmonotone excursions,
but cannot remove a locally linear/monotone spatial gradient. Synthetic tests
must demonstrate both unchanged affine responses and removal of an isolated
spike; a uniform additive stage shift must be retained exactly. Existing E020
shows both broad spatial trends and sparse connectivity events, so large
universal improvement is not assumed. No independent reference noise available.

Tag (never exclude) each curve if ANY frozen E020 band event falls among source
adjacent pairs with BOTH endpoints within[-4,+4], the width-centre union of
tested support; exclude boundary-crossing pairs-4.5→-4 and4→4.5. Report sensitivity
paired changes by this tag, exploratory mechanism context only. No new physical
branch classification. If typical sensitivity does not drop, preserve any
local benefit and stage retention but do not claim broad stabilisation; next
test should target fixed-position correspondence/spatial-gradient cancellation,
not a length sweep. If sensitivity drops but stages distort, keep point widths
and investigate a matched-support difference operator. If both favourable,
freeze a later evaluation on independent information, not old-score tuning.

## Identity, budget and independent review

Bind cached E020 runtime to successful clean computation84c34422d52c7ff3f062add41a7bfe7537935861,
exact3936 measurement keys (stage/transect/arm/t index), valid finite widths,
load/tangent grids,3840 adjacent keys,96 curve summaries and96 zero replays.
Recompute cached curve ranges/counts from widths and zero replay values; verify
adjacent width differences and event union flags. No new raw-data hash forest:
reuse sealed Run/commit identity and record actual file paths/byte sizes.
Code frozen and synthetic-tested, then independent read-only review BEFORE
aggregate calculation. One fresh R001 on Mac; CPU AND wall60s, library threads1,
stop on identity/schema/budget failure and retain partial receipt. Renderer may
read only existing E020 raw strips, not resample originals. Independent actual
table/figure/wording review before closure.

## Minimum decision visualisation and evidence

1. Matched48-case sensitivity scatter per arm on common axes/identity line,
   stage colours, primary paired-change annotation and coverage.
2. All36 signed stage-increment comparisons per arm on common signed axes,
   identity/zero lines; no clipping negative changes or hiding reversals.
3. All12 transects, all4stages originalH: point solid versus median dashed
   over all9 centre shifts, shared width axis, E020 event positions if in range.
4. FixedT6 all4 original photo strips, fixed support span and point location,
   plus both-method width/load trajectories at c0. Original predeclaredT6 is
   explanatory, not an average benefit claim. No cherry-picked best case.

Save864 centre estimates with valid/support flags,96 sensitivity comparisons,
72 stage comparisons, JSON summary incl per-stage/per-tag breakdowns, runtime
receipt, exactly FOUR figures PNG/PDF with explanations, README_analysis,
compact tracked Run/evidence/independent review, S03 impact and Obsidian update.
Blocked: physical accuracy, independent-road/beam transfer, future prediction,
optimal segment length, old-score rescue or stable material correspondence.

## Outcome — 2026-10-15, R001

Successful clean7dab072, wall.071103s/CPU.046416s, threads1. All864 centres
valid both methods,96 sensitivity and72stage comparisons complete. Independent
code and actual evidence reviews complete,4PNG/PDF figure sets inspected;
see compact evidence/review/Run records and linked `README_analysis.md`.

Primary original48 paired median(SM-SP)=0; separate S medians both1.441719px,
14improve/30equal/4worse (arithmetic equality1e-8). Secondary aligned medianD0,
15/27/6. Thus no reduced typical paired sensitivity for this one support;
preserve local improvements without a broad stabilisation claim. Both arms
36/36 observed stage signs retained, but max absolute increment distortion
.351420/.268047px. AtT4/40→50kN original increment.582299→.230878px;
sign agreement does not establish complete amplitude retention or physical truth.

Disposition repair: keep old point observable/forecast scores, retain short
median as a local diagnostic component rather than replace the target.
Next proposed/not executed: matched-position stage differences, comparing common
versus independent shifts to separate shared spatial-gradient cancellation from
correspondence error. No length sweep/new model or independent-reference claim.
