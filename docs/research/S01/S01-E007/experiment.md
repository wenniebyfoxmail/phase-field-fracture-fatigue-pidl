---
storyline_id: S01
experiment_id: S01-E007
protocol_revision: v1
created_at: 2026-10-13
status: frozen_pending_independent_review
branch: codex/s01-e007-paired-harm-20261013
base_commit: 221d41aaf2b69d39adfa522c14497b76406f90b3
---

# Original-target harm and paired gain with abstention

C2 / real-road current-image crack-box detection. One bounded development claim:
a paired harm/gain decision can retain E003 detections and convert correction
geometry into actual net detection benefit. Unit image, grouping reid; same16
train/five reused development locations. No future, mechanics, physical absence
or new-location generalisation claim. No fresh confirmation access is permitted
under this development-only contract, even after a pass. A pass proposes a
separately reviewed fresh confirmation contract; it is not deployment authority.

## Result standard and attainable range

Protected detection gain requires BOTH macro-location recall delta>=+.05 at the
same1FP/image,IoU>=.5 and micro baseline-hit GT identity retention>=.95. Comparator
unchanged E003 outputs/scores (115TP/302FP,macro.289509 on reused development).
Use each method's own admitted prefix, atomic score ties and unchanged greedy
one-to-one matcher. Identity(image_id,GT index). Baseline zero-TP gives undefined
retention and inconclusive claim. Missing primary never grants confirmation.

+.05 is the existing meaningful detection margin, not a threshold relaxed after
E006. E003 proposal oracle.683550, E005 original/corrected union oracle.723149
leave substantial headroom over operating.289509; the union gain.039599 alone
cannot meet+.05. The route must also recover currently coverable but undetected
GT through better coordinates at fixed scores. This is a feasibility upper bound,
not proof a linear paired head can attain the margin. Five reused locations and
correlated proposals cannot establish population confidence or generalisation.
.95 permits at most5 losses among115 baseline hits; net gain needs newly detected
targets, not just improved pair classification or coverage. Report all progress
but retain the frozen verdict when either clause fails.

## Train-only qualification and correction generation

Qualification locations fixed353/1459/2028/5982 (E006 numeric-fold3); remaining12
are decision-fit locations. The shared E003 encoder already saw all16 train
locations; qualification excludes new coefficients/scalers/reference fitting,
not the encoder. It is conditional, not end-to-end holdout.

Fit3 ridge correction heads on the12 decision-fit locations with numeric-sorted
location index modulo3 exclusion (8 fitting/4 held each). Thus every decision-fit
pair uses a head that excludes its own location AND all4 qualification locations.
Fit a fourth ridge head on all12 to create4 qualification-location corrections.
Each uses hashed E005 context features/associations,padding4,GT-balanced ridge
l2=.001,train-only scaler,offset±2,scale.25..4,imageclip,side<1fallback,asE006.
No E006 fold coefficients are refit/reused implicitly. Four actual new fits.

Parents by GT-free E003score top40/image,lexical originalbox/parent ties. E003
train scores replay from its separate padding.1 pooled classifier cache. Original
spatial features reused from verified E006 cache. New corrections require their
own padding.1 RGB crops/E003 features[:-1]96x7x7,adaptive avgpool3x3,C/y/x order.
Train paired input1745 values:864 original+864 corrected spatial;6 original+6
corrected geometry;dx/oldwidth,dy/oldheight,logwidthratio,logheightratio;E003logit.
No GT or IoU enters inference.

For each original pick highest-IoU GT, lowest index on exact IoU tie. Protected
if original IoU>=.5. Harm=protected AND correction IoU against THAT GT<.5.
Gain=any GT with correction IoU>=.5 but original IoU<.5. Both flags can be1 if
switching to a different target; such a change remains harmful. No-GT image gives
both0. Gain is pair geometry, not a claim of novel full-bank coverage or net TP.

## One paired model and abstention qualification

