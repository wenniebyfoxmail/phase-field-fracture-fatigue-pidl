# Staged Row-Head vs Split-Trunk Protocol Result, 2026-06-01

## Source

Both runs use strict FEM-mesh soft-hist0 PIDL settings with `Umax=0.12`,
`N100`, seed 1, `uv750 -> alpha750 -> joint10000`, diagnostic cycles
`0,1,2,3,20,40,69,80,99`, and routine state-timing plus gradient exports.

- row-head archive: `/mnt/data2/drtao/pidl_archives/staged_head_730101a/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_tsuv10lr_stagedAlpha_uv750-RPROP0.0001_a750-RPROP1e-05_j10000`
- split-trunk archive: `/mnt/data2/drtao/pidl_archives/split_trunk_c1e8ac9/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_tsuv10split_stagedAlpha_splitTrunk_uv750-RPROP0.0001_a750-RPROP1e-05_j10000`

## Event Summary

| run | first boundary hit | confirmed stop | verdict |
|---|---:|---:|---|
| row-head staged | 80 | 83 | life-window similar to baseline, field gap remains |
| true split-trunk | 77 | 80 | slightly earlier event, no mechanism closure |

## Post-History State Metrics

| run | cycle | alpha_max | alpha_bar_max | f_min | psi_raw_max | psi_active_max | E_el | E_d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| split-trunk | 0 | 0.9995 | 0.4286 | 1.0000 | 2788.39 | 0.4286 | 0.004787 | 0.005433 |
| split-trunk | 1 | 1.0001 | 0.8528 | 0.5464 | 2850.41 | 0.4243 | 0.004785 | 0.005428 |
| split-trunk | 2 | 1.0001 | 1.2842 | 0.3141 | 2793.50 | 0.4314 | 0.004784 | 0.005417 |
| split-trunk | 3 | 1.0001 | 1.7066 | 0.2054 | 2789.47 | 0.4224 | 0.004783 | 0.005404 |
| split-trunk | 20 | 1.0001 | 2.3161 | 0.1261 | 2801.66 | 0.5116 | 0.004224 | 0.005610 |
| split-trunk | 40 | 1.0002 | 2.3172 | 0.1260 | 2836.54 | 0.4753 | 0.003244 | 0.006112 |
| split-trunk | 69 | 1.0002 | 2.3180 | 0.1259 | 2640.48 | 0.4579 | 0.001340 | 0.007293 |
| split-trunk | 80 | 1.0002 | 2.3181 | 0.1259 | 2525.40 | 0.0128 | 0.000001 | 0.007970 |
| row-head | 0 | 0.9993 | 0.4268 | 1.0000 | 2803.53 | 0.4268 | 0.004793 | 0.005437 |
| row-head | 1 | 0.9996 | 0.8563 | 0.5436 | 2815.03 | 0.4295 | 0.004789 | 0.005431 |
| row-head | 2 | 1.0000 | 1.2759 | 0.3171 | 2798.21 | 0.4196 | 0.004788 | 0.005420 |
| row-head | 3 | 1.0000 | 1.6942 | 0.2077 | 2793.75 | 0.4184 | 0.004787 | 0.005407 |
| row-head | 20 | 1.0003 | 2.9084 | 0.0861 | 2820.60 | 0.4535 | 0.004267 | 0.005568 |
| row-head | 40 | 1.0003 | 5.8604 | 0.0247 | 2778.38 | 0.4276 | 0.003334 | 0.006011 |
| row-head | 69 | 1.0005 | 8.3728 | 0.0127 | 2680.71 | 0.3943 | 0.001514 | 0.007075 |
| row-head | 80 | 1.0004 | 8.9956 | 0.0111 | 2467.21 | 0.0645 | 0.000006 | 0.007836 |

## Gradient Gate

At cycle 80 pre-alpha-history-refresh:

| run | E_el | E_d | E_hist | contribE_el_grms | contribE_d_grms | contribE_hist_grms |
|---|---:|---:|---:|---:|---:|---:|
| split-trunk | 7.81e-7 | 7.970e-3 | 4.33e-6 | 3.05e-3 | 1.92e-2 | 1.71e-2 |
| row-head | 5.73e-6 | 7.836e-3 | 4.24e-6 | 8.59e-3 | 2.43e-2 | 2.03e-2 |

The split-trunk run has a much lower `alpha_bar_max` than row-head near the
event, but its elastic energy still collapses near the boundary hit and its
active driver also drops. It therefore changes the internal magnitude but does
not repair the coupled field trajectory.

## Interpretation

The true split-trunk design is a useful negative discriminator. Giving `u/v`
and `alpha` separate trunks plus separate staged optimizers changes the history
magnitude, but does not make the crack evolution FEM-like. The common problem
across both runs is early history accumulation followed by late elastic-driver
collapse near the boundary event.
