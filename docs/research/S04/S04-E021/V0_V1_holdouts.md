# How to read `V0_V1_holdouts.png`

## How to read

This figure asks whether the selected physical-raw correction V1 reduces error
relative to the admissible uncorrected V0 on each complete development Umax
holdout. It was generated once by `S04-E021-R001` from the frozen
`folds.csv`/`decision.json` outputs. It contains no confirmation trajectory and
is not a road-data or physical-validation figure.

## Data provenance

Run `S04-E021-R001`; runtime commit `6aa21e3`; frozen sources
`folds.csv` and `decision.json`. The PNG is copied byte-for-byte into the
separate documentation-validation directory; it is not rerendered.

Image:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001/V0_V1_holdouts.png`

## Panels

- **Left — all-cycle balanced R:** `R=sqrt(E(V1)/E(V0))`, where each of the
  three cycle strata contributes equally. Values below the dashed V0=1 line
  mean lower physical-raw RMSE for V1. The worst holdout is U0.11 at
  `R=0.967385`, so the preregistered worst-case quantity is `Q=0.967385`.
- **Right — C1–20 G:** early-cycle RMSE ratio, again V1/V0. All four values are
  below one, so the fatal early-regression condition is not triggered.

No point is marked as fallback: all four outer folds selected a learned
correction using inner-development rules before their outer scores were read.

## Interpretation and limitation

The plotted direction is consistent across the four already viewed development
trajectories. The worst reduction is modest (about 3.26% in RMSE); no practical
margin or uncertainty interval has been qualified. The figure does not prove
fresh-amplitude generalisation, teacher correctness, physical mechanism,
forecast skill or permission to train a PIDL/NN model.

Independent review caveat2026-10-15:U0.11 C41+ stratum RMSE rises about1.61%.
This two-panel figure shows balanced-total and early ratios, not a guarantee
that every stratum/cycle improves. The frozen primary verdict is unchanged.

Visual QA: both panels are nonblank; axes, case labels, legends and the V0=1
reference are readable; plotted values and direction match `folds.csv`.
