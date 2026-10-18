# Attempt S09-E010-A005-producer-run

- Status: `accepted`
- Created: 2026-10-19T05:11:24+08:00
- Closed: 2026-10-18T22:30:00+01:00
- Type: `producer-execution`
- Human decision required: False

## Motivation

Execute the single approved three-arm run, preserve its first outcome, and
decide whether support/amplitude balancing improves growth-regime ranking.

## Trigger

The user explicitly approved execution according to the final run card.

## Result

The run completed all 1,500 authorised optimiser steps with exact `A25` replay,
shared identity, finite outputs, zero hard-constraint violations, complete
receipts, and 28/28 retrieved SHA256 matches. The frozen classification is
`NO_TARGETED_RANKING_SIGNAL`: `B25` and `A25` both scored AUC 0.68 and pair
score 34, so the required gain of 4 was not achieved.

All four protected `B25/A25` ratios passed. Within the balanced formulation,
beta 0.25 reduced `L_P` from 2194.52 to 0.7224 versus `B0`, but did not change
the amplitude ranking. Field replay confirmed that visually convincing total
peak fields are dominated by the supplied pre-state; the predicted increment
remains weakly cycle-dependent and spatially misaligned.

## Adopted decision

Freeze the valid negative primary result and retain the conditional physics
finding. The global SVD audit initially suggested a low-rank representation,
but the focused pair-contrast audit showed that all eight wrong pairs retain
finite local repair sensitivity. The current mean B25 descent instead worsens
all eight wrong margins while improving all 17 already-correct margins.

The next minimal causal test therefore keeps the current head and beta 0.25,
and adds an explicit cross-cycle ranking objective against a compute-matched
B25 continuation. A factorized amplitude-by-support head is deferred until an
objective-only repair is tested. Do not sweep beta or ordinary scalar weights.

## Independent result review

ChatGPT Pro first returned `REVISE_AND_REREVIEW` solely because the compact
result package omitted the raw A25 per-cycle projection counts. The archived
raw-log supplement closed that evidence gap without a rerun: 48/48 count
integers matched the frozen E009 reference, and the exact replay gate passed
33/33 clauses. The final verdict is `RESULT_EVIDENCE_READY_PASS`.

## Evidence

- `docs/research/S09/S09-E010/run_analysis_20261019.md`
- `docs/research/S09/S09-E010/result_evidence_review_20261019.md`
- `docs/research/S09/S09-E010/results/`
- `docs/research/S09/S09-E010/results/cycle_separability/B25_update500_pair_contrast_jacobian_receipt.json`
- `local_archive/experiments/S09-E010/runs/S09-E010-R001-support-amplitude-three-arm/`

