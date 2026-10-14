---
storyline_id: S01
experiment_id: S01-E008
protocol_revision: v1
created_at: 2026-10-15
status: frozen_pending_independent_review
branch: codex/s01-e008-corrected-scoring-20261015
base_commit: 05f37c7e06c96bd06008ccc7b574ca4d9075a5b2
---

# Score corrected crops with E003 and preserve original detections

C2,current-image real-road crack-box detection. Does rescoring the corrected
image crop expose useful geometry at the operating budget while preserving E003
old targets? Unit image;grouping reid. No model training,new correction fitting,
time prediction,mechanics or fresh-location claim. This request prepares a
reviewed version only:human approval of exact transfer/publication/execution is
required before any producer use. No fresh access exists under this protocol.

## One protected net-gain criterion

The single development claim requires all three logically necessary clauses:
macro-location recall gain>=+.05 at1FP/image,IoU>=.5;micro E003-hit GT identity
retention>=.95;total TP gain>=1. The last clause makes actual net target benefit
explicit:macro weighting alone can rise while total hits fall. It does not relax
or reinterpret E007. Comparator is unchanged E003 original rows and scores.
Each method uses its own global admitted prefix and unchanged atomic-tie greedy
matcher;GT identity(image_id,index). Undefined macro or baseline-hit retention
is inconclusive,not permission to proceed. Raw candidate coverage or score lift
cannot substitute for operating detections.

+.05 and.95 retain the established meaningful margin and preservation objective.
E003 development operating macro.289509 and oracle.683550 leave headroom;the
prior union oracle.723149 is only a geometric ceiling. E007's zero gain did not
come from the+.05 threshold:accepted gains stayed below the old score cutoff.
A pre-design analytic count on already seen training qualification rows found
177 geometry-gain pairs;27 have sqrt(parent proposer confidence)>=old cutoff
.2377838571,21 also pass the fixed.7 original near-duplicate guard. Probability<=1
therefore still allows some useful promotions under the same fusion rule. This
is an upper-bound readiness check,not new classifier inference,TPs or evidence
that21 targets are distinct/newly detected. Five reused development locations
and four seen training locations do not identify population generalisation.

## Unchanged classifier and candidates

Use exact E003 checkpoint bc304c5f... epoch2,MobileNetV3-small eval/inference mode,
unchanged weights/classifier. One corrected crop per inherited GT-free top40
parent/image;no new YOLO proposal generation. Train qualification corrections
are the existing S01-E007 location-excluded bank on353/1459/2028/5982. Its new
regression coefficients/scalers exclude these locations;the shared E003 encoder
saw all16 train locations. Qualification is conditional and already reused.
Development corrections use the existing E006 validation bank with full E005
head;no head fit or choice in E008. Distribution shift remains a limitation.

Verify all inherited source/config/lock/input/cache identities and replay the
existing correction bank before use. Validate prepared-image SHA and dimensions
for each image whose corrected crop is scored. Same own-box padding.1,clip,
Python-round crop edges,RGB Resize224/ImageNet normalization as E003. Extract
frozen full-network global-average pooled576 features onGPU1,then unchanged
classifier CPU eval,one thread,batches512,softmax crack score. Store pooled cache
and classifier outputs for exact replay. This GPU-feature/CPU-classifier backend
matches prior training score replay;validation originals retain their historical
GPU E003 scores. Do not claim cross-platform floating-point byte identity.

Corrected score=sqrt(parent proposer confidence*corrected-crop probability).
Qualification local parent remapping follows the inherited E007 scoped bank and
does not change GT identities. Original probability,score,coordinates,scoped ID
and row order remain byte-equivalent
as JSON values in the emitted original branch. No classifier-only promotion or
proposer-confidence refit. Scores are uncalibrated ranking values,not probabilities
of a valid crack box. No GT/IoU reference enters candidate admission at inference.

## Fixed additive admission and training qualification

