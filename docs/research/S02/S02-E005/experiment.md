---
storyline_id: S02
experiment_id: S02-E005
protocol_revision: v1
status: closed_descriptive_diagnostic
claim_class: C3_transition_prediction_diagnostic
evidence_domain: controlled_experiment
scientific_verdict: negative_for_fixed_published_label_history_increment
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

Code review: independent local Codex REVIEW_PASS at exact c71ea39; see code_review.md. Run S02-E005-R001 succeeded on Taobo CPU, exit0, retrieval verified. Evidence review: independent Codex REVIEW_PASS; see evidence_review.md.

## Dated S02 claim impact — 2026-10-13

Frozen v1 produced a bounded negative: equal-record MAE M0=0.081686 mm versus M1=0.109182 mm, difference+0.027496 mm; M1 worse in both records and secant best in both. Source publication labels only. This closes the four-fit exploration without additional arms or tuning. It does not close the observation-history storyline, qualify physical error, or alter earlier FATACRACK/Mendeley data gaps. Required numerical evidence, independent review and full-tail decision figure are present. Next meaningful change requires a separately frozen representation or new qualified observation axis; current evaluated tails must not be retuned to rescue this result.

## Dated S02 claim impact — 2026-10-17, FF localisation

R003/A002 is a post-result frozen-prediction label-sensitivity diagnostic, independently reviewed. Top5 FF origins111000/104000/105000/102000/97001 account for58.84% of two-phase gross lowering; hole-projection contribution63.51%/22.28% is phase-dependent; low-past11/33 contributes8.02%/22.97%, not enriched. All33 retained; no fitting, training, model forward or old-result change. R001 negative remains; R002 numerical paths reproduced. No physical hole/noise cause or road claim. See S02-E005-R003.md and ff_locality_evidence_review.md; next need author timing/processing and repeatability evidence.
