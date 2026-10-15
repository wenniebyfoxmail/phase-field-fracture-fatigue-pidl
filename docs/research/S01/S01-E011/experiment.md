---
storyline_id: S01
experiment_id: S01-E011
protocol_revision: v1
created_at: 2026-10-15
status: frozen_pending_independent_design_review
branch: codex/s01-e011-scalar-utility-20261015
base_commit: 6ab576bc1c688e1903b0d2532c5f1698db5b1588
---

# Low-capacity incremental utility from the existing twelve scalar features

## Question, evidence and repair

C2 real-road current-image box detection; image evaluation unit, location grouping, no future horizon. Can one fixed12-scalar linear utility head turn an existing corrected-box opportunity into actual E003-relative net detections while retaining at least95% of old hits? Primary comparator is unchanged E003. E010 is the fixed prior method/component reference, not a newly fitted second arm.

E010 retained282/282 old detections but gained0;2901 appended candidates never entered its operating prefix. All four already known positive-singleton-utility corrections were rejected (stored OOF utilities around-1.006,-1.046,-1.097,-1.353) despite corrected E003 scores0.600–0.776 above cutoff0.237784. Negative-utility rejection worked on the full-bank diagnostic249 cases, but useful-candidate sign selection did not. Fit positive support was only4/1/4/3. A589-parameter head with that sparse support motivates a controlled lower-capacity hypothesis; the evidence does not establish overfitting or capacity as the unique cause.

The sole scientific intervention is selecting the complete PRE-EXISTING12-scalar block instead of576pooled+12scalars, reducing589parameters to13including bias. This changes representation and capacity together; a result cannot attribute an effect to parameter count alone. All labels, sign weights, loss, regularisation, training/held partitions, static eligibility, score mapping, tie handling, NMS, metric and primary standard remain E010-identical. No post-hoc subset, transform, interaction, threshold, l2 or alternative model selection.

Research disposition entering E011: repair. It tests a concrete fix for useful-candidate rejection. This experiment is not a guarantee of gain, and sparse support remains a material risk even with13parameters.

## Frozen evidence and information boundary

Use only pinned E008-R001 corrected score/evaluation/receipt/cache identities and existing four-train-location metadata/GT; data_lock.json preserves those exact identities. E010-R001 input audit/evaluation are pinned for identity comparison and diagnostic context. Do not use E010 coefficients, stored OOF utilities, gate decisions, or fitted q as learner input, labels, sample weights or calibration. Reconstruct the SAME fit-only counterfactual labels from cached original/corrected rows and current FIT GT. Compare all fold label records/baselines/indices/sign counts and full-bank diagnostic content to the E010 input audit excluding protocol/run lineage fields; discrepancy stops before fit. If accelerating by reading a verified E010 label receipt, isolate its appropriate FIT-fold section and prove equality to canonical recomputation before execution; never use its full-bank oracle labels for training.

All four sites353,1459,2028,5982 and prior outcomes have been viewed. E003 encoder saw all16training sites; correction heads exclude these four. Leave-one-site-out excludes only the NEW scalar-head coefficients/scaler/weights/labels. Design choice uses consumed evidence; there is no untouched-site, statistical generalisation, development, fresh-location or mechanics claim. Fresh/confirmatory/reserve locations remain sealed.

## Exact scalar contract (fixed order)

1. parent_proposer_logit
2. parent_crack_logit
3. corrected_crack_logit
4. log_aspect
5. log_area_fraction
6. width_fraction
7. height_fraction
8. center_x_fraction
9. center_y_fraction
10. parent_iou
11. nonparent_max_iou
12. nonparent_overlap_max_score

These are exactly E009 features(data)[:,576:588] and E010's final12columns. Probability logits clamp to[1e-6,1-1e-6]; geometry uses corrected width/height/centre relative to metadata image dimensions. parent_iou compares corrected with its parent. Nonparent statistics use ALL other original E003 boxes in that image, excluding the parent; maxIoU defaults0, and highest original score among nonparents with IoU>=0.5 defaults0. No GT, GT-overlap, global operating cutoff, new pixels or new learned embeddings enter the features.

Prefer a scalar-only builder to avoid allocating a learned pooled matrix; an inherited588builder followed by the exact fixed slice is mathematically permissible only if no pooled column enters scaling, fitting or prediction. Verify identity to the inherited scalar block and invariance to poisoned pooled values AND GT. Features must be float64 finite[N,12]. The576pooled cache may remain an identity-checked inherited dependency, but none of its values contributes to the head. Training mean/population std (floor1e-8) uses eligible rows of the three FIT locations only; never held rows. No feature selection from the four rejected cases.

