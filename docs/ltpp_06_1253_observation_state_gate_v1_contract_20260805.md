# LTPP 06-1253 Observation-State Gate v1 Contract

**Frozen before execution:** 2026-08-05  
**Claim class:** state-semantics / trajectory-sufficiency diagnostic  
**Input:** frozen `line_damage` only  
**Decision:** `PASS_L_AS_NEXT_FIELD_ADAPTER` or `FAIL_L_NOT_QUALIFIED`

## PIDL Experiment Gate

- Mechanism question: Does an irreversible latent state plus noisy survey observation predict the next full line-distress field more reliably than persistence and a nonmonotone local-trend model?
- Claim changed if success: The latent observation-state representation may advance to multisection field-adapter qualification.
- Claim changed if failure: Do not use hard latent irreversibility as the next adapter for this dataset; keep the total Freeze-Then-Select goal blocked at field representation.
- Cheaper diagnostic first: This is the cheapest offline diagnostic against already frozen fields; no PIDL/FEM training is launched.
- Minimal output asset: `decision.md`, `result.json`, and `fold_metrics.csv`.
- Code/producer alignment: deterministic Mac post-hoc analysis only; no producer machine or GPU required.
- Success criteria: every gate in `Qualification rule` passes without post-result changes.
- Failure criteria: any gate fails, any fold is invalid, or a degeneracy guard triggers.
- Registry destination: `docs/workstreams/ltpp_06_1253_single_annotator_fts_progress_20260805.md`.
- Decision: launch offline diagnostic.

## Frozen data and splits

Input file:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fields_v1_20260805/frozen_observation_fields.npz`

Use only indices 0-6 of `line_damage`. Indices 7-8, `area_damage`, `combined_damage`, MON_DIS, climate, traffic, moisture, FWD, and maintenance metadata are excluded from fitting and scoring.

Four rolling-origin folds use real elapsed years:

| Fold | Training surveys | Forecast survey |
|---|---|---|
| F1 | 1-3 | 4 |
| F2 | 1-4 | 5 |
| F3 | 1-5 | 6 |
| F4 | 1-6 | 7 |

The complete held-out spatial field is hidden. There is no random pixel split.

## Models

### P: persistence

The forecast mean is the most recent observed field.

### S: smooth nonmonotone local trend

The forecast is the most recent observation plus its last annualized temporal difference multiplied by elapsed forecast time. A shrinkage factor in `{0.25, 0.5, 1.0}` is selected only by inner rolling-origin forecasts within the outer training period. Values are clipped to `[0, 1]`. The model may rise or fall.

### L: irreversible latent state with noisy observations

For each pixel, PAVA estimates a nondecreasing latent sequence from the outer training surveys. Survey-level residual bias is estimated iteratively and constrained to have zero temporal mean. The next latent state is the last state plus a nonnegative annualized mean latent increment. A drift factor in `{0.0, 0.5, 1.0}` is selected only by inner rolling-origin forecasts. Values are clipped to `[0, 1]`.

The held-out survey bias has expectation zero and is never estimated from the held-out field.

## Shared observation uncertainty

All three models use the same fold-specific predictive noise distribution:

- Student-t with 4 degrees of freedom for pixel observation residuals;
- zero-mean Gaussian survey-bias component;
- scales estimated only from temporal changes in the outer training fields;
- deterministic Monte Carlo samples with a frozen seed;
- scale floors prevent zero-width intervals.

This shared layer prevents L from winning by receiving a more flexible uncertainty model.

## Metrics

Foreground is fixed as held-out `line_damage >= 0.1`. The primary score is:

`balanced MAE = 0.5 * foreground MAE + 0.5 * background MAE`.

Safeguards are balanced CRPS, soft Dice, empirical 80% prediction-interval coverage, and mean interval width. Spatial uncertainty uses fixed contiguous `6 x 10` macrotiles and 2,000 deterministic cluster-bootstrap replicates.

A fold is informative when foreground occupies at least 0.1% of pixels and mean absolute change from the previous survey exceeds `1e-4`.

## Qualification rule

L passes only if all conditions hold:

1. Median balanced-MAE improvement is at least 10% against P and against S.
2. L beats each baseline in at least three of four folds on balanced MAE.
3. In no fold is L more than 5% worse than the best baseline on balanced MAE.
4. Median balanced-CRPS improvement is at least 5% against P and against S.
5. The 90% cluster-bootstrap lower bound for balanced-CRPS improvement is above zero against both baselines.
6. In every fold, L soft Dice is no more than 0.02 below the best baseline.
7. In every fold, L 80% interval coverage lies in `[0.70, 0.90]`.
8. In every fold, L interval width is at most 1.5 times S interval width.
9. All four folds are finite and at least three are informative.
10. L does not degenerate to all-zero, all-one, or exact persistence forecasts in every fold.

Any failed condition returns `FAIL_L_NOT_QUALIFIED`. Thresholds and models cannot be changed after execution under v1.

## Evidence boundary

Even a pass means only that L deserves multisection field-adapter testing for one-step forecasting of this frozen single-annotator line proxy. It does not establish physical damage truth, PDE terms, climate causality, superiority to PIDL/joint training/Freeze-Then-Select, cross-road generalization, or annotation ground truth.

A failure does not refute physical crack irreversibility. It rejects only this observation-state implementation for this frozen pilot.

External review and local disposition:

`docs/reviews/ltpp_06_1253_observation_state_gate_external_review_20260805.md`

