# Same Driver Same Fields Audit - 2026-06-09

## Purpose

Compare FEM and PIDL fatigue-history driver candidates on the same mapped states and common FEM element grid. PIDL triangles are area-averaged onto the FEM quadrilateral cells before reduction.

## Driver Definitions

- `raw_driver`: undegraded tensile energy `psi+`.
- `active_driver`: degraded tensile energy `g(alpha) * psi+`.
- `fatigue_effective_driver`: `f(alpha_bar) * g(alpha) * psi+`.
- `g_from_driver_ratio`: closure check `(g*psi+)/psi+`.
- `f_from_driver_ratio`: closure check `(f*g*psi+)/(g*psi+)`.

FEM's actual fatigue update is Gauss-point and substep based, so the element-level fields here are post-hoc comparable reductions, not a replacement for the internal GP update trace.

## Left Precrack Band Key Rows

| state    | quantity                 |         fem |          pidl |   pidl_over_fem |
|:---------|:-------------------------|------------:|--------------:|----------------:|
| c1_peak  | raw_driver               | 63.9208     | 131.711       |      2.06053    |
| c1_peak  | active_driver            |  0.0048531  |   0.00129715  |      0.267282   |
| c1_peak  | fatigue_effective_driver |  0.0048531  |   0.00129715  |      0.267282   |
| c1_peak  | g_direct                 |  0.256871   |   0.27744     |      1.08008    |
| c1_peak  | f_direct                 |  1          |   1           |      1          |
| c20_peak | raw_driver               | 74.7383     | 149.727       |      2.00335    |
| c20_peak | active_driver            |  0.00587956 |   0.000477797 |      0.0812641  |
| c20_peak | fatigue_effective_driver |  0.0040227  |   0.000464936 |      0.115578   |
| c20_peak | g_direct                 |  0.248504   |   0.22786     |      0.916929   |
| c20_peak | f_direct                 |  0.955221   |   0.998951    |      1.04578    |
| c40_peak | raw_driver               | 76.6375     | 167.439       |      2.18482    |
| c40_peak | active_driver            |  0.0155877  |   0.000315621 |      0.020248   |
| c40_peak | fatigue_effective_driver |  0.00214497 |   0.000306653 |      0.142964   |
| c40_peak | g_direct                 |  0.241207   |   0.205074    |      0.850198   |
| c40_peak | f_direct                 |  0.885412   |   0.997832    |      1.12697    |
| c69_peak | raw_driver               | 72.3062     | 176.965       |      2.44744    |
| c69_peak | active_driver            |  0.0208632  |   0.000165705 |      0.00794244 |
| c69_peak | fatigue_effective_driver |  0.00121342 |   0.000156748 |      0.129178   |
| c69_peak | g_direct                 |  0.238087   |   0.182171    |      0.765144   |
| c69_peak | f_direct                 |  0.867789   |   0.995144    |      1.14676    |

## Tip Column Key Rows

| state    | quantity                 |         fem |         pidl |   pidl_over_fem |
|:---------|:-------------------------|------------:|-------------:|----------------:|
| c1_peak  | raw_driver               |  0.245491   |  0.404155    |       1.64631   |
| c1_peak  | active_driver            |  0.0323545  |  0.0341274   |       1.0548    |
| c1_peak  | fatigue_effective_driver |  0.0323545  |  0.0341274   |       1.0548    |
| c1_peak  | g_direct                 |  0.934772   |  0.932986    |       0.99809   |
| c1_peak  | f_direct                 |  1          |  1           |       1         |
| c20_peak | raw_driver               |  9.82695    |  9.77642     |       0.994858  |
| c20_peak | active_driver            |  0.00156055 |  0.00156367  |       1.002     |
| c20_peak | fatigue_effective_driver |  0.00117181 |  0.00147342  |       1.25739   |
| c20_peak | g_direct                 |  0.8752     |  0.864983    |       0.988326  |
| c20_peak | f_direct                 |  0.940708   |  0.934191    |       0.993072  |
| c40_peak | raw_driver               | 20.7344     | 22.1143      |       1.06655   |
| c40_peak | active_driver            |  0.00183287 |  0.000473899 |       0.258556  |
| c40_peak | fatigue_effective_driver |  0.0006245  |  0.000422982 |       0.677313  |
| c40_peak | g_direct                 |  0.874242   |  0.855363    |       0.978405  |
| c40_peak | f_direct                 |  0.935816   |  0.930595    |       0.99442   |
| c69_peak | raw_driver               | 26.5839     | 31.3944      |       1.18095   |
| c69_peak | active_driver            |  0.00306236 |  0.00029475  |       0.0962495 |
| c69_peak | fatigue_effective_driver |  0.00011744 |  0.000275528 |       2.34611   |
| c69_peak | g_direct                 |  0.873052   |  0.846159    |       0.969196  |
| c69_peak | f_direct                 |  0.930583   |  0.926766    |       0.995898  |

