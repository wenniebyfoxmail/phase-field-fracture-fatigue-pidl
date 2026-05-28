# FEM/PIDL Cyclewise Baseline Comparison

Date: 2026-05-28

## Inputs

FEM cyclewise handoff:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28
```

Files used:

- `reverseBC_u12_cyclewise_mechanism_metrics.csv`
- `reverseBC_u12_cyclewise_element_fields_c1_c74.mat`
- `README_reverseBC_u12_cyclewise_mechanism.md`

PIDL baseline archive:

```text
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12
```

Generated comparison outputs:

```text
_analysis_fem_mechanism_20260528/baseline_pidl_cyclewise_scalar_diagnostics/element_diagnostics_summary.csv
_analysis_fem_mechanism_20260528/baseline_fem_pidl_cyclewise_mechanism_comparison.csv
_analysis_fem_mechanism_20260528/figures/baseline_fem_pidl_cyclewise_mechanism_comparison.png
```

## Definition Notes

The FEM README defines:

- `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`, and `psi_plus_elem` as element
  means over Gauss/history data.
- `alpha_bar_monitor_max` as a solver/internal monitor quantity, not the same
  reduction as `alpha_bar_elem_max`.
- Crack tip as maximum element-centroid `x` where `d_elem >= threshold`.
- Right-boundary fracture diagnostic as elements near the right boundary with
  `d_elem >= 0.95`.

The PIDL cyclewise scalar diagnostics were recomputed post-hoc from saved
network/checkpoint states using the same mesh as the baseline archive. The
cycle label is the saved PIDL checkpoint index; c40 in this table is the same
state used by `trained_1NN_40.pt` and `checkpoint_step_40.pt`.

## Main Cyclewise Findings

The c40/c70 interpretation holds over the full available FEM window c1-c74.
The mismatch is not only an endpoint accident.

Selected values:

| Cycle | FEM `E_el` | PIDL `E_el` | FEM `E_d` | PIDL `E_d` | FEM hist max | PIDL hist max | FEM `f_min` | PIDL `f_min` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.004640 | 0.004647 | 0.000371 | 0.005463 | 29.566 | 2.655 | 3.06e-3 | 1.00e-1 |
| 40 | 0.003174 | 0.003386 | 0.002160 | 0.006018 | 103.071 | 7.202 | 2.96e-4 | 1.69e-2 |
| 70 | 0.001162 | 0.001505 | 0.004719 | 0.007176 | 215.476 | 8.690 | 2.62e-4 | 1.18e-2 |
| 74 | 0.000070 | 0.001235 | 0.005446 | 0.007361 | 227.955 | 8.830 | 2.60e-4 | 1.15e-2 |

Median PIDL/FEM ratios over c10-c74:

| Ratio | Median |
|---|---:|
| `E_el` | 1.07 |
| `E_d` | 2.64 |
| history max | 0.067 |
| history mean | 0.555 |
| `f_min` | 51.79 |

Interpretation:

- PIDL elastic energy is close for most of the trajectory, until FEM fractures
  near c74.
- PIDL fracture/damage energy is too high throughout the trajectory.
- PIDL global/domain-mean history is only moderately low, but its local history
  peak is much too weak.
- Because PIDL local history is too weak, its minimum degradation `f` remains
  tens of times larger than FEM. This is the strongest evidence that the local
  fatigue-driving mechanism is under-concentrated in PIDL.
- PIDL crack-tip position lags FEM increasingly near the FEM fracture event:
  about `-0.025` at c40, `-0.045` at c70, and `-0.087` at c74. This is a real
  gap, but it appears downstream of the local history/degradation gap.

## Kt Caveat

The FEM `Kt_proxy` grows from about 12 at c1 to about 6771 at c74. PIDL `Kt`
grows from about 7.6 at c1 to about 18.9 at c74. The order-of-magnitude gap is
consistent with missing local stress/energy concentration, but the exact ratio
is definition-sensitive because the two proxy implementations were produced by
different post-processing paths.

Use `Kt` as a mechanism alarm, not yet as a calibrated scalar target.

## Consequence For Next Experiments

The next experiment should not only try to reach the right boundary at the
right cycle. It should test whether the local head/mesh/refinement changes:

- local history peak growth,
- minimum fatigue degradation,
- `E_d` level,
- crack-tip lag,
- and FEM/PIDL residual fields on the same selected cycles.

For the current baseline, the likely chain is:

```text
weak local psi/history concentration
  -> weak local f degradation
  -> damage spreads/dissipates through too much E_d
  -> tip motion and Kt proxy lag FEM near fracture
```

The all-cycle FEM export now gives a better gate for reruns: compare the whole
trajectory first, then inspect residual fields at c10, c40, c70, and the
method-specific near-fracture cycle.