## Unchanged candidate policy and direct utility labels

Preserve all19855original E003 rows, IDs, boxes, scores, probabilities and order as an immutable prefix. For every correction s0=sqrt(parent proposer_confidence * cached corrected E003 probability). Static eligibility is GT-free: s0 strictly greater than parent original score, corrected coordinates different from every original in its image and IoU<=0.7 with every original INCLUDING parent. No correction-only NMS while forming labels.

For each held site in353/1459/2028/5982, use only the other THREE FIT sites to form original bank B_T and its own global1FP/image,IoU0.5 prefix under canonical greedy assignment and atomic equal-score groups. Baseline H0 is the admitted GT identity set(image,index). For EACH statically eligible FIT correction c individually, evaluate B_T+[c] at unchanged s0 with a newly determined own prefix; Hc is its admitted identity set. Store new=|Hc-H0|,lost=|H0-Hc|,FP_c=1 iff c itself is admitted and takes a false-positive role in the SAME canonical assignment,else0. U=new-lost-FP_c with all unit weights1. Valid duplicates can be FP; maxIoU<0.5 is not the FP definition. Budget displacement may affect old targets in any FIT image, so no local-image or fixed-cutoff approximation.

Every eligible FIT row gets a label, including0. Never mine/select by GT. The only safe shortcut skips a candidate STRICTLY BELOW the first EXCLUDED original score group; at/equal/above must undergo canonical handling. Test atomic ties, cross-image loss, valid duplicates, shortcut exactness and held-GT poisoning. No held/full-bank cutoff or annotations determine FIT labels/scalers/weights.

After all four heads fit and verify, predict ONLY eligible held rows. Ineligible rows explicitly have eligible=false,utility=null. Admit only predU>0; zero ties abstain. Utility is a sign gate, never a probability or score multiplier. Rank admitted corrections by UNCHANGED s0 descending, lexical image/box/parent tie break, correction-only NMS IoU>0.5; append sorted by scoped parentID with unique c:parent IDs. Originals are never suppressed, replaced or recalibrated. There is one policy and one pooled learned comparison.

## Fixed loss, fit sequence and numerical admission

Positive AND negative U strata must exist in EACH three-site FIT bank before ANY fit (zero stratum optional). Sign groups positive/zero/negative receive equal total weight: wi=1/(K*n_sign), no sampling. Fit float64 linear ridge with bias: L=.5*sum wi*(theta^T zi+b-U_i)^2 +.5*.001*||theta||², bias unpenalised. Solve ONE13x13 normal system per fold, no retries, pseudoinverse fallback, alternate penalty or calibrator. This weighted-distribution score is not a naturally calibrated expected utility.

Verify finite coefficients, initial zero-model and final loss, final<=initial, analytic gradient infinity<=1e-7 and consistent Gram residual, partitions/scalers/sign weights. Record consumed fit marker before each solve. All FOUR heads must pass before ANY held prediction; no all-four deployment fit. First failure stops, actual consumed fit count preserved.

## Feasibility, criteria and component milestones

Before fits, verify cache/metadata/baseline identity, exact label equivalence and positive/negative FIT support. One fixed FULL-bank GT-informed oracle uses Ufull(c)>0 and the SAME static gate/s0/NMS/append/budget. It must pass the same primary conjunction or stop without fitting. This is separate diagnostic context, never train labels, an extra learned arm or a mathematical upper bound (nonadditive matching/NMS). Expected existing support is7332eligible rows, positive counts4/1/4/3, full-bank oracle282old+4new/0lost,macrodelta0.0093254. Reconstruct rather than assuming these counts.

The ONLY learned primary criterion is the pooled OOF conjunction at1FP/image,IoU>=0.5:

- old E003 GT-hit retention>=0.95;
- totalTP net>=1;
- macro-location recall delta strictly>0.

Each clause is necessary: preserve existing detection, add actual targets at the same FP budget, and avoid a gain solely from weighting a large site while harming the average site. This is unchanged from E010, not a relaxed success definition. Undefined baseline macro/zero old-hit set gives inconclusive. Integrity/identity failure is inadmissible.