Joint two-logit linear head,outputs(harm,gain),one float64 L-BFGS optimization.
Train-only unweighted means/popstd floor1e-8;equal-location/equal-pair prior mass,
then each output class-balanced to.5/.5. Average the two BCE losses and add
.5*.001 coefficient-squared sum;bias unpenalized. Zero init,max200,strongWolfe,
gradienttol1e-7,changetol1e-12,one CPUthread. Finite,final<=initial+1e-12,
grad_inf<=1e-5;exact objective/scaler/weights/gradient replay. Both classes must
exist in both fit outputs;otherwise qualification is unidentifiable and stops.
Scores are uncalibrated rankings, not probabilities with a risk guarantee.

First fit uses12 locations. Four PREDECLARED policies differ only harm-score
limit(.01,.025,.05,.1);gain score must be>.5, harm<=limit;else abstain original.
Unchanged E006 conflict rule protects nonparent originals and earlier accepted
corrections atIoU>.5,score-desc order;original IDs/count/order/scores unchanged.
Each policy evaluated ONLY on4 qualification locations. It qualifies if exact
budget macro recall delta>0 and micro retention>=.95, AND among accepted originally
valid parents empirical same-target harm<=.05 with>=20 such accepted exposures.
Twenty exposures merely allow measuring a .05 empirical rate (one harm); it is
not20 independent units, a confidence bound or guaranteed test retention.
Select qualified policy by largest macro delta,then retention,then fewer accepted
corrections,then smaller harm limit. No other thresholds,searches or policies.

If none qualifies,stop before all16 refit/development comparison. Report whether
failure is insufficient exposures/classes(inconclusive qualification) or observed
harm/no gain(negative qualification);development claim uncomputed. Preserve
partial protections/coverage/model signals and a concrete next route.
If one qualifies, freeze that threshold, then one second paired-head fit on all16
using the fixed3-fold/qualification pair cache. Reusing qualification labels for
this deployment refit is disclosed; qualification does not evaluate these new
coefficients. The final head and E005 full16-data correction head can shift from
qualification; the single development comparison is decisive for that shift.
No fifth ridge fit. No final refit or development evaluation before qualification.

## Execution, stop rules and evidence

Author/import/unit/analysis onMac;actual4ridge and up to2paired fits on
GPU-server/D-26-09,GPU1 after availability/runtime check. Scope only
scripts/pavetrack_paired_cv,tests/pavetrack_paired_cv,docs/research/S01/S01-E007,
review records and dated S01 claim impact. Inherited source remains unchanged.
Fresh Run S01-E007-R001;reuse verified E006 context/scorer/original spatial caches,
extract only new corrected spatial features. Budget4 new ridge fits,1 qualification
head,at most4 train qualification comparisons,at most1 all16 refit and1 development
comparison;no fresh pixels or unseen confirmation. No retries after actual fit
unless reviewed execution-only amendment can prove no duplicate scientific fit.

Independent exact-source/config/lock/protocol review required before launch.
Validity failures are inadmissible;numerical success does not prove detection.
Protected primary miss stops current Run,retains E003 and seals fresh. Track
component milestones:valid same-target labels,train harm/protection,qualification
actual gain,and final exact-budget gains/losses. If protection improves but no
net gain,redirect toward more informative localisation capacity/data rather
than repeatedly loosening thresholds. No extra arm underE007.

Minimum evidence:source/input/run/cache receipts,4heads and split/scaler/objective
replay,paired labels/features/probabilities,two fit histories when applicable,
all4 qualification metrics/exposures/harm and fixed selection,final outputs and
exact target-retention replay if qualified,per-location tables/FP types/oracle;
F01 qualification and development paired recall/retention with thresholds;
F02 strongest frozen-score new/lost GT and admitted FP,up to2 locations/role;
10k paired-location bootstrap seed20261013 descriptive only;README_analysis,
retrieval receipt,independent evidence review and Obsidian milestone. Qualification
stop requires its decision figure even without development. Successful launch,
classifier score or scalar loss is not the result endpoint.