## Active Driver vs Delta Alpha-Bar

| solver   | from_state                         | to_state   | region             |   driver_area_mean |   delta_alpha_bar_area_mean |   corr_driver_delta_alpha_bar |
|:---------|:-----------------------------------|:-----------|:-------------------|-------------------:|----------------------------:|------------------------------:|
| FEM      | state0_initial_unloaded_prehistory | c1_peak    | left_precrack_band |        0.0048531   |                  0.0159985  |                      0.835455 |
| FEM      | state0_initial_unloaded_prehistory | c1_peak    | tip_column         |        0.0323545   |                  0.0323545  |                      1        |
| PIDL     | state0_initial_unloaded_prehistory | c1_peak    | left_precrack_band |        0.00129715  |                  0.016386   |                      0.335937 |
| PIDL     | state0_initial_unloaded_prehistory | c1_peak    | tip_column         |        0.0341274   |                  0.0343237  |                      0.995654 |
| FEM      | c3_unloaded                        | c20_peak   | left_precrack_band |        0.00587956  |                  0.0868304  |                      0.974883 |
| FEM      | c3_unloaded                        | c20_peak   | tip_column         |        0.00156055  |                  0.266712   |                      0.447583 |
| PIDL     | c3_unloaded                        | c20_peak   | left_precrack_band |        0.000477797 |                  0.0126849  |                      0.897803 |
| PIDL     | c3_unloaded                        | c20_peak   | tip_column         |        0.00156367  |                  0.270556   |                      0.229875 |
| FEM      | c20_unloaded                       | c40_peak   | left_precrack_band |        0.0155877   |                  0.220331   |                      0.991903 |
| FEM      | c20_unloaded                       | c40_peak   | tip_column         |        0.00183287  |                  0.0270735  |                      0.947564 |
| PIDL     | c20_unloaded                       | c40_peak   | left_precrack_band |        0.000315621 |                  0.00858482 |                      0.937395 |
| PIDL     | c20_unloaded                       | c40_peak   | tip_column         |        0.000473899 |                  0.0119853  |                      0.849568 |
| FEM      | c60_unloaded                       | c69_peak   | left_precrack_band |        0.0208632   |                  0.18884    |                      0.998596 |
| FEM      | c60_unloaded                       | c69_peak   | tip_column         |        0.00306236  |                  0.0298731  |                      0.999933 |
| PIDL     | c60_unloaded                       | c69_peak   | left_precrack_band |        0.000165705 |                  0.0019359  |                      0.856348 |
| PIDL     | c60_unloaded                       | c69_peak   | tip_column         |        0.00029475  |                  0.00310025 |                      0.710823 |

## Outputs

- `tables/same_driver_same_fields_reductions.csv`
- `tables/same_driver_same_fields_delta_alpha.csv`
- `figures/same_driver_same_fields_area_means.png/pdf`
- `figures/same_driver_same_fields_effective_degradation.png/pdf`
- `figures/same_driver_same_fields_delta_alpha.png/pdf`
- `figures/same_driver_same_fields_residual_fields.png/pdf`
