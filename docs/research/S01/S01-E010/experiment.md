---
storyline_id: S01
experiment_id: S01-E010
protocol_revision: v1
created_at: 2026-10-15
status: frozen_pending_independent_design_review
branch: codex/s01-e010-incremental-utility-20261015
base_commit: 9067eaa03382e007472191b82ea79c2fd9991d26
---

# Learn incremental hits and FP cost relative to E003

## Decision, evidence, and scope

C2, real-road current-image crack-box detection, image evaluation unit/reid grouping. Does one signed incremental-utility gate on existing corrected-crop features improve the finite reused-bank detection result while retaining at least95% of E003 old GT hits? Preserve E009 negative. It retained282/282, but112corrections appended/10inprefix were allFP(3partial/2duplicate/5background),new0/lost0/net0. The four known fixed-oracle new detections had q-scores too low both for parent admission and operation cutoff; dropping only the parent gate cannot fix them.

One coherent repair is changing the learned quantity from valid-box probability to E003-relative incremental benefit/cost, and therefore its decision mapping from probability attenuation to a signed utility gate. These two semantic changes belong to one utility method; no claim can attribute its effect to the loss alone. E008 score is retained for cross-branch ranking; predicted utility is never treated as a probability or multiplied into that score.

Reuse only pinned S01-E008-R001 corrected-pooled cache12602×576,float32, its score/receipt/evaluation and existing four-training-location metadata/GT. Reuse exact E009588-feature construction (576pooled+12scalars, same order). No E009 fitted head/q as input. Copy input hashes/lineage from E009 data_lock but use own protocol; no full inherited load() that opens prepared images. Source domain is conditional/reused: E003 encoder saw all16train sites, E008/E009 outcomes and all4sites have been viewed, correction heads exclude all4. Leave-site-out excludes only the new utility model/scaler/weights/labels, not the shared encoder or prior research design. No fresh/generalisation/development claim.

## Frozen GT-free eligible bank

All19855original rows, scores, probabilities, IDs, coordinates/order remain an unchanged prefix. For each correction compute fixed s0=sqrt(parent proposer confidence * E008 cached corrected probability). Statically eligible iff s0>parent original E003score, not exact original coordinates, and IoU<=0.7 with every original in its image including parent. No utility model, label or GT enters this eligibility; it is identical across folds for a given image. Ineligible rows are never training examples and receive no model prediction (archive explicit eligible=false,utility=null); they cannot be appended.

Do not apply correction-only NMS while constructing training labels. Labels are ONE-correction interventions, not a chosen policy of multiple corrections. At actual admission, eligible held correction must also have predicted U>0 (ties abstain); sort admitted corrections by fixed s0 descending/lexical image-box-parent tie break, apply correction-only NMS IoU>0.5, append by scoped parentID with unique c:parent IDs. Never suppress/replace/recalibrate original rows. No alternative margin, score multiplier, ratio, quota or policy arm.

## Direct single-correction utility target

For each fold F, let T be its THREE FIT locations only. Construct B_T from unchanged E003 original rows/images/GT in T and evaluate its inherited global operating prefix at1FP/image,IoU>=0.5 with atomic score ties and exact greedy GT matcher. H0 is its admitted GT identity set (image_id,index). Neither held images, held GT nor all-four operating threshold may determine B_T, labels, scalers or weights.

For each eligible correction c from T, evaluate A_c=B_T plus only c at fixed s0 using the SAME operating metric and its OWN global prefix. It is not enough to use a fixed baseline threshold; inserting c can move the budget cutoff and displace other original detections anywhere in T. Let Hc be that admitted target set. Store:

new_c=|Hc-H0|; lost_c=|H0-Hc|;
FP_c=1 iff c is itself admitted in A_c's prefix and is a false positive in that exact greedy assignment, else0;
U_c=new_c-lost_c-FP_c.

All three unit weights1 fixed before learned outcomes. An admitted false correction spends one FP slot even when totalFP stays capped, so FP_c is the correction's actual FP-role cost, not totalFP(A_c)-totalFP(B_T). A redundant valid correction that adds no new identity gets U<=0 even if it takes an old row's TP assignment; it is not rewarded merely for IoU>=0.5. Any harm to other old targets is included through full-prefix set difference. Non-admitted corrections have U=0. Label supervision uses current fit-partition GT only, never features/inference. This is an engineering detector-selection target, not downstream maintenance/inspection utility.

Counterfactuals must include exactly all static-eligible fit rows (no hard-negative mining or target-dependent sample choice). Do not use the previously reported full-bank23pairs/15missedtargets as train labels; those used all-four baseline coverage and are contextual counts only. Store per-correction fit IDs, cutoff, new/lost/FP/U so independent reconstruction is possible.

An implementation may accelerate labels with per-image matching/global score-group cumulative updates and skip c only if its score is STRICTLY below the first excluded original score group (cannot affect an earlier prefix). All ties and any candidate at/above that group require exact handling. Prove numerical/identity equivalence against full canonical B_T+[c] evaluation on synthetic tie/displacement cases and representative fixed-cache cases before execution. No approximate labels, local-image-only budget, or global-cutoff shortcut that leaks heldGT.

## One balanced signed-utility ridge head

Use four fixed folds held353/1459/2028/5982, all other3fit, no random row split. For each fit partition, compute mean/population std(floor1e-8) on its eligible training rows only, for exact588GT-free columns. Define strata by target sign positive/zero/negative. Each present stratum gets equal total mass, wi=1/(K*n_stratum); no resampling, truncation, winsorisation or hyperparameter sweep. Positive and negative utility strata must both exist in EACH FIT partition; zero may be absent. Missing sign support stops inconclusive before any new fit. Report sparse counts without changing weights after outcomes.

