---
storyline_id: S01
title: Real longitudinal road evidence
status: active
---

# S01 — Real longitudinal road evidence

S01 asks which current road states and longitudinal transitions can be measured
from real, traceable asset-time evidence without promoting image ordering or
scene similarity into crack identity, mechanics or prediction.

## Claim-impact ledger

### 2026-10-11 — S01-E002

Native-scale tiling materially improved PaveTrack crack candidate coverage
(macro oracle delta +0.339449) but missed the frozen operating-recall gate
(delta +0.069892 versus +0.10). The experiment closes negative for its bounded
v1 claim while retaining the coverage component. The localisation bottleneck
now moves to ranking within a fixed false-positive budget. Any continuation must
use a new experiment, tile-native hard-negative ranking and unused reserve
locations; SAM2 remains blocked.

### 2026-10-12 — S01-E003

One independently reviewed tile-native hard-negative ranker improved development
macro recall from 0.262757 to 0.289509 (+0.026752), and TPs from 110 to 115 at
unchanged 302 FPs. The +0.05 development gate was not met, so no new confirmation
was authorized. Preserve the epoch-2 checkpoint and partial detection benefit;
new-location effectiveness is untested. Exact selected-FP replay shows 190/302
partial-overlap boxes below IoU 0.50, motivating valid-detection quality ranking
or localisation refinement as the next smallest solution. This is a new design
proposal, not an additional run under E003.

### 2026-10-12 — S01-E004

The independently reviewed eight-feature valid-detection quality head worsened
selected-development macro recall from 0.289509 to 0.249720 (-0.039789), TPs
115 to 106 at unchanged 302 FPs. Background/no-small-overlap FPs fell 92 to 41,
but partial-overlap and duplicate FPs increased. Keep E003 as the working
checkpoint; no fresh confirmation was authorized. Next solution proposal is
observable-context bbox correction with frozen E003 scores and train-only
reference associations, as a separate reviewed experiment.
