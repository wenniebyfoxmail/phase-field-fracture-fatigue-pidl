---
storyline_id: S01
experiment_id: S01-E004
protocol_revision: v1
status: draft
primary_storyline: S01
scientific_verdict: pending
---

# Valid-detection quality ranking

## Bounded claim and target

C2 current-image crack-box measurement, real-road PaveTrack PD fixed-holdout
location generalisation. One question: can a quality ranker convert existing
candidate coverage into at least +0.05 location-macro recall over frozen E003
at one global false positive per image, IoU>=0.50?

The baseline is the E003 epoch-2 geometric-mean score. Candidate and baseline
use identical tiled boxes and images. Tiled proposer, tile size/stride, NMS,
cap, CNN weights and image preprocessing stay frozen.

## Intervention

Use all hash-bound E003 train proposals. Re-score them once with frozen E003
ranker; no CNN/proposer training. Labels: 1 when a proposal has max IoU>=0.50
with any train crack annotation, otherwise 0. This labels detection validity,
not crack presence; partial-overlap boxes are retained as invalid detections.
Duplicate-qualified boxes may receive label 1; exact evaluation still charges
unmatched duplicates as FPs. This head does not claim to solve duplication.

One eight-feature logistic model: proposer logit, frozen crack-presence logit,
log box aspect, log image-area fraction, normalized width and height, normalized
box center x and y. Clamp probabilities to [1e-6,1-1e-6] before logits; fit feature
mean/std on train proposals only (floor std at 1e-8). No location IDs, timestamps,
GT quantities, val/test labels or IoU are prediction inputs.

One deterministic float64 CPU L-BFGS fit on D-26-09: max 200 iterations, strong
Wolfe line search, gradient tolerance 1e-7, one CPU thread, zero initialization.
Objective is balanced binary cross entropy (equal total mass for valid and
invalid classes) plus 0.5*0.001*sum(coefficients^2), excluding intercept.
No model/feature/regularization/fusion/seed search. The candidate score is this
model's predicted valid-detection probability; baseline remains E003 fusion.
Check final gradient infinity norm<=1e-5, finite parameters/loss and objective
not greater than its zero-initialization value; otherwise stop as numerical
inconclusive before viewing validation or accessing test.

## Information boundaries

Train/validation locations are the inherited E002 partitions. Existing E003
validation has been used for checkpoint selection and route design; its result
is development evidence, not independent confirmation. Fit sees train labels
only. Validation features are transformed with frozen train statistics.

New confirmation uses 1174,1729,2246,2260,2485, which E003 did not access. No
pixel or target-count selection. Frozen reid is the independence unit. Exact
workbook, artifact, source-score and location locks are in config/data_lock.
Require validation delta>=+0.05 and complete model/score/source freeze before
any acquisition or reading of these fresh image pixels. Always validate the
freeze before the downloader, workbook preparation and test evaluation.

## One primary criterion and result map

Macro recall is averaged over target-bearing locations; zero-target locations
still contribute FP budget. Primary confirmatory delta is quality-score minus
E003-score recall on the same fresh boxes at 1 FP/image, IoU>=0.50. Pass at
+0.05 absolute. Five percentage points in mean location recall at fixed FP
burden is the practical effect target, not a pooled-count or significance claim.

Validity pass and primary delta>=+0.05 supports the bounded claim; smaller delta
is negative for that margin, while any positive partial effect is retained.
Unidentified primary/failed numerical fit is inconclusive; invalid identity,
split or source is inadmissible. Secondary oracle/capture ratios and FP classes
do not vote. Report paired per-location deltas and descriptive 10,000-resample
location bootstrap (seed 20261012); small selected holdout limits population
inference. An unchanged oracle is expected because boxes are unchanged.

## Development gate and stop rule

One fit. Validation delta>=+0.05 authorizes one new confirmation. Otherwise stop
without consuming fresh locations; record development negative and new-location
claim inconclusive. Do not lower the used gate, tune score/feature selection,
add an arm or rerun training. A new intervention is a new Experiment.
No SAM2, physical growth, mechanics, forecasting or deployment claim.

## Minimum evidence and execution

Independent exact-source/config/protocol/data-lock review; immutable source
manifest; producer PID/runtime/GPU/paths/command receipt; training features,
validity labels and frozen statistics; fitted coefficients and loss/gradient;
paired validation rows and numerical recomputation; freeze authorization or
stop decision; if authorized, one size/CRC/hash-verified acquisition, prepared
manifest and paired test rows; decision figure and deterministic errors; analysis
README; independent evidence review and dated S01 entry.

User authorized next-step advancement. Use gpu-server/D-26-09 GPU1 for fixed CNN
feature extraction and CPU on that producer for the single logistic fit. Check
process/GPU identity read-only before launch; fresh Run S01-E004-R001. No fresh
holdout access or fitting on Mac. Preserve used protocols unchanged.