Four predeclared score-ratio rules1/1.25/1.5/2. Admit a correction only when its
new fused score>ratio*original E003 score. Equality abstains. Reject correction
IoU>.7 with ANY original,including its parent;exact same coordinates always reject.
Then correction-only greedy IoU>.5 suppression in new-score descending order,
lexical image/box/parent ties. It cannot suppress or edit an original. Append
accepted rows in parent-ID order with unique c:<parent> IDs. Preserve every
original in its original list order. Parent-bank integrity is a validity gate;
actual operating retention still needs measurement,because added FPs or changed
matching can reduce the admitted prefix's old hits.

Score all12602 qualification alternatives once. Evaluate only the four frozen
rules on these four training locations. A rule qualifies when macro delta>0,
old-hit retention>=.95 and net totalTP>=1. No E007 replacement-harm/exposure20 gate
is reused:originals are never replaced;operating target loss and added FP burden
are the relevant risks here. Report duplicate/partial/background FPs and all
new/lost old target identities. Choose qualified rule by highest macro delta,
then retention,then netTP,then fewer additions,then larger ratio. Freeze it before
any new development scoring. No threshold sweep,coefficient fit or alternate
score aggregation. None qualified->stop before development;metric undefined
->inconclusive;otherwise observed lack of protected gain->negative training
qualification. Whole decision object and all four policies replay exactly.

If one qualifies,score each of the existing10877 validation alternatives once
and apply only that fixed rule. One development comparison;no reselection/refit.
All three development clauses required. Miss keeps E003 and stops this attempt.
Pass supports a bounded reused-development result only;any fresh confirmation
requires a new separately frozen/reviewed contract and human approval. Fresh
locations1174/1729/2246/2260/2485 and all reserves remain unaccessed.

## Budget,execution and evidence

Zero fitting:classifier,encoder,proposer,4 E007 heads and full E005 head unchanged.
One qualification crop-feature extraction/scoring cache;four training-only
comparisons;at mostone validation crop-feature extraction/scoring cache andone
comparison. No repeats after extract_started/score markers,duplicate Run or
actual comparison. S01-E008-R001 on GPU-server/D-26-09,GPU1 physical UUID
GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a after preflight availability/runtime.
Mac only author/import/unit/read-only analysis. No external push/transfer/producer
execution before human approval of the final 6.1-sol/Medium-reviewed version.

Scope:scripts/pavetrack_rescore_cv,tests/pavetrack_rescore_cv,own Experiment and
review records;inherited modules unchanged. Dedicated branch from approved remote
05f37c7 so unpublished E007 result commits are not silently included in publication.
E007 evidence inputs are read-only external archives,not new branch publications.

Minimum evidence:exact scoring caches,IDs/crops/image hashes/lineage,immutable
originals and accepted alternatives,rejected duplicate/ratio counts,all four
qualification outputs and full decision;development only if qualified;all-policy
and per-location tables,retained/lost/new identities,FP types,old/new score-prefix
counts,geometry-gain recognition diagnostic and oracle secondary;10k paired-
location bootstrap seed20261013 descriptive only. F00 all training rule margins;
F01 per-location comparator/candidate recall and retention for selected rule or
fixed ratio1 if none;F02 highest frozen E003score new/lost/admitted FP examples,
up to2 locations/role. Corrected-only FP examples are a separately labelled
secondary view,ranked by corrected score,up to2 locations. No informative example
is invented for an empty role. README_analysis,retrieval receipt,independent
6.1-sol/Medium evidence review and short Obsidian decision/result milestones.

Validity failure->inadmissible;unidentified metric->inconclusive;valid failure
->negative bounded comparison;valid pass->supports bounded development claim.
Preserve component advances without rescuing the primary. If corrected scores
enter the prefix but do not yield protected net benefit,identify FP/duplicate
cost and stop this frozen-classifier route rather than loosening ratios. If even
useful geometry cannot enter the prefix,redirect to more informative localisation
capacity/data instead of another unchanged selector. No new arm within E008.
