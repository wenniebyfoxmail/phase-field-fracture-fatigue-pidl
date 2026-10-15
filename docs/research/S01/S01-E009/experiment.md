---
storyline_id: S01
experiment_id: S01-E009
protocol_revision: v1
created_at: 2026-10-15
status: frozen_pending_independent_design_review
branch: codex/s01-e009-localization-quality-20261015
base_commit: 663ace26341156c534d9e25f0a43198cf9f51c5d
---

# Cached corrected-crop localisation quality with E003 protection

## Decision and evidence

C2 real-road current-image crack-box detection. Can one fixed localisation-validity head on cached corrected-crop features produce positive finite-bank detection benefit while retaining at least95% of E003 detected GT identities? Evaluation unit image, grouping reid. This is a reused-training feasibility test, not new-site generalisation, forecasting, mechanics or a development result. No new run or fit is authorised by this design document.

E008 established useful score exposure:77–151 added corrections entered the operating prefix and1–4 previously missed targets were detected, but3–14 old targets were lost. Partial-overlap FPs rose from110 to130–162; duplicate FPs20 to21–25. Thus the primary measured lever is rejection of boxes with IoU<0.5, not more candidate coverage or a new score-ratio sweep. Keep E008 negative unchanged.

Reuse only S01-E008-R001 qualification_pooled_features.npz (float32 N×576, N12602), qualification_scores.json, scoring_receipt, evaluation and fixed original/pair bank, plus existing pinned training manifest metadata/GT for exactly353/1459/2028/5982. No original image or prepared-image file may be opened; prepared-image SHA strings are lineage metadata only. E008 source is c24ff8f286f0d13f4bc55278df6010965f47fe68; archive SHA ecd4e98a5bfa8cc240dcff22355eacab89889d4e5d22b32240d2c65dd51d4115; evaluation SHA902796c2e71fcc9e56295bb04ea422bd5d71c07dea46e5822368568ea744dcb9. Bind cache SHA/shape/dtype, parent IDs, all original rows and probabilities before use. Use exact E008 probability cache, do not rerun even the frozen classifier.

The four correction heads were already trained without these four locations. E003 encoder/classifier saw all16 training locations; E008 outcomes on all four have been viewed. Therefore leave-location-out below excludes only the new head/scaler, and does not create an untouched holdout. Label it conditional reused-training crossfit throughout.

## Single head and exact feature/target definitions

One logistic head with588 inputs:576 unchanged corrected-crop average-pooled values, followed by these12 GT-free scalars in this exact order:
1 logit(parent proposer confidence);
2 logit(parent E003 crack probability);
3 logit(corrected E003 crack probability from E008 cache);
4 log(corrected width/height);
5 log(corrected area/image area);
6 corrected width/image width;
7 corrected height/image height;
8 corrected centre x/image width;
9 corrected centre y/image height;
10 corrected/parent box IoU;
11 maximum corrected IoU with any non-parent original box in the same image (0 if absent);
12 maximum original frozen E003 score among non-parent originals overlapping the corrected box at IoU>=0.5 (0 if absent).
Clip probabilities to[1e-6,1-1e-6] only for logit. Geometry uses existing boxes and pinned metadata dimensions. No GT, labels, IDs, location encoding or chosen operating threshold enters feature construction or inference.

Binary target y=1 iff max corrected-box IoU with any GT box in its image>=0.5, else0 (empty GT gives0). Existing training annotations only. This is a valid-localisation target, not a novel-target/duplicate-removal label. Valid duplicates remain positive, so a learned duplicate-rejection claim is blocked; retain fixed GT-free duplicate guards and report duplicate FP cost separately. The feature overlap terms may identify invalid partial boxes but do not magically make valid duplicates negatives.

## Fit and leave-location-out separation

Four fixed folds, in order353,1459,2028,5982; fit each head on all cached rows from the other three locations, predict the held location exactly once. No random row split. Compute training-column population means/stds on the three fit locations only; floor std at1e-8. No held-location preprocessing, class weighting, balancing, sampling, calibration, early-stopping validation or hyperparameter choice. Standardisation for all588 dimensions is train-fold only. All fit rows have equal weight, preserving fit-fold class prior. Intercept zero and weights zero initially. Float64, oneCPU thread; seed20261015; logistic mean BCE plus0.5*0.001*L2 of weights, intercept unpenalised. Torch LBFGS max_iter200/max_eval250/history20/strong_wolfe/tolerance_grad1e-6/tolerance_change1e-9. Accept a fit only if objective finite, final objective<=initial and gradient infinity norm<=1e-5; any failure stops all inference/comparison, no retry or alternate model. Record closure calls, counters, means/stds, positive/negative counts and fit/held IDs. Empty class stops inconclusive.

The pooled out-of-fold predictions are the only candidate policy. Each held location uses its own fitted head; no rule is selected after outcomes. Also report each location and exact training composition. No all-four deployment head, no reuse of in-sample predictions for evaluation.

## GT-free admission with immutable E003 originals

