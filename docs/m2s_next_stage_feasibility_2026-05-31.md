# M2S Next-Stage Feasibility Package

Date: 2026-05-31

## Purpose

Move the FYR M2S validation beyond the single-trajectory FEM truth check.  The
single soft-hist0 trajectory was useful but too easy, because visible damage
almost directly ordered remaining life.  This package tests leave-one-trajectory
holdout splits and sparse/noisy observation quality.

## Data

- Strict full-field soft-hist0/reverseBC cadence handoffs: `n_step=2/3/10`,
  fixed `Umax=0.12`, cycle-wise element fields.
- Legacy five-Umax FEM scalar reductions: `Umax=0.08...0.12`, cycle-wise scalar
  reductions from `~/Downloads/_pidl_handoff_v2/post_process`.
- Total holdout table: 1228 rows across 8 trajectories.

## Method

Ridge regression is trained on complete trajectories and evaluated on a held-out
trajectory.  Cycle index is excluded from the input features.  Feature tiers are
`figure_damage`, `damage_field`, and `state_driver_raw_active`.

Sparse/noisy observation tests use the strict full-field subset, because those
handoffs contain cycle-wise damage fields.  Virtual sensors sample damage near
the crack path, off the crack path, or in a mixed layout; Gaussian noise and
missing observations are then added.

## Key Results

| suite | figure damage RUL MAE | damage field RUL MAE | state-driver RUL MAE |
|---|---:|---:|---:|
| combined all | 70.78 | 69.43 | 29.03 |
| legacy five-Umax scalar | 85.74 | 82.32 | 34.77 |
| strict soft-hist0 cadence field | 0.76 | 1.23 | 0.76 |

On the useful cross-Umax stress test, visible-damage-only features generalise
poorly, while state-driver proxies improve RUL prediction substantially
(`R2≈0.82`).  On the strict cadence subset, all tiers are near-trivial because
the trajectories are too similar; this should not be used as proof of hidden
field superiority.

Sparse mixed damage sensors on the strict field subset degrade from `MAE≈11.88`
cycles with 4 clean sensors to `MAE≈1.55` cycles with 64 clean sensors.  With
64 sensors and 0.10 damage noise, MAE remains about `2.88` cycles.

## Limitations

- The five-Umax holdout uses older scalar reductions, not the newer strict
  full-field soft-hist0 family.
- The strict full-field subset varies cadence only, at fixed `Umax=0.12`.
- Sparse sensors are virtual FEM samples, not real pavement measurements.
- Do not claim real deployment validation or hidden-state superiority beyond
  what the holdout rows show.

## Safe FYR Claim

A multi-trajectory FEM holdout benchmark provides the minimum next validation
rung for M2S, because it tests whether the framework generalises beyond a single
monotonic damage path and whether sparse observations still contain enough
information for useful state/prognosis inference.

## Artifacts

Local output directory:

```text
_analysis_m2s_next_stage_20260531/
```

Main files:

```text
m2s_multitrajectory_holdout_summary.csv
m2s_sparse_noisy_observation_summary.csv
m2s_holdout_rul_true_vs_pred.png
m2s_observation_quality_mae.png
m2s_next_stage_feasibility_report.md
```

Runner:

```text
SENS_tensile/run_m2s_next_stage_feasibility.py
```
