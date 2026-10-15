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

### 2026-10-13 — S01-E005

The reviewed context amendment qualified train input visibility (target-balanced
full containment .800425 at padding2 to .932699 at selected padding4). One
frozen-feature linear box head then worsened reused-development macro recall
.289509 to .076111 (-.213398), TPs115 to36 at the same302FPs. Keep E003; no fresh
access. Replacement destroyed prior candidate coverage despite some new covered
targets. The next proposal protects original candidates and separately qualifies
a local spatial original-versus-correction selector, with train-only out-of-sample
qualification and the same fixed-budget detection purpose. This is untested.

### 2026-10-13 — S01-E006

Paired original/correction selection preserved more actual detections than E005
mandatory replacement(TP103 versus36), but did not deliver protected net benefit
on reused development. Against unchanged E003:recall.289509 ->.245195;
102/115 old targets retained,13 lost,1 new actual detection at unchanged302FPs.
Both frozen +.05 gain and .95 retention clauses fail. Keep E003, no fresh access.
R001 metadata-order execution defect was repaired and independently reviewed;
R002 adopted exact features/four heads without refitting and completed the one
selector fit. Next proposed solution makes paired replacement harm explicit and
qualifies an abstain-to-original policy on held train locations; no new arm or
experiment is executed by that proposal. Independent evidence review PASS at b960d3c; current attempt closed.


### 2026-10-15 — S01-E010 implementation preparation

The frozen incremental-utility method is implemented and independently code-reviewed at cdd9d951 (gpt-6.1-sol Medium). Cached fit-only counterfactual support has only4/1/4/3 positive rows by held fold, with negative support in every fit bank. A separate GT-informed fixed selection retains282/282 old E003 hits and adds4, loses0,macro delta0.0093254; this is a candidate opportunity, not a learned result. Prepare exact R001 approval to test whether the model can realise that opportunity. No fits, learned comparisons or fresh-location access; E003 remains the working detector.


### 2026-10-15 — S01-E010-R001 outcome

Four approved utility heads and one comparison completed; independent numerical review passed. E003 old hits282/282 retained, new0/lost0/net0,macro change0. The2901appended corrections never enter the operation prefix, and allfour positive-singleton-utility candidates have negative stored OOF utility despite sufficient E003 scores. Keep E003; the frozen incremental-utility linear selector did not deliver actual net benefit. Next unexecuted proposal tests one capacity change to existing12scalars with all labels/scores/thresholds fixed; capacity remains a hypothesis. Fresh sites sealed. Fixed35-member resultZIP exists onproducer; exact retrieval approval and visual acceptance remain pending.