Preserve every original row, coordinates, E003 probability, original score, ID and row order as an unchanged prefix. A correction score is s=sqrt(parent proposer confidence * E008 corrected E003 probability)*sigmoid(quality logit); this can only attenuate the E008 corrected score. There is exactly one fixed ratio1:append only if s>parent original E003 score. Ties abstain. Reject exact original-coordinate copies or corrected IoU>0.7 with any original (including parent); then correction-only greedy NMS IoU>0.5, higher s first, lexical image/box/parent tie-break. Append survivors by scoped parent ID; unique c:parent IDs. No GT used in these decisions and no original suppression, replacement, rescoring, calibration or quota change.

Compute baseline/candidate each at its own global prefix, both330images/330FP (1FP/image), IoU>=0.5, inherited atomic-score-tie greedy matcher and GT identity(image_id,index). Recompute all metrics/target sets. Original preservation is a data invariant, not a guarantee of old-hit retention; explicitly measure retained/lost/new old GT identities, incremental FP and prefix displacement. Do not splice cached E008 results into the new candidate verdict.

## One attainable primary criterion

All three clauses are necessary for this one finite-bank protective net-benefit decision: macro-location recall delta>0; retained old GT identities/282>=0.95; total TP net gain>=1. Undefined macro or zero baseline hits is inconclusive; any validity failure is inadmissible. A positive result allows preparation of a separate next study, never deployment or fresh access.

These are the same E008 training-qualification thresholds, not a relaxation of its5-point development criterion. E009 includes no development claim/comparison and therefore does not assert that5points has been reached. A single net new GT is the smallest countable engineering increment on this reused bank; it is not a statistical-significance or generalisation claim. Report effect sizes and four-location variation, with descriptive10000 paired-location bootstrap seed20261015 if plotted; no CI threshold votes on success.

Feasibility must be checked before any fit, using already-scored frozen arrays: exact label counts by location, head-training class support, candidate label/score upper-bound and a clearly GT-oracle-filtered ceiling under the SAME score formula and duplicate guards. Oracle q=y (1 for valid localisation,0 otherwise) is a feasibility diagnostic, not a prediction/performance arm; each learned q is in[0,1], so s cannot exceed E008 score. Report whether any useful newly detected target remains eligible and how much duplicate FP pressure survives the valid-localisation oracle. Because greedy matching/NMS is nonmonotone, call this an oracle policy, not a mathematical upper bound on recall. If oracle policy cannot achieve the primary protective net benefit, stop before fitting and redirect to geometry/duplicate utility modelling; do not train a head that cannot address the diagnosed ceiling. This audit is fixed ex ante, never a way to select labels/model/threshold after fits.

## Budget and stop rules

Exactly at most4 new heads,1 fixed pooled out-of-fold comparison; zero all-four fit, encoder/classifier/proposer/corrector updates, pixel access, crop extraction, probability re-inference, GPU jobs, development scoring, test/fresh/reserve access or hyperparameter arms. CPU producer gpu-server/D-26-09 only after code review plus exact human execution approval. Max900wall seconds per head,3600total including audit/fitting/comparison, peakRSS4GiB. First numerical, identity, feasibility, resource, duplicate-run or fit failure stops the run and subsequent folds; record how much budget was consumed. No retry under R001. Use fresh Run directory with pre-fit markers and per-fold receipts; budget counters include every actual fit even if failed. Cache-only deterministic verification of scores/metrics is allowed, does not repeat fitting or become an extra comparison arm.

If result passes: prepare a separately reviewed plan to test whether this effect survives independent evidence; no automatic data use. If negatives arise from valid duplicates consuming budget despite partial-FP reduction: keep the component improvement, stop this validity-only head and next test explicit incremental/duplicate utility supervision in a new contract. If partial-FP discrimination itself fails despite feasible oracle: stop this fixed linear representation/head and inspect capacity/data support before proposing one new lever. If label-based feasibility fails: no fit, redirect geometry/duplicate modelling. No additional E009 arms.

## Minimum evidence and review status

All source/input lineage, fold exclusion and feature/label reconstruction; true train/held counts; coefficients/scalers/convergence/resource traces; one OOF score for each exact parent; unchanged original prefix; rejected reasons; full fixed decision and per-location old/new/lost identities/FP types/prefix counts. F00 shows E003 vs candidate primary components, F01 all four held-location outcomes, F02 fixed highest original-E003-score new/lost/FP cases (up to2 locations/role; missing roles labelled absent), overlay only after a separately authorised existing-image access plan; E009 itself is pixel-free so existing E008 fixed montages may illustrate prior motivation but cannot be relabelled E009 cases. For E009 use pixel-free box-coordinate diagrams with GT/image dimensions from the pinned training metadata, clearly labelled schematic; report exact identities and geometric IoUs. README_analysis and independent evidence review required after execution.

This is a design-only freeze. Read-only6.1-sol/Medium independent design review is requested. A design PASS is not Code Ready or Run approval: implement the exact recipe, meaningful synthetic tests, bind source/config/lock, obtain independent code review, then prepare the final transfer/execution version for human approval. No fitting or producer transmission is authorised now. In-scope paths own Experiment, review and later own runner/tests; inherited modules unchanged. Dedicated branch from approved663ace2 excludes unpublished E008 result commits.
