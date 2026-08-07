# Experiment Record: LTPP 06-1253 Observation-State Gate v1

**Experiment ID:** `ltpp_06_1253_observation_state_gate_v1_20260805`  
**Date:** 2026-08-05  
**Status:** completed, rejected for promotion  
**Decision:** `FAIL_L_NOT_QUALIFIED`  
**Evidence class:** negative state-semantics / trajectory-sufficiency diagnostic

## Purpose

Determine whether an irreversible latent crack state with an explicit noisy survey-observation layer predicts the next complete `line_damage` field more reliably than:

- persistence of the last observation;
- a smooth but nonmonotone local-trend model.

This experiment tests the observation-state representation only. It does not select PDE terms or train PIDL.

## Why this experiment was run

The preceding `06-1253` diagnostics showed that both the hand-vectorized pilot observations and official section-level distress metrics can decrease between surveys. Therefore, raw map geometry cannot be imposed directly as an irreversible phase-field damage state. This gate tested whether irreversibility could instead be assigned to a latent state while survey observations remain noisy and nonmonotone.

## Frozen input

- Input: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_single_annotator_fields_v1_20260805/frozen_observation_fields.npz`
- Channel: `line_damage` only.
- Shape used: seven surveys by 126 by 382 pixels.
- Dates used: the first seven authorized primary surveys, 1991-2007.
- Excluded: area and combined channels, 2012/2015 auxiliary surveys, climate, traffic, moisture, FWD, MON_DIS, and maintenance metadata.
- Annotation status: single primary annotator; not physical ground truth.

## Predeclared comparison

Four full-field rolling-origin folds were used:

| Fold | Training surveys | Forecast survey |
|---|---|---|
| F1 | 1-3 | 4 |
| F2 | 1-4 | 5 |
| F3 | 1-5 | 6 |
| F4 | 1-6 | 7 |

Models:

- `P`: last-observation persistence.
- `S`: nonmonotone local trend with training-only shrinkage.
- `L`: PAVA irreversible latent history, nonnegative drift, and shared noisy observation layer.

The complete forecast-date field was hidden. No random pixel split was used. Spatial uncertainty was evaluated with fixed contiguous `6 x 10` macrotiles rather than treating pixels as independent samples.

## Primary promotion requirements

L had to pass every predeclared condition, including:

- at least 10% median balanced-MAE improvement against P and S;
- at least three wins in four folds against each baseline;
- no fold more than 5% worse than the best baseline;
- at least 5% median balanced-CRPS improvement against both baselines;
- positive 90% cluster-bootstrap lower bounds for CRPS improvement;
- protected soft Dice, interval coverage, interval width, finite metrics, informative folds, and nondegeneracy.

Any failed condition required `FAIL_L_NOT_QUALIFIED`; thresholds could not be relaxed after execution.

## Results

| Quantity | Result | Gate interpretation |
|---|---:|---|
| Median bMAE, P | 0.24270 | baseline |
| Median bMAE, S | 0.25434 | baseline |
| Median bMAE, L | 0.22432 | best absolute value |
| L bMAE improvement vs P | 7.57% | **fail**, below 10% |
| L bMAE improvement vs S | 11.80% | pass |
| L bMAE wins vs P | 3/4 | pass |
| L bMAE wins vs S | 4/4 | pass |
| L bCRPS improvement vs P | 8.21% | pass |
| L bCRPS improvement vs S | 13.86% | pass |
| CRPS bootstrap q05 vs P | 4.22% | pass |
| CRPS bootstrap q05 vs S | 7.87% | pass |
| Worst bMAE regression vs best baseline | 0.085% | pass |
| F4 L interval coverage | 68.90% | **fail**, below 70% |

All four folds were informative. Soft Dice, interval width, finite-metric, bootstrap, worst-regression, and nondegeneracy gates passed.

Inner selection chose latent drift factor `0.0` in all four folds. Therefore, the observed advantage came from preserving a denoised irreversible history, not from forecasting positive crack growth.

## Decision and interpretation

The model is not promoted as the next field adapter. The result supports one narrower observation:

> Separating a persistent latent history from noisy survey geometry is useful, but this single-section implementation does not provide a qualified predictive crack-growth state.

Do not relax the v1 thresholds and do not tune another `06-1253`-only variant. The next evidence-bearing test is cross-section reproduction within the separate multisection route.

## Forbidden claims

This experiment does not establish:

- that the inferred latent state is true physical damage;
- that a crack-growth mechanism has been learned;
- that any PDE, climate, traffic, or moisture term is valid;
- that L outperforms PIDL, joint training, or Freeze-Then-Select;
- that the result generalizes to other road sections;
- that the manual annotation is ground truth.

Failure also does not refute physical crack irreversibility. It rejects this model as the next adapter for this frozen pilot.

## Artifacts

- Contract: `docs/ltpp_06_1253_observation_state_gate_v1_contract_20260805.md`
- External review: `docs/reviews/ltpp_06_1253_observation_state_gate_external_review_20260805.md`
- Runner: `SENS_tensile/run_ltpp_06_1253_observation_state_gate_v1.py`
- Decision: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/decision.md`
- Fold metrics: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/fold_metrics.csv`
- Full result: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/result.json`
- Audited attempt: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_observation_state_gate_v1_20260805/_attempt_ledger/attempt.md`
- Workstream summary: `docs/workstreams/ltpp_06_1253_single_annotator_fts_progress_20260805.md`

## Next update rule

This file is the detailed record for experiment v1 and remains immutable except for provenance corrections. A new model or cross-section run must receive a new experiment ID and a separate MD file. Only its one-line purpose, decision, and next discriminator should be reflected in `docs/research_frontier.md`.

## Visual evidence checkpoint

The project-level checkpoint combines the completed `06-1253` rolling-origin evidence with the qualified six-section inventory and the still-pending dual-blind annotation gate:

- PNG: `docs/figures/ltpp_freeze_select_progress_20260805.png`
- PDF: `docs/figures/ltpp_freeze_select_progress_20260805.pdf`
- Reproduction script: `scripts/plot_ltpp_research_progress_20260805.py`

The figure must be read as a progress boundary, not as a cross-section forecast result. The 37 qualified states have passed source/geometry/climate checks but do not yet constitute a reviewed multisection label benchmark.
