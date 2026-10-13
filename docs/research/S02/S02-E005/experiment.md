---
storyline_id: S02
experiment_id: S02-E005
protocol_revision: v1
status: prepared_pending_independent_code_review
claim_class: C3_transition_prediction_diagnostic
evidence_domain: controlled_experiment
scientific_verdict: not_evaluated
---

# Published-DIC-label history increment exploration

Owner S02-E005; dedicated branch `codex/s02-e005-fatacrack-label-exploration-20261013`, base2136154. User on2026-10-13 authorizes exploration/training. This is a **new, explicitly narrower target**, not a PASS or amendment rescuing the blocked physical-metrology protocol.

## Frozen contract v1, before any scored fits

- Question: do two older boundary-response differences add held-later-time predictive information about the released tip-x label beyond current observations and recent tip growth?
- Unit: F/FF released records; no certified physical-specimen independence, population inference, road transfer or physical error accuracy. Data including evaluation tails are development-exposed.
- Issue time: after current cycle N max/min DIC pair and released tip estimate are available. Horizon exactly1000cycles. Target Δx=x(N+1000)−x(N), mm. Constant-load continuation is a declared scenario, not a future measured-load input.
- Required keys: N−2000,N−1000,N,N+1000 in direct finite tip and all four boundary channels. No cycle1 column guess,999→1000repair, imputed target or outcome-ranked exclusion. Expected F379/FF107.
- Fit/evaluation: target-cycle sorted eligible rows, prefix floor(0.7*n), remainder rolling evaluation. F265/114; FF74/33. Last fit target must be no later than first evaluation origin. No retraining in evaluation. Past evaluation measurements enter only once observed. This is one-step rolling, not autonomous rollout or untouched confirmatory testing.
- Fixed input ROI: x∈[1,49]mm; means of top/bottom uy/ux give opening and shear differences in mm. Do not normalize by a disputed actual-force value, infer stiffness or claim calibrated coordinates. Treat CSV values as their published representation.
- B0 persistenceΔx=0; B1 secantΔx=x(N)−x(N−1000).
- M0 features: current x,y,recentΔx,cycleN,current opening,shear.
- M1 same M0 plus opening/shear change N−(N−1000) and (N−1000)−(N−2000). No extra past-tip feature. Shared DIC error remains a limitation.
- Learner: ridge alpha1, fit-prefix population-standardization only; drop columns with scale≤1e−12; intercept not penalized. Two fits/record, four fits total; no seeds/search/extra models/clipping or smoothing. CPU NumPy, no neural training.
- Primary descriptive quantity: equal-record mean of MAE(M1)−MAE(M0); expose both record values and B0/B1 comparisons. No physical PASS margin, statistical significance or window-bootstrap CI. Improvement supports only this bounded published-label diagnostic; not Takens embedding or damage identification. If M1 fails to beat the simpler controls, report that limitation even if it beats M0.
- Validity failures: locked-file mismatch, chronology/phase-channel keys mismatch, missing fixed ROI/channel, nonfinite outputs or fit/evaluation information leakage→inadmissible. Missing independent metrology is explicitly outside this label-only claim, not silently assumed repaired.
- Stop/resource cap: one scheduled fit bundle only; maximum10minutes CPU, one BLAS thread, no GPU memory allocation. No post-result alteration of features/split/alpha/labels. Negative/inconclusive remains recorded; code fixes after viewed results require an explicit validity review/new revision rather than scientific retuning.

## Data, provenance and readiness

10 required source CSVs fromhttps://zenodo.org/records/2329057; official MD5 identities in`data_lock.json`. Current acquisition raw root`local_archive/open_data/fatacrack_qualification_20261013/`. Original publication thickness/load differences remain documented in the prior qualification audit. Preserve other frozen datasets/holdouts.

Reuse search found the no-fit S02-E003 secant evaluator, but it only handles DCB workbook labels and cannot join fixed boundary-channel histories. This new small runner reuses the persistence/secant and macro-record comparison contract. Mac runs only deterministic prepare and synthetic causality/unit checks; real fit selected producer`gpu-taobo`, using an attributed fresh /mnt/data2/drtao/wennie/S02-E005-R001 root, CUDA_VISIBLE_DEVICES=0 with CPU-only NumPy and no CUDA libraries. CPU preflight and storage required. Source snapshot bound to committed code; branch pushed for cross-machine recoverability.

Required before fit: independent read-only Code Ready review of exact commit/runner/data lock/protocol, user-selected review channel per research-review-channels workflow. No fit executed during preparation.

Minimum evidence: exact prepared-origin/split table, coefficients/standardization, all147 evaluation predictions, per-record summary, producer receipt/retrieval verification, and all evaluation trajectories plus paired method-error plot made from scored outputs, README_analysis and bounded independent evidence review. Execution and label-diagnostic conclusion recorded separately.

## Outcome map / bottleneck

Validity fails→inadmissible; primary computed→report descriptive sign and simple-control comparison without physical success label; unable to compute→inconclusive. Measured failure may distinguish response-history versus current-state model weakness, but cannot justify adding arms after results. Real metrology/independent trajectories remain separate acquisition bottlenecks.

## Reviews and Runs

Code review: pending channel selection and exact-snapshot dispatch. Run S02-E005-R001: not_started. Evidence review: not_started. No claim-bearing fitted result yet.
