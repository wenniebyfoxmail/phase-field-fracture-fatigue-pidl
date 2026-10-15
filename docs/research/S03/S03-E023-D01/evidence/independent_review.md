# Independent review — 2026-10-15

Reviewer `/root/halfdepth_code_review`, read-only; no files edited, raw pixels,
fits, training, actual aggregate runner or external sends.

## Before numerical execution

Reviewed cumulative relative bands and missing/zero/boundary conventions.
Initial review found nonfinite metricD0 could bypass abs(diff)>EPS comparisons;
main fixed explicit finite check and added complete72x81 synthetic source
success/nonfinite/duplicate/malformed regressions. Also source-summary identity.
Final clean9f41bb7b76a0b95370e0c5f687a1e2c18fdbf3e9 verified;20synthetics
independently passed0.248s. No runner blocker remained. Primary36/secondary36,
grid9..81, rowdb/columnda, strict amplitude versus EPS sign, whole81support,
zero/missing unassessable, rho0no-admissible and4pxright-censor checked.

## Actual independent recomputation

Without E023evaluate, reviewer regrouped E0225832raw cells, recomputed72pair
bounds,648bands and all coverages/statuses/strict amplitudes/max deviations/
ratios. Every field matches; maximum numeric difference0. Both arms36eligible,
no missing. Original direction32/23/17/13/13/11/10/10/10;
aligned30/23/14/13/11/10/10/10/10. Amplitude original28/19/15/13/13/11/10/10/10;
aligned28/21/14/13/11/10/10/10/10. Statuses original4/22/10, aligned6/20/10.
Runtime clean9f41bb7/upstreamclean247b8f6/4sourcebytes verified;wall.0592185s/
CPU.047176s/threads1. Numerics complete, not physical qualification.

## Source audit

Reviewer independently read all3acquisition workbooks, confirmed eight target
cells, Beam4 empty20kN stop/time row and unused later rows. FourthXLSX is cube
materials, not acquisition. Actual selection/half-depth code locators checked.
Abstract/§2 support predefined stops, not precise eight origin information sets.

Initial review caught Jina-v4 error page and locally missing Specifications
Table. Main obtained canonicalv4/PMCtable/header by web-reader, preserved error
file under explicit502name and original extraction, completed explicit local
transcription. Reviewer read source_access_receipt and supplemented full main
text; channel confusion resolved. PDF/supplement challenged/uninspected; no
author-had-no-plan or exhaustive-absence claim.

## Actual figure QA

Main and reviewer inspected4R001PNGs and guides. Legend unobstructed;36rowmap
order/arms/rho conventions correct. Shared ratio symlog retains full tails,
1line contextual not physical noise; table legible/unclipped. No inversion,
clipping or plot change needed. PNG/PDF pairs present.

## Final wording check complete

Reviewer read README_analysis, Outcome, compact summary, reading/load records,
R001receipt, S03entry and Obsidian result/Roadmap. All numbers consistent;
.5px not sufficient/physical tolerance,9first-loss cases not continuous bounds,
4common-sensitive/10right-censored categories correct. Exact8origin knowledge
not demonstrated, not absence of a plan; inaccessible supplement boundary
retained. Prior other-chat source-note text still preserved. No further
calculation or figure repair; no physical/forecast upgrade.
