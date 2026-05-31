# M2S Framework Validation

Date: 2026-05-31

## Purpose

Validate the paper framework at the smallest controlled level: measurement to
state/prognosis on a synthetic FEM truth trajectory.

This is not a field deployment claim.  FEM is treated as the hidden truth, and
the question is whether different observation levels contain enough information
to predict remaining fatigue life without using cycle index as a feature.

## Data

FEM truth:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
/mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
combined handoff:
/mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat
N_f = 69
cycles = 1...69
elements = 45000
```

Runner:

```text
SENS_tensile/run_m2s_synthetic_validation.py
```

Remote output:

```text
/mnt/data2/drtao/projects/pidl-femmesh-inverse-alphaT-215c3bd/SENS_tensile/run_logs/m2s_framework_validation_softHist0_20260531/
  m2s_validation_cycle_features.csv
  m2s_validation_summary.csv
  m2s_validation_summary.md
```

## Inputs And Outputs

Observation/input sets:

| set | content | interpretation |
|---|---|---|
| `figure_damage` | crack-tip proxy, damaged area, right-boundary damage, crack-strip damage, damage max/p99 | figure/image-like geometric observation |
| `damage_field` | richer reductions of the full FEM damage field | field observation, but no hidden energetic/history variables |
| `state_driver_raw_active` | damage plus `alpha_bar`, fatigue factor, raw `psi`, and active degraded `g(d) * psi` | hidden state-driver observation with raw/active split |

Prediction/output:

```text
remaining life = N_f - cycle
```

Cycle index is deliberately excluded from the input features, otherwise the
task would collapse into reading the clock.

## Method

For each cycle, the script builds area-weighted reductions over the domain,
crack strip, right-boundary band, and tip-local zones.  It then runs leave-one-
cycle-out prediction with:

```text
ridge regression over alpha grid = [0.01, 0.1, 1, 10, 100]
nearest-neighbor diagnostic in standardized feature space
```

The raw/active guardrail is explicit:

```text
psi_raw = FEM psi_elem / psi_plus_elem
psi_active = ((1 - d)^2 + 1e-6) * psi_raw
```

This is important because the inverse `alpha_T` retry showed that raw `psi` can
look large while the degraded active driver is still too small.

## Result

| feature set | n features | best alpha | ridge LOOCV MAE | ridge RMSE | ridge R2 | NN MAE | max abs error |
|---|---:|---:|---:|---:|---:|---:|---:|
| `figure_damage` | 8 | 0.1 | 0.333 cycles | 0.711 | 0.999 | 1.26 | 3.01 |
| `damage_field` | 20 | 0.01 | 0.214 cycles | 0.537 | 0.999 | 1.45 | 3.89 |
| `state_driver_raw_active` | 85 | 1.0 | 1.40 cycles | 10.65 | 0.714 | 1.30 | 88.47 |

Selected cycle-level sanity checks:

| cycle | RUL | crack-tip proxy | `psi_raw` tip2 | `psi_active` tip2 | figure pred | state-driver pred |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 68 | 0.000 | 2.685 | 0.0545 | 64.95 | 67.05 |
| 10 | 59 | 0.019 | 6.094 | 0.0563 | 58.52 | 58.99 |
| 30 | 39 | 0.125 | 7.160 | 0.0554 | 39.01 | 38.98 |
| 50 | 19 | 0.277 | 6.705 | 0.0556 | 18.50 | 19.10 |
| 69 | 0 | 0.499 | 143.392 | 0.0040 | -0.46 | -88.47 |

## Interpretation

The framework is feasible at the synthetic single-trajectory level: an M2S
pipeline can map observations to a useful state/prognosis variable when FEM
provides controlled truth.

The important caveat is that this benchmark is too easy.  On one monotonic FEM
trajectory, crack geometry and damage level almost directly order the remaining
life.  Therefore the result supports the framework's first validation rung, but
it does not yet prove that hidden energetic/history fields add independent
prognostic value over image-level damage.

The state-driver set is not better here because it is high-dimensional and
strongly collinear on a single trajectory; the late-cycle raw `psi` spike also
creates an extrapolation failure at cycle 69.  This should not be read as
"state fields are useless"; it says the next validation must include multiple
trajectories so that damage geometry alone no longer uniquely identifies life.

## What This Gives The Paper

Safe claim:

```text
The proposed M2S layer can be validated first on synthetic FEM trajectories:
from progressively richer observations, it predicts FEM remaining life and
exposes whether image-level damage, field-level damage, or hidden energetic
drivers carry the prognostic signal.
```

Do not yet claim:

```text
Hidden state-driver fields outperform image-level crack observations.
The inverse problem is materially identifiable.
The framework is validated on real pavement sensing data.
```

## Next Validation Rung

Build a multi-trajectory FEM benchmark with at least:

```text
different Umax values
different alpha_T / fatigue degradation settings
possibly different initial notch/precrack severity
```

Then test cross-trajectory splits:

```text
train on several trajectories, hold out one trajectory
```

That is the first setting where the framework can test whether hidden
state-driver information adds value beyond visible damage progression.
