---
storyline_id: S01
experiment_id: S01-E006
protocol_revision: v1
created_at: 2026-10-13
status: frozen_pending_independent_review
branch: codex/s01-e006-protected-selection-20261013
base_commit: 1e31845770454bd52f3f17b6061fc54d422d2c1d
---

# Protected originals and paired correction choice

## Decision and result standard

C2 / real-road / current-image crack-box detection. Does a local validity
selector choose E005-style corrections without materially losing E003 detections,
and convert added geometry coverage into actual net detection gain? Evaluation
unit: image, independent grouping reid; same frozen 16 train/5 reused validation
locations and five sealed fresh locations1174/1729/2246/2260/2485. No temporal,
mechanical, physical absence, width or future-prediction claim.

One **protected detection-gain** criterion has two independently necessary
clauses, matching the user's explicit preservation-and-gain objective:

1. Macro-location recall at1FP/image, IoU>=.5, minus frozen E003 >=+.05.
2. At each method's own exact-budget prefix, retain >=.95 of the baseline
   detected GT identities, **micro** pooled ratio across all locations.

Retention identity is (image_id, GT index), using the unchanged deterministic
one-to-one greedy matcher and atomic score ties. Intersection divided by number
of baseline-hit identities. A baseline TP=0 location contributes0 to both sums;
an entirely zero-TP baseline gives undefined retention and an inconclusive
protected claim, never permission for fresh access. Report per-location and
micro retained/lost/new GT counts, but do not switch the gate aggregation.

+.05 is the established practical five-percentage-point detection margin;
.95 allows at most5% loss of old detected targets and makes preservation an
explicit bounded claim, not a promise of perfect safety. Neither is relaxed
after results. Apply both in development and confirmation. Development is
exploratory because locations were reused. A positive smaller gain or retention
component is retained as partial progress; it does not authorize confirmation.

## What is protected, and what is learned

Original bank retains every E003 parent ID/coordinate/score. Original coordinates
are a fallback. **Final emission need not contain the original coordinates** for
a chosen parent; only candidate identity/count and E003 score are structural
invariants. Actual detected-target preservation must pass the retention clause.
This tests paired coordinate choice, not blind candidate augmentation, global
reranking or a deployable protected-original union.

- Freeze E002 tiled proposer, E003 epoch2 CNN/ranker and E005 full corrector
  hashes in config. No encoder, proposer or final corrector retraining.
- In each image select at most40 parent candidates by original E003 score
  sqrt(proposer_confidence*E003_crack_probability), then original box lexical
  order and parent ID. Cap40 is a fixed extraction/selection compute budget;
  it was not tuned using validation results or GT. Fewer parents: use all.
- Produce one original/correction pair per selected parent. Selector predicts
  geometric **box validity** max IoU>=.5, not greedy duplicate eligibility.
  Duplicate risk is handled by the frozen coordinate-conflict policy, not mislabeled
  as a learned duplicate-negative task. Labels use only train reference boxes.
- Each pair keeps parent score. Choose correction only when its selector
  probability is strictly greater than original probability; exact tie keeps
  original. No confidence/margin/threshold sweep, no change to E003 score.
- A preferred correction with IoU>.5 against **any non-parent original** falls
  back to its own original. Then process parents by descending E003 score,
  reid,image,original box,parent ID: if a correction overlaps a previously
  accepted correction at IoU>.5, loser falls back original. Originals are never
  suppressed; correction count never creates extra emitted candidates.
- Emitted rows stay in original input parent order, retain count and E003 score.
  The inherited metric's own lexical-box greedy order within an atomic score
  tie remains unchanged as an algorithm; changed coordinates can change that
  intra-tie matching order. Do not claim score invariance guarantees TP retention.

## Training-only correction qualification

Four folds: sort train location strings numerically, assignment index modulo4.
Fold0:24/514/1577/3662; fold1:95/728/1638/4494;
fold2:151/1400/2027/5508; fold3:353/1459/2028/5982.
For each fold, fit one E005-form corrector using only associated proposals from
other12 locations. Replay source E005 train association IoU>=.05/max-IoU first-GT
index ties; target clipping dx/dy[-2,2],scale[.25,4], equal represented-GT total
weight1/G shared across its n_g proposals, total mass1. Train-only per-fold
mean/population std floor1e-8. Frozen ridge coefficient penalty .001, unpenalized
intercept, float64 closed form, one CPU thread. Finite and normal-equation
residual<=1e-8; final objective<=zero-head+1e-12. The held4 locations are never
used for that head's coefficients/scaler or regression targets during fitting.

