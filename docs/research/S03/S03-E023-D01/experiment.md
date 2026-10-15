# S03-E023-D01 — bounded relative-location tolerance and load knowledge

2026-10-15; `relative-tolerance-v1`; C1 viewed-development diagnostic.
Retain unchanged point half-depth optical image width; no new training, images,
registration, human annotations, future-load predictor or historical scores.
Matching worktree base6040e9026571bd85f08669c97777f65a9cf34d50. Local only,
no push/producer/external messages. User authorises calculation, visuals and
Obsidian. Scope new E023 code/tests/render/docs and S03 navigation.

## Question, unit and frozen support

What relative tangential mismatch preserves the direction of each nominal
stage difference, conditional on each absolute shift staying within +/-2px?
One beam, all12 transects x3 transitions x2 arms. OriginalH36 pairs primary;
background-aligned36 secondary. No pooling, post-hoc removal or independent
specimen confidence intervals. Canonical first-frame native pixels, not mm.

Read ONLY E022-R001 perturbations.csv, pair_metrics.csv, summary.json and
runtime_receipt.json from the local archive. Require successful clean numerical
commit247b8f6ac0f31b09ca70411baceeb2baae5c3bf6, protocol stage-shift-v1,
72 unique pairs and5832 unique cells, exact nine-point marginal grids,
loads10/30/40/50 and adjacent stages. Validate diagonal flags, baseline flags,
finite valid increments, D0 consistency and deviation=increment-D0, and match
E022 paired-valid/baseline-valid/nonzero/sign-loss endpoint metrics. No new
raw-width sampling. Bind these source filenames/byte sizes and upstream receipt.

## Prespecified descriptive criterion

da,db in{-2,-1.5,...,2}; r=db-da. For rho in{0,.5,...,4}px, use all cells
S(rho) with |r|<=rho, not only the band boundary. Counts9,25,39,51,61,69,75,79,81.
D0 is the unchanged zero-shift optical increment, NOT truth. Direction stable
iff EVERY increment in S(rho) has the sign of D0 and magnitude>1e-8.
EPS is arithmetic only. The primary curve counts direction-stable pairs out
all36 opportunities per arm, with eligible support stated. Missing/invalid any
of81 cells or invalid/zero D0 => unassessable, not safe/fail. All raw cells kept.
Nested survival declines by construction; this is a descriptive tolerance
envelope, not evidence that small errors occur or a probability/confidence bound.

Per pair save largest tested stable rho AND first failing tested rho:
- loss at rho0: no admissible tolerance, not '0px tolerated';
- stable at0 but loss at.5: tested safe0/first fail.5, no continuous interval claim;
- stable through4: right-censored at4 on this grid, not unlimited tolerance.
No interpolation, subgrid claim, invented global80% pass rule or single physical
accuracy number. The nine-point spacing is not measurement precision.

Secondary amplitude guard: max_S |increment-D0| < |D0|, strict. Report separately
from direction; positive overshoots can retain sign but exceed one nominal
increment. Save maximum absolute response and ratio to |D0| at every rho.
No physical noise/error margin exists; this guard does not establish accuracy.
The overall tighter-relative-offset question remains conditional on common
offsets in +/-2px and unchanged tangent convention, not material tracking.

## Load-knowledge source audit (no new prediction score)

Freshly read primary Data in Brief DOI10.1016/j.dib.2023.109703, its associated
supplement and public dataset-v4 description where accessible; inspect all four
already-cached XLSX workbooks (three acquisition sheets and one cube test) and actual retrospective selection
code for the eight old forecast queries. Separate evidence of a predefined
loading protocol, exact next nominal target, next INCLUDED IB observation and
future measured force. No availability claim based only on filename/time order.
Use full local primary text with locators; retain gaps/unknowns. Retrospectively
conditioned evaluation may still be useful but is not origin-information proof.
No contact with authors or external submission. No raw 3GB archive download.

## Runtime, tests, figures and review

Before aggregate results: protocol+code freeze, synthetic tests and independent
read-only code review. Test nested counts, axis convention, common-shift failure,
zero-only safe/first-loss, right censoring, negative D0, zero/missing handling,
strict amplitude guard versus sign, duplicate/malformed source rejection.
Fresh Mac R001 CPU AND wall60s, threads1, new output only; identity/schema/budget
errors stop with receipt. Retain missing counts; no broad tuning or extra arms.

Figures fixed before calculation: (1) primary direction coverage versus rho,
secondary amplitude shown separately, both arms; (2) all36 direction envelopes
per arm in transition/transect order, distinct missing state; (3) all36 worst
response-to-|D0| envelopes per arm, threshold1 clearly contextual, raw tail not
hidden; (4) load knowledge evidence table, not a numerical accuracy chart.
PNG/PDF plus per-figure guide and README_analysis, visually inspect final files.
Save648 band rows/72 pair bounds, summary, receipt, load-audit record and exact
independent code/evidence reviews. Report S03 and concise Obsidian milestones.

## Next decision

Use pair-specific finite-grid bounds to select the next position-check test;
keep already-common-sensitive cases visible. Do not promise a universal physical
tolerance. If exact next nominal input is unverified, keep old eight queries
labelled retrospective load-conditioned and prepare a separately specified
origin-only next-observation baseline instead of silently using future force.

## Outcome — 2026-10-15

Clean9f41bb7 R001 succeeded, wall.0592185s/CPU.047176s, threads1;72pair bounds/
648band rows.20synthetics independently checked;22additional reused-helper
regressions passed. Reviewer independently recomputed every band/bound from
E022 raw5832cells, no E023evaluate call, maximum difference0. Four final
PNG/PDF sets and sidecars visually checked. Exact source/channel limits in
evidence/load_knowledge_review.md and paper_reading_record.json.

Original36 direction coverage at rho0/.5/1/1.5/2/2.5/3/3.5/4:
32/23/17/13/13/11/10/10/10; amplitude28/19/15/13/13/11/10/10/10.
Aligned direction30/23/14/13/11/10/10/10/10; amplitude28/21/14/13/11/10/10/10/10.
Original4no-admissible/22bracketed/10right-censored; aligned6/20/10.
Nine original pairs stable at0 fail at.5; six last-stable.5 first-fail1.
No universal safe tolerance; .5gridstep is not physical measurement precision.

Fresh main-text reading confirms predefined load stops; three acquisition
workbooks confirm all8retrospective labels. Exact next INCLUDED nominal target
at each historical origin remains not demonstrated in accessed sources.
Canonical PMC table/header and datasetv4 web-reader successful; originalJina
main extraction supplemented explicitly; Jina-v4 502 is not source evidence.
Main/supplementary PDFs browser-challenged/uninspected, no exhaustive absence
claim. Retain old results as retrospective nominal-load-conditioned development,
not evidence of origin-only next-observation prediction or future force knowledge.

Next proposed: compare internal CHECK tangent-position residual capability with
these pair-specific grid envelopes. Preserve difficult components; no case
exclusion, grid densification, model or new forecast execution here.