Fit one float64 CPU ridge with intercept:
L=0.5 sum_i wi*(theta^T zi+b-U_i)^2 +0.5*0.001*||theta||^2.
Intercept unpenalised. One linear solve per fold, no l2 alternatives/retry/pseudoinverse fallback. A correct weighted Gram solve and scaled loss/gradient must agree; accept finite coefficients/objective, final loss<=constant-zero initial loss and gradient infinity<=1e-7. Failure stops all remaining work, retain actual fit count. Four heads must all fit and verify before ANY held-location prediction. No all-four deployment fit or in-sample score substitutes. Predicted utility is signed count/cost units; only its sign selects additions. Original s0 ranking is unchanged.

This is a small finite-bank engineering test of a head/decision rule, not a statement that current sparse data supports high-capacity or independent generalisation.

## Feasibility before fit and one primary result standard

Before fitting, bind cache SHA/shape/dtype/parent IDs, old baseline rows/targets and metadata; reconstruct all eligible fit-partition counterfactual labels. Report U>0/U=0/U<0 by fold and fit location, class/source support, new/lost/FP roles and any numerical identity failure. Check target/partition isolation by poisoning heldGT in tests: no fit label or scaler may change. There is no held-label tuning or calibrator.

A single predeclared annotation-informed feasibility policy uses the FULL four-site baseline only for DIAGNOSTIC oracle labels, Ufull(c)>0, then applies the same GT-free eligibility/s0/NMS/append policy and same operating budget. It never supplies training labels or changes model/threshold/weights. If this fixed oracle policy fails the same protective net-benefit conjunction, stop without fits; this is a conservative study stop, not a mathematical ceiling or proof every gate is impossible (nonmonotone matching/NMS). It is one oracle diagnostic, not an additional learned comparison arm.

The ONLY learned primary conjunction, on pooled eligible-held predictions exactly once: E003 old-hit GT retention>=0.95 AND totalTP net>=1 AND macro-location recall delta>0 at1FP/image,IoU>=0.5. Same finite-bank qualification standard as E008/E009, not a relaxation or a5-point development claim. Undefined baseline macro/zero baseline hits is inconclusive. Original-row preservation never substitutes for old-hit retention. Case/per-site/partialFP/duplicateFP and calibration-like plots are diagnostics, not votes. Positive result is a bounded reused-training engineering increment, not significance or new-site effectiveness.

All4held sites remain previously consumed training sites. Fold-level annotation counterfactuals are preparation labels, not four extra final policy comparisons. Single-candidate labels need not add under joint selection; final1pooled comparison is mandatory and is the only learned result.

## Budget, authority, and stops

At most4newridge heads/one solve each, onepooled learned comparison. Max37806fit-row counterfactual labels before eligibility short-circuits and12602full-bank oracle-label slots (each scope once, cache receipts; deterministic verification only may replay). Zero new pixels/crop or feature extraction/E003encoder-classifier forwards/corrector fits/all-fourfit/development/fresh/reserve access. CPU1thread,gpu-server/D-26-09 only after exact human execution approval and independent code review. Max900seconds/headfit,3600totalincludinglabels/audit/fits/prediction/comparison,peakRSS4GiB. First identity/support/feasibility/numerical/resource/duplicate-run failure stops; no retry,extra arms or silent budget reset. Record every consumed fit marker; all four verified before predicting. Under budget exhaustion no model verdict, retain partial evidence only.

This turn authorises local design/preparation and read-only cached counterfactual support audit only. No actual ridge solve, learned prediction, new model scoring, source transmission, push or producer execution. DesignPASS requires subsequent exact implementation/testing and independent6.1sol-Medium code review, then final human approval of transfer/public branch/execution. No automatic follow-on Run or fresh unsealing after success.

## Outcome-to-solution map and minimum evidence

Validityfailure->inadmissible; support/undefinedmetric->inconclusive; valid primarypass->bounded positive engineering result and preparation of a separate study; valid primarymiss->negative, retainE003. If positiveU supports exist but all learned useful candidates suppressed, inspect positive/negative sign errors and held-site support before choosing one new representation/training lever; no threshold rescue. If sign errors are low yet joint budget harms dominate, inspect nonadditive candidate interactions and next propose one budget-aware set decision test, not another validity head. If support/oracle insufficient, stop before fitting and design a new training-evidence route on authorised training data; fresh sites stay sealed. This tests a concrete repair, not merely an explanation of E009.

Minimum artifacts:source/input identities, all fit-only baseline/counterfactual label receipts,new/lost/FP/U decompositions,weights/scalers/Gram residuals/coefficient/convergence/resource/fitcount; per-held prediction with eligibility status; immutable original prefix; exact pooled decision and per-location/new/lost/FP/prefix counts; F00primary margins,F01held-site variation,F02fixed highest-oldscore new/lost/FP coordinate schematics (up to2locations/role,explicitabsentroles),no image pixels; descriptive10000paired-locationbootstrap seed20261015 only; README_analysis and independent evidence/visual review. Until implementation the status is design-only, not Code Ready or execution approval. Scope:own experiment/review and future own runner/tests; inheritedmodulesunchanged, dedicatedbranch from approved9067eaa excludes unpublishedE009resultcommits.


## Independent design disposition — 2026-10-15

gpt-6.1-sol Medium independent review PASS, bound to frozen design commit202ff7386ebade72a4f41da8f747c10cb6d49ec0; see docs/reviews/S01-E010_design_review_20261015.md. No method, budget or result-standard change after review. Status only updated: implementation/code review pending, fit-support and fixed-oracle numerical checks not yet performed. Sign-balanced ridge output is a weighted-distribution score, not naturally calibrated expected utility. No fitting, new learned prediction, producer execution or fresh access authorised by this design verdict.
