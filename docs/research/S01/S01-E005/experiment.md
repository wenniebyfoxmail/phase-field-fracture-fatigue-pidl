---
storyline_id: S01
experiment_id: S01-E005
protocol_revision: v1
created_at: 2026-10-13
status: frozen_pending_independent_review
branch: codex/s01-e005-box-refinement-20261013
base_commit: ab4aa7817977d73a54bca39a6ab77191926d988f
---

# Frozen-feature box refinement to convert coverage into detections

## Question and result standard

C2 / real-road / current-image crack-box detection, grouped by `reid` location.
Does one train-only frozen-feature box head convert existing tiled candidates
into more valid detections at the same 1 FP/image operating budget than frozen
E003? Input: one current RGB image and original candidate geometry. Reference:
released workbook crack boxes; IoU>=0.50, greedy one-to-one matching. This is
image detection, not physical crack absence, metrology, growth or forecasting.

Primary: paired absolute macro-location recall difference at 1 FP/image,
candidate minus frozen E003. Metric, atomic score ties, global threshold and
zero-target handling are inherited unchanged. Success margin >=+0.05 absolute:
a meaningful five-percentage-point conversion improvement over the stronger
E003 baseline; same criterion in development and fresh confirmation. It is a
practical experiment decision margin, not a claim of deployment utility.

Development uses the same five reused validation locations, so effects there
are exploratory. Only after exact model/validation freeze and delta>=+0.05 may
five still-unused locations 1174/1729/2246/2260/2485 be acquired once. A missing
identifiable primary is inconclusive; negative development stops fresh access.
A fresh primary pass supports only this fixed selected new-location set.

## Intervention frozen before execution

- Reuse E002 tiled proposer and E003 epoch-2 ranker hashes in run_config.json;
  train proposals, validation scores and development image manifest are frozen
  external inputs. No CNN/proposer training, score change or new proposal arm.
- Associate each train proposal to maximum-IoU crack GT iff IoU>=0.05; earliest
  GT index breaks ties. Reference boxes come only from the 16 train locations.
- Train-only context audit: padding p means extra p*proposal width/height **on
  each side**, image-clipped and Python round to integer crop edges. Audit the
  fixed choices 0.5,1.0,2.0. Full containment uses exact coordinate inequalities
  on this rounded crop; no tolerance. Choose smallest p with target-balanced
  containment >=0.90. Each represented GT has equal mass, shared across its
  associated proposals. Also report raw proposal containment, represented and
  unrepresented GT counts, clipped target count. This input visibility check
  uses no validation/test labels or performance. If none passes, stop before
  extraction/fit and request an independently reviewed input amendment; do not
  try a new context/model silently. It is an observability screen, not evidence
  of detection quality; 90% allows a disclosed minority of partial views.
- Freeze eval-mode E003 MobileNetV3-small `.features` -> `.avgpool` -> flatten:
  576 pooled features. Existing transform: RGB, Resize(224,224), ToTensor,
  ImageNet mean [.485,.456,.406], std [.229,.224,.225]. No stochastic augmentation.
  Append six geometry features in config order: log aspect, log image area
  fraction, width/W,height/H,cx/W,cy/H. GT is never a prediction feature.
- Train standardization: unweighted means and population standard deviations
  across associated train rows, floor1e-8. Features stored float32, fit float64.
- Four targets: dx=(GTcx-cx)/w,dy=(GTcy-cy)/h,log(GTw/w),log(GTh/h).
  Fit **clamped** targets: dx/dy in [-2,2], log scales in [log .25,log4].
  Report clipping count; all associated rows remain, including partial overlaps.
- Each represented GT receives total weight1/G; its n_g proposals weight
  1/(G*n_g), total mass1. Objective = .5*sum_i w_i*||D_i Theta-Y_i||²
  + .5*.001*||Theta_without_intercept||². D is standardized features plus1.
  Single closed form: (D'WD+R)Theta=D'WY, R=.001 I except final intercept0.
  One CPU thread; four outputs fit jointly; no regularization/model sweep.
- Numerical acceptance: finite arrays/parameters, normal-equation gradient
  infinity norm<=1e-8, final objective<=zero-head objective+1e-12. Recompute
  train audit, scaler, objective and gradient from exact cached train arrays.
- At prediction: same selected crop, features/scaler, four outputs; nonfinite
  output is inadmissible. Clamp offsets/scales to training bounds, decode box,
  clip to image, fallback original if clipped width or height<1 pixel. Report
  bounded/image-clipped/fallback counts. No GT-dependent correction selection.
- Preserve original candidate IDs and E003 score sqrt(proposer*crack_probability).
  Deterministic NMS suppresses only IoU>0.5 within image, sorted by descending
  frozen score, reid,image,box,candidate ID. Retained rows preserve input order.
  Replay identical NMS on originals and require IDs/order/boxes/scores unchanged;
  otherwise evidence is inadmissible. Candidate arm includes this fixed duplicate
  handling as part of box refinement. No extra score or NMS threshold sweep.

## Validity and outcome map

Partition identity, exact source/checkpoint lineage, actual GPU1/runtime,
train-only fitting/context/scaler, unchanged E003 scores and reproducible metric
are necessary admissibility checks. Failure means inadmissible, not method
negative. No represented targets / no identifiable recall means inconclusive.

Valid development delta<+0.05: negative for this fixed head; preserve positive
component gains separately, retain E003 and do not access fresh confirmation.
Valid development pass: freeze head, scaler, selected context, source/config/
lock, validation pre/post-NMS outputs and authorization before downloader access.
Fresh pass/fail: supports/negative for the fixed location-generalisation claim.
No fresh computation: new-location claim inconclusive. Do not loosen a viewed
margin or erase useful partial progress. Findings must end in adopt/retain or a
specific reviewed correction hypothesis, not only a failure explanation.

## Budget, evidence and execution

One extraction, one fit, one validation evaluation, at most one authorized fresh
evaluation. Fresh Run S01-E005-R001 on gpu-server / D-26-09 GPU1, check availability
and runtime before launch; Mac only imports/tests/analysis. Raw assets in producer
run and local_archive/experiments/S01-E005/runs/S01-E005-R001/.

Required: context audit; train/validation feature receipts; frozen model; exact
paired rows before/after NMS; primary, per-location table; correction flags;
paired max-IoU changes; oracle coverage; FP decomposition; two figures with
README_analysis.md; producer receipt/retrieval check and independent evidence
review. F01 same-scale E003/refined per-location recall and +0.05 margin, 10,000
paired-location bootstrap seed20261013 (descriptive for reused validation).
F02 exact-budget recovered TP, lost TP and candidate FP examples, highest frozen
score then lexical tie order, two distinct locations per role; original/refined/
GT overlays. All raw rows remain authoritative, examples do not vote.

In scope: scripts/pavetrack_box_cv, tests/pavetrack_box_cv, owning Experiment,
review records and dated S01/Obsidian milestone. Inherited helpers remain unchanged.
