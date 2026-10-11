# History Driver Definition Audit

This audit compares candidate fatigue-history drivers on the latest aligned FEM/PIDL mapped states:

- `raw`: undegraded tensile energy, FEM `psi_plus_elem`, PIDL `psi_raw_elem`.
- `active_g`: stiffness-degraded tensile energy, FEM `g_psi_plus_elem`, PIDL `psi_active_elem`.
- `fatigue_active`: `f * g * psi_plus`, FEM `f_g_psi_plus_elem`, PIDL `f_fatigue_elem * psi_active_elem`.

The archived strict PIDL state-timing run used `history_driver_mode: active_degraded`, i.e. `active_g`.
The FEM export stores all three candidates, but the GRIPHFiTH history update is driven inside the phase-field assembly rather than by the PIDL post-fit helper.

## Left Precrack Band Area-Mean Drivers

|   cycle | driver         |         fem |          pidl |   pidl_over_fem |
|--------:|:---------------|------------:|--------------:|----------------:|
|       1 | active_g       |  0.0048531  |   0.00129715  |      0.267282   |
|       1 | fatigue_active |  0.0048531  |   0.00129715  |      0.267282   |
|       1 | raw            | 63.9208     | 131.711       |      2.06053    |
|      20 | active_g       |  0.00587956 |   0.000477797 |      0.0812641  |
|      20 | fatigue_active |  0.0040227  |   0.000464936 |      0.115578   |
|      20 | raw            | 74.7383     | 149.727       |      2.00335    |
|      40 | active_g       |  0.0155877  |   0.000315621 |      0.020248   |
|      40 | fatigue_active |  0.00214497 |   0.000306653 |      0.142964   |
|      40 | raw            | 76.6375     | 167.439       |      2.18482    |
|      69 | active_g       |  0.0208632  |   0.000165705 |      0.00794244 |
|      69 | fatigue_active |  0.00121342 |   0.000156748 |      0.129178   |
|      69 | raw            | 72.3062     | 176.965       |      2.44744    |

## Driver vs Delta Alpha-Bar Correlation In Left Precrack Band

| solver   |   cycle | driver         |   driver_delta_alpha_bar_corr |   delta_alpha_bar_area_mean |   driver_area_mean |
|:---------|--------:|:---------------|------------------------------:|----------------------------:|-------------------:|
| FEM      |       1 | raw            |                      0.892527 |                  0.0159985  |       63.9208      |
| FEM      |       1 | active_g       |                      0.835455 |                  0.0159985  |        0.0048531   |
| FEM      |       1 | fatigue_active |                      0.835455 |                  0.0159985  |        0.0048531   |
| PIDL     |       1 | raw            |                      0.646491 |                  0.016386   |      131.711       |
| PIDL     |       1 | active_g       |                      0.335937 |                  0.016386   |        0.00129715  |
| PIDL     |       1 | fatigue_active |                      0.335937 |                  0.016386   |        0.00129715  |
| FEM      |      20 | raw            |                      0.953138 |                  0.0980375  |       74.7383      |
| FEM      |      20 | active_g       |                      0.963245 |                  0.0980375  |        0.00587956  |
| FEM      |      20 | fatigue_active |                      0.951731 |                  0.0980375  |        0.0040227   |
| PIDL     |      20 | raw            |                      0.583873 |                  0.0154978  |      149.727       |
| PIDL     |      20 | active_g       |                      0.861193 |                  0.0154978  |        0.000477797 |
| PIDL     |      20 | fatigue_active |                      0.78154  |                  0.0154978  |        0.000464936 |
| FEM      |      40 | raw            |                      0.951542 |                  0.220331   |       76.6375      |
| FEM      |      40 | active_g       |                      0.991903 |                  0.220331   |        0.0155877   |
| FEM      |      40 | fatigue_active |                      0.843796 |                  0.220331   |        0.00214497  |
| PIDL     |      40 | raw            |                      0.91972  |                  0.00858482 |      167.439       |
| PIDL     |      40 | active_g       |                      0.937395 |                  0.00858482 |        0.000315621 |
| PIDL     |      40 | fatigue_active |                      0.91888  |                  0.00858482 |        0.000306653 |
| FEM      |      69 | raw            |                      0.868935 |                  0.18884    |       72.3062      |
| FEM      |      69 | active_g       |                      0.998596 |                  0.18884    |        0.0208632   |
| FEM      |      69 | fatigue_active |                      0.344933 |                  0.18884    |        0.00121342  |
| PIDL     |      69 | raw            |                      0.862128 |                  0.0019359  |      176.965       |
| PIDL     |      69 | active_g       |                      0.856348 |                  0.0019359  |        0.000165705 |
| PIDL     |      69 | fatigue_active |                      0.84616  |                  0.0019359  |        0.000156748 |

## Outputs

- `tables/history_driver_definition_reductions.csv`
- `tables/history_driver_vs_delta_alpha_bar.csv`
- `figures/history_driver_definition_reductions.png`
- `figures/history_driver_delta_alpha_bar_correlations.png`

## Preliminary Interpretation

If PIDL is compared to FEM using the current strict run, PIDL is closest to the `active_g` driver by construction. FEM has substantial raw and active driver in/near the retained precrack band after loading, so allowing history everywhere lets FEM accumulate fatigue there. A fatigue-only precrack mask is the clean next discriminator: keep the soft retained mechanical precrack, but freeze fatigue history in the old crack band.