Criterion calibration: baseline282TP/330FP,macro0.7763889 over330images/330provided GT targets and only4reused sites. The empirical fixed GT-informed opportunity is4net targets and about0.009325macro, not a proven ceiling. A one-target gain with no loss is a meaningful minimal finite-bank action signal and less than that observed opportunity; a recovered target at a108/105target site changes macro by approximately0.002315/0.002381. Published GT uncertainty is unquantified, so no physical/reference-error or statistical-significance claim follows. Per-site baseline recall0.5/0.805556/0.895238/0.904762 is reported to expose variation. Four-site bootstrap is descriptive, not power or independent validation.

Predeclare separate component milestones, which never rescue the primary verdict: L0 input/numerical/sequence integrity; L1 at least one of the FOUR ALREADY KNOWN useful candidates gets positive held utility and survives admission (report all four, no cherry-picking); L2 actual additional hits or other observable end-metric progress that still misses any primary clause; L3 protective net-benefit conjunction. Also report all249known negative-utility cases and all singleton-neutral selections, number appended/inprefix, old/new/lost and FP roles. These diagnostics use consumed full-bank annotations only after prediction, not model tuning. Do not require recovering all four as another primary gate.

## Budget, authority and evidence

At most4new scalar heads/one solve each and1pooled learned comparison. Same label-slot caps as E010:37806FIT and12602full-bank oracle before eligibility; deterministic verification replays permitted, not new arms. CPU1thread on gpu-server/D-26-09 only after separate code review and exact human source/publication/R001 approval. Max900seconds/headfit,3600total including labels/audit/fits/prediction/comparison,peakRSS4GiB. E010's65second/0.68GiB execution supplies resource context; these are hard caps, not planned consumption. Zero image/crop reads, pooled feature extraction, encoder/E003 forwards, corrector fitting, all-four refits, development comparisons or fresh/reserve access. Stop on identity/support/feasibility/numerical/resource/duplicate-run failure, no retry or budget reset.

Minimum outputs: input/source identities and exact12column feature contract; fit-only label decomposition/indices/cutoffs/GT sets; weights/scalers/13coefficients/objectives/Gram residuals/resource/fit counts; eligible/null per-row held utility; unchanged original prefix; old/new/lost/per-site/FP/prefix results and decision. F00 shows primary margins against E003, F01 all four sites, F02 fixed highest-oldscore new/lost/FP coordinate cases (up to2distinct sites/role, absent roles explicit), F_preparation shows support and fixed diagnostic opportunity. No source pixels. Include case JSON/CSV, README_analysis, descriptive10000paired-site bootstrap seed20261015, fixed-four-useful-candidate sign/admission table, and independent numerical/visual evidence review. Record E010 and E011 component metrics side by side from archived results; do not rerun/refit E010 or choose a winner post hoc. Keep raw results local/producer, only approved source published.

This turn authorises design freeze and independent6.1sol-Medium DESIGN review only, plus approved E010 result retrieval/QA/archive. No E011 solve/fit, new learned prediction, source transmission, push or producer execution. Design PASS requires subsequent implementation/testing (including scalar/pooled invariance and label equivalence), independent exact-commit code review, then human approval of the final source/public branch/R001 version.

## Outcome-to-solution map

Validity failure->inadmissible; support/undefined metric->inconclusive; primary pass->bounded engineering gain/advance, prepare a separate next study only; valid primary miss->negative, keep E003. Preserve L0/L1/L2 findings separately.

If useful signs recover but joint budget creates old-target losses, the next proposed intervention addresses joint candidate/budget decisions under a new reviewed contract. If this one reduced-capacity test still fails to produce protected net benefit because useful-candidate signs do not recover, stop cycling through cache-only linear feature/penalty/threshold variants. Redirect to a TRAINING-evidence enrichment design that adds qualified positive incremental examples across authorised training sites while retaining an isolated evaluation partition; name locations/reference/annotation budget and stop rule before access. Do not unseal confirmation sites as a remedy. If netTP improves but another primary clause misses, diagnose site-specific old-target harm before defining one new repair; no threshold rescue here. Capacity remains a hypothesis regardless of outcome because representation also changes. The endpoint is a measured repair path toward actual detections, not a cause-only review.

## Worktree and scope

Dedicated branch codex/s01-e011-scalar-utility-20261015 from approved public6ab576bc1c688e1903b0d2532c5f1698db5b1588, excluding unpublished E010 result commits. Current scope only docs/research/S01/S01-E011 and its design review. Inherited runners/tests/protocols remain unchanged; implementation is a later authorised stage. No Pages or external messages.
