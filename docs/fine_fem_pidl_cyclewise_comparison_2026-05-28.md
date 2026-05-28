# Fine-Mesh FEM vs Baseline PIDL Cyclewise Comparison

Date: 2026-05-28

## Inputs

Fine FEM reverseBC u=0.12 handoff:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_fine_reverseBC_u12_cyclewise_mechanism_2026-05-28
```

Files used:

- `fine_reverseBC_u12_cyclewise_mechanism_metrics.csv`
- `fine_reverseBC_u12_cyclewise_element_fields_c1_c69.mat`
- `mesh_geometry.mat`
- `README_fine_reverseBC_u12_cyclewise_mechanism.md`

Baseline PIDL archive:

```text
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12
```

Generated outputs:

```text
_analysis_fem_mechanism_20260528/fine_fem_baseline_pidl_cyclewise_mechanism_comparison.csv
_analysis_fem_mechanism_20260528/figures/fine_fem_baseline_pidl_cyclewise_mechanism_comparison.png
_analysis_fem_mechanism_20260528/figures/fine_fem_baseline_pidl_cyclewise_mechanism_comparison.pdf
```

## FEM Payload Notes

The fine FEM payload has 69 cycles (`c1-c69`) and the same 43 scalar metric
columns as the earlier cyclewise FEM export. The README defines `d_elem`,
`alpha_bar_elem`, `f_fatigue_elem`, and `psi_plus_elem` as element means over
Gauss/history data. `alpha_bar_monitor_max` is still a separate solver/internal
monitor quantity and must not be compared directly to the element-field max.

The mesh payload reports 10401 nodes and 10261 Q4 elements. Treat this as a
separate FEM reference, not as a simple relabelling of the previous 77730-field
handoff.

## Selected Values

| Cycle | FEM `E_el` | PIDL `E_el` | FEM `E_d` | PIDL `E_d` | FEM hist max | PIDL hist max | FEM `f_min` | PIDL `f_min` | FEM `x_tip_d095` | PIDL `x_tip` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.004862 | 0.004808 | 2.27e-7 | 0.005471 | 0.609 | 0.737 | 7.81e-1 | 6.54e-1 | NaN | 0.000 |
| 10 | 0.004680 | 0.004647 | 0.000310 | 0.005463 | 8.813 | 2.655 | 2.04e-2 | 1.00e-1 | 0.013 | 0.0196 |
| 40 | 0.003121 | 0.003386 | 0.002304 | 0.006018 | 80.830 | 7.202 | 5.54e-4 | 1.69e-2 | 0.1917 | 0.1595 |
| 69 | 0.000059 | 0.001574 | 0.005589 | 0.007130 | 126.288 | 8.660 | 1.65e-4 | 1.19e-2 | 0.4990 | 0.3730 |

Median PIDL/FEM ratios over `c10-c69`:

| Ratio | Median |
|---|---:|
| `E_el` | 1.082 |
| incremental `E_d` from c1 | 0.236 |
| history max | 0.092 |
| history mean | 0.615 |
| `f_min` | 30.43 |
| `Kt` proxy | 0.011 |

## Interpretation

The fine FEM export changes the exact timing and amplitudes, but not the main
mechanism diagnosis. FEM reaches the right boundary by c69, while baseline PIDL
still has a large tip-position lag and a much weaker local concentration.

The important repeat finding is:

```text
PIDL local history peak remains too small
  -> PIDL local f degradation remains too weak
  -> PIDL incremental damage/fracture energy remains too low
  -> PIDL crack-tip advance and Kt proxy lag FEM near fracture
```

Compared with the previous FEM export, the fine run has lower early/mid-cycle
history and `psi_plus` peaks, but PIDL is still below the FEM local peak by
roughly an order of magnitude over the useful comparison window. This makes the
gap less extreme than the previous FEM comparison, but still mechanism-level,
not just a final-cycle criterion mismatch.

## How To Use This Next

Use the fine FEM payload as a second FEM reference for any new PIDL variant.
For each PIDL rerun, report both comparisons:

- previous reverseBC cyclewise FEM (`c1-c74`),
- fine reverseBC FEM (`c1-c69`).

The pass/fail gate should prioritise:

- outside-precrack incremental `E_d`,
- local history max and mean,
- minimum `f_fatigue`,
- `x_tip` lag,
- residual fields at c10, c40, and near the FEM fracture cycle.

Do not use `alpha_bar_monitor_max` as the main field-level maximum; keep using
`alpha_bar_elem_max` for fair field reductions.