For train parent scoring, save separate576 pooled E003 features from padding.1
crops (not the padding4 corrector context). Apply the frozen E003 classifier
in CPU eval mode, batches512, and save probability/geometric score; verifier
replays the same checkpoint classifier exactly from hashed features. This freezes
only the train score backend. Validation uses exact inherited GPU E003 scores;
test uses the existing frozen E003 scoring route. No scoring model is changed.

Generate selector corrections only from their parent location's held-out head,
using padding4 context and the original E005 clamp/decode/image-clip/degenerate
fallback rule. Store four heads, fold membership, coefficient/scaler/numerical
receipts and all predicted boxes. Recompute normal equations without fitting
extra heads when verifying. Full E005 head is used only for validation/test,
not selector train corrections. No fifth corrector fit or hyperparameter sweep.

The frozen E003 encoder was previously trained on all16 train locations,
including GT-derived classification crops. Thus cross-fitting qualifies the
**new box-regression coefficients/scaler conditional on this shared encoder**;
it is not end-to-end OOF evaluation or an unbiased generalisation estimate.
Deployment with the E005 full-data head can shift the correction distribution
relative to fold heads; final validation/confirmation must test that shift.

## Selector input, objective and fit

Original and corrected variants both use their own RGB crop, padding.1 each
side, image-clipped and Python-round integer edges. Existing E003 Resize224,
ToTensor, ImageNet means/std. MobileNetV3-small eval/inference mode;
`features[:-1]` (exclude final576 convolution) yields96x7x7; adaptive average
pool3x3, flatten C,y,x gives864 spatial values. Append log aspect, log image-area
fraction,width/W,height/H,cx/W,cy/H, logit(parent E003 score clipped1e-6),
is_correction flag. Exactly872 float32 features; no GT or IoU at inference.

Training samples are both variants of each GT-free top40 parent, including
partial/non-overlap negatives. Prior weight per variant =1/(L*P_l*2), where
P_l is number of selected parent pairs in location l,L=16. This gives equal
location mass and equal pair/variant base mass; then normalize each validity
class's weighted mass to.5/.5. Class balancing may make final variant weights
unequal; do not call the final objective equal-pair after class balance.

Train-only unweighted means/population std floor1e-8. Float64 balanced BCE
+.5*.001 sum coefficient², unpenalized intercept. Zero initialization; one
L-BFGS fit max200,strong-Wolfe,gradient tolerance1e-7,change tolerance1e-12,
one CPU thread. Acceptance: finite coefficients, final objective<=initial+1e-12,
gradient infinity norm<=1e-5. Recompute initial/final objective, scaler and
gradient from hashed feature arrays and train labels. Score is uncalibrated
validity ranking for coordinate choice, not an actual road probability.

## Gates, budget, firewall and evidence

Validity gates: source/partition/asset identity, OOF regression split and scaler,
no validation/test information in fitting, preserved parent IDs/count/E003 scores,
numerical admissibility and exact metric/target-retention replay. Inadmissible
means invalid evidence, not a scientific method negative. No identifiable primary
means inconclusive. Valid but either protected criterion fails: negative for
this frozen bounded claim, stop fresh; preserve useful partial findings.

Budget:4 fixed crossfit ridge fits,1 selector fit,1 development comparison,
at most1 reviewed fresh comparison. GPU-server/D-26-09 GPU1 after availability
and runtime check; no Mac training. Run S01-E006-R001. Raw external/local archive
under the owning Experiment. Inherited source remains unchanged.

Development pass writes **pending independent review only**, never usable fresh
authorization. A separate independent development-evidence PASS must bind source
manifest/model/evaluation/run ID and exact pending-state SHA to an external
review receipt hash. Only explicit
review-bound authorize stage can create final authorization. Full model/cache/
validation/review verification precedes any downloader, prepared test or pixel
access; duplicate access/fit/extraction rejected. Review fail or missing receipt
cannot be bypassed by the development primary pass.

Minimum evidence: exact original/pair/emitted rows, probabilities, heads/features/
labels/receipts, choices/conflict fallbacks; protected criterion and per-location
retained/lost/new GT counts; FP types/oracle secondary diagnostics; F01 per-location
paired recall and retention with both margins,10k paired-location bootstrap
seed20261013 descriptive for reused development; F02 strongest frozen-score
new detected target, lost old target and candidate FP, two distinct locations
per role, original/correction/GT overlay; README_analysis.md; execution/retrieval
receipt and independent evidence review. After negative, retain E003 and a
concrete bounded next solution; do not only list causes or add unreviewed arms.
