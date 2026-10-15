# Independent code and evidence review — 2026-10-15

Reviewer `/root/halfdepth_code_review`, read-only; no file changes, real-image
sampler runs, fits or forecasting. Protocol `tangent-response-v1`.

## Code readiness before R001

Bound numerical commit `84c34422d52c7ff3f062add41a7bfe7537935861`, clean.
Reviewer independently ran all8 synthetic tests, passed in0.015s. Input snapshot
digest independently recomputed as
`22b8b2da344432d35513e47d56cd78d20ddc0d7526a467d7eeec45e7bf088431`.
E019 successful receipt/commit,48 translations and96 baseline references
validated. Reused helpers unchanged relative to reviewed E019 commit. Earlier
NaN reference bypass, finite translation/origin-zero and budget checks repaired
before this frozen run. Selected component enumeration/censor convention and
same-band peak-motion distinction reviewed. No remaining numerical-run blocker.

Renderer-only follow-up `099b738d4801706a320a852ec1a02b3c6055c99f` reviewed
before rendering: predeclared overall/stage×arm union-event counts divided by
paired-valid counts, not arithmetic mean of arm rates; each stage×arm480
opportunities. Explicit colorbar layout changes no numerical data. Stable
case ordering and first-occurrence tie handling/deduplication correct. Strip
and heatmap extents match array centres; invalids excluded from event denominator.

## Actual evidence audit

R001 successful at reviewed clean numerical commit, wall2.717790083s,
CPU2.657989s, threads1. Four-input digest and all4 original JPEG byte counts/
CRCs independently checked against source identities and receipt.

3936 unique profiles all valid,3840 unique adjacent pairs all paired-valid,
96 curve summaries and96 zero-position replays, all replay differences0.
All saved profile/deficit arrays41×481 and source strips57×121 match grids.
Reviewer independently enumerated components from all3936 stored deficits,
matching every saved interval. Independent recomputation of all3840 pair
overlap/split/merge/union and width/peak differences matched; all96 curve
counts/ranges/maxima matched.

Overall16/3840=.4166667%,0 disjoint switches,5 splits,11 merges. Each arm
8/1920: original3split/5merge, aligned2split/6merge. All eight stage×arm
breakdowns match. Original/aligned curve width-range medians7.146621165/
7.135375513px; maximum adjacent changes9.369827433/9.363597263px.
FixedT6 eight curves all no events, ranges7.44558..7.79737px. First event
T1/10kN/t3.5→4 is split; largest-jump case T1/30kN/t8.5→9 is merge,
13.481170956→22.850998389px with peak-3.75→-4px. Selection rules satisfied.

Auxiliary complete-table checks matched: no-event maximum absolute width
change4.518240207px atT5/10kN/t5→5.5; largest original peak motion20.5px
atT2/40kN/t-4.5→-4 accompanies width change-.014813729px and no event.

All5 actual PNGs independently viewed: no clipping/blank panels/coordinate
reversal/legend obstruction, heatmap colorbar correct. T6 strip projections
explicitly not human/physical edges. Main-agent sidecar validator10 formats/
5 notes passed. README and final closure wording receive a final read below.

## Interpretation boundary

Evidence complete for the bounded C1 spatial/algorithmic diagnostic, not physical
accuracy or forecast validity. Prefer: most adjacent positions do not trigger
the predeclared component events yet width has substantial spatial response;
sparse half-depth connectivity candidates accompany large jumps. Do not infer
verified material/physical branch identity, true-width smoothness, or successful
spatial aggregation from low event frequency. Sixteen records include both
arms and duplicate origin-stage pairs, not sixteen independent physical events.
Fixed-segment aggregation remains an untested proposed next experiment.

## Final document check

Reviewer subsequently read `README_analysis.md`, compact evidence summary,
R001 receipt, this review, Experiment Outcome and S03 claim-impact entry.
All numbers, including six-decimal diagnostic crossings, match reviewed raw
evidence. Dependency/denominator and physical-reference limits clear; no-event
is not certified smoothness, segment aggregation is proposed/not executed,
old forecast scores unchanged. No remaining numerical, visual or wording
blocker; E020 bounded diagnostic may close and be delivered.
