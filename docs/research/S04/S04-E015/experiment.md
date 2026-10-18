---
storyline_id: S04
experiment_id: S04-E015
protocol_revision: v1
status: completed
started_at: 2026-10-08
closed_at: 2026-10-08
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# M2 raw-driver coefficient-prediction feasibility

## Scientific question

For the support-masked rank-20 raw-driver residual representation selected only
as an E014 diagnostic, can a fixed closed-form ridge map same-cycle PINN-only
features to correction coefficients that reduce residual RMSE on a completely
held-out Umax trajectory by the frozen practical margin?

## Claim contract

- Claim tier / tag: `T2 synthetic science / exploratory residual prediction`.
- Estimand: predicted (not oracle-fitted) raw-log10 correction on each held-out
  cycle's FEM-p99 active support, C1 through FEM own-first-event inclusive.
- Holdout unit: one complete Umax trajectory. Basis, target coefficients,
  feature statistics, target scaling, ridge weights, and alpha selection use
  only the other two Umax trajectories.
- Comparator: zero correction. E014 M2 oracle coefficients are a non-voting
  ceiling diagnostic.
- If pass: authorise a separately gated Taobo pointwise/MLP coefficient-model
  comparison using the same inputs and holdout firewall.
- If fail: do not escalate architecture using only these three trajectories;
  first add an independent Umax trajectory or revise observable inputs.
- Because M2 was chosen after viewing E014, this is exploratory feasibility,
  not independent confirmation.

## Frozen representation and targets

- For each outer fold, fit the E014 `M2_support_pod` rank-20 mean/basis using
  only the two training Umax trajectories. Training raw residuals are zeroed
  outside their own FEM-p99 active support.
- For each training cycle, the 20 coefficient targets are the minimum-norm
  area-weighted least-squares coefficients on that training cycle's FEM-p99
  support.
- At held-out inference, no FEM residual, FEM support, FEM event time, or oracle
  coefficient is an input. The predicted coefficients reconstruct a full-grid
  correction; held-out FEM support is used only for scoring.
- The evaluation window ends at the held-out FEM own-first-event, so this is a
  retrospective bounded evaluation window, not prospective event forecasting.

## Frozen PINN-only features

All features are from the current same-cycle PIDL export plus declared loading:

1. `Umax`, `cycle/100`, and `log1p(cycle)`;
2. area-weighted mean, standard deviation, q90, and q99 for each of PIDL damage,
   history, raw-log10 driver, and active-log10 driver (16 scalars);
3. for each of those four fields, 20 area-weighted projections onto the outer-
   training M2 spatial basis after subtracting that field's outer-training mean
   (80 scalars).

Total: 99 features. Log floor is `1e-12`. Feature and coefficient standardizers
are fitted on training rows only.

## Frozen ridge selection

- Alpha grid: `[1e-6, 1e-4, 1e-2, 1, 1e2, 1e4]`.
- Within each outer fold, use the two directional whole-Umax validations:
  train on training-Umax A / validate on B and train on B / validate on A.
- The M2 basis is fixed from both outer-training Umax trajectories; all ridge
  standardization and weights in each directional validation use only its fit
  Umax. Select the alpha with lowest mean standardized coefficient MSE; ties go
  to the smaller alpha. Refit once on both outer-training Umax trajectories.
- This inner procedure tunes the coefficient map only. The complete outer Umax
  remains untouched until final scoring.

## Frozen decision contract

- Evidence identity: `input_lock.json` locks the E013 data lock and E014 decision
  and arm summary.
- Necessary validity gates:
  1. reused trajectory identity/semantics/grid validation passes;
  2. outer-fold M2 oracle rank-20 medians and bootstrap endpoints reproduce the
     E014 table within absolute `1e-10`;
  3. all feature/target matrices and predicted coefficients are finite, every
     design has the declared 99 features, and held-out prediction does not call
     the held-out residual/support coefficient solver.
- Primary criterion: in all three complete-Umax folds, the 97.5th-percentile
  endpoint of the deterministic non-circular moving-block bootstrap distribution
  of median per-cycle **predicted** error ratio is `<0.90`. Block length 5,
  2,000 replicates, seeds `20261150 + fold_index`.
- Threshold rationale: same practical 10% margin as E013/E014, now applied to
  genuinely predicted coefficients rather than oracle coefficients.
- Missing rule: an identified failing fold makes the bounded verdict negative;
  otherwise any unidentified fold makes it inconclusive.
- Non-voting diagnostics: oracle M2 ceiling, coefficient mean predictor, alpha,
  coefficient correlation, C1-20/C21-40/middle/late/event bins, and correction
  magnitude.
- Stop rule: one frozen ridge analysis only. Do not add features, alphas, nonlinear
  models, or a neural network after viewing R001.

```text
validity fails                              -> inadmissible
all three predicted-coefficient folds pass  -> supports separate neural comparison
any identified fold fails                   -> negative for current inputs/ridge
no identified fail + unidentified            -> inconclusive
```

## Producer and evidence

- Producer: Mac local closed-form light analysis; no iterative PIDL/neural
  training loop.
- Runner: `SENS_tensile/analyze_m2_coefficient_predictability.py`.
- Output: `local_archive/experiments/S04-E015/runs/S04-E015-R001/analysis/`.
- Minimum evidence: input validation, E014 oracle reproduction, alpha-selection
  table, predicted per-cycle metrics, primary/phase summaries, coefficient
  diagnostics, one figure with README, decision, and Run receipt.

## Code review

Independent verdict: `PASS — Code Ready`, bound to:

- protocol SHA-256 `eeb0f327175634fcd38419ab2eef15102bb1fbb7bad3b07fa7a225a83467c49c`;
- input-lock SHA-256 `dc98db4f50079494f9e836a8a356194b16da3a859a5f3993b4b408d5abd354d8`;
- runner SHA-256 `f4b52ecadbcb0dc4d8a2038cfa106f6067158f9bb8645b3a6f760a5d5973a4b7`;
- tests SHA-256 `e047d914ff30bdbf236fcf270cb550900f03d7df9c13288b94813d33d71510c6`.

The reviewer independently checked PINN-only feature isolation, complete-Umax
holdout, diagnostic-only oracle use, M2 reproduction, ridge standardization,
bootstrap/status logic, and a synthetic held-out mutation test. Deterministic
checks: 22 passed with warnings treated as errors.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S04-E015-R001 | M2 coefficient ridge feasibility | succeeded | verified | `RUN_RECEIPT.md` |

## Scientific verdict

**Negative for the current 99 PINN-only features and frozen ridge map.** All
three complete-Umax folds fail the `<0.90` bootstrap-upper criterion:

- Umax=0.11: median `0.9582`, upper `0.9874`;
- Umax=0.12: median `1.1115`, upper `1.1374`;
- Umax=0.13: median `0.8911`, upper `0.9519`.

E014 M2 oracle results reproduce exactly, so the failure is coefficient
predictability rather than loss of the representation ceiling. All folds select
`alpha=10000`; predicted/oracle coefficient correlations are approximately
`-0.050`, `0.016`, and `0.042`. Do not escalate to MLP/graph architecture using
only these three trajectories. The next admissible evidence axis is an
independent Umax trajectory or a genuinely new same-cycle observable.

Independent result review: `PASS — Evidence Ready`; 14 input hashes, 264 cycle
rows, 54 inner-selection rows, primary and oracle bootstraps, prediction-path
isolation, and the figure/receipt package were verified. The bounded conclusion
is only that the frozen ridge map failed the transfer criterion; low coefficient
correlation does not independently prove that the feature set contains no
useful nonlinear information.
