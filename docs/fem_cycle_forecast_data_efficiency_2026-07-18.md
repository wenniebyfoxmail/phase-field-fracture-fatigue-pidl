# FEM Cycle Forecast Data-Efficiency Matrix

## Scope

Taobo run `pf_cycleforecast_cecaf20_20260718_0848` trained a frozen matrix from commit `cecaf208e590ebaafd299d99fcb309235ea65bb1` on the complete eta=0 FEM c1-c89 cycle-peak trajectory. The matrix contains `C_train={20,40,60,67}`, temporal context `k={1,3,5,10}`, a parameter-matched pointwise baseline, the multiscale mesh operator (`k=1`), temporal mesh variants, and persistence. Every learned cell used seed 1 and 3000 fixed steps.

## Data firewall

Each cell uses only c1 through its cutoff for normalization and training. There is no future-driven early stopping. The nominal context choice was written and hashed from nonlocked c77-c86 results before c89 was opened. c89 was then evaluated once for the frozen checkpoints. Dataset SHA-256 was `bd5b731daeb0718368309cd50c44fa7422e49096b495f619eba429d1c6bde419` on Mac and Taobo.

## Result

- c20 is sufficient for reliable next-cycle prediction among the tested cutoffs, but it is not a proven minimum below c20; persistence is already strong in this smooth early regime.
- k3 is the nominal global choice by mean c76-origin h10 active log-MAE (`0.4793` versus `0.4796` for k1), which is a negligible tie. Extra history is therefore not uniformly better. With the full c67 prefix, k10 gives the lowest ordinary c67-origin h10 active log-MAE (`0.104`).
- At the near-event c76 origin, k3/k5/k10 pass the complete FEM-centred gate through h3. The selected c67/k3 model first fails at h4/c80 because absolute-p99 IoU falls to `0.443`, even though active log-MAE is only `0.086`.
- All contexts catastrophically miss c89. Selected k3 gives active log-MAE `3.0265`, correlation `-0.4500`, absolute-p99 IoU `0.0100`, and support-area ratio `96.76`. Longer history of the same four fields does not identify the late regime transition.

## Interpretation boundary

This is single-trajectory temporal evidence. Only one complete compatible trajectory was available, so leave-one-trajectory-out was impossible. Do not claim transfer across physical trajectories, geometry, mesh, load amplitude, or material parameters.

## Assets

Local package:

`local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/fem_cycle_forecast_data_efficiency_20260718/`

Primary files are `analysis/RUN_MANIFEST.json`, `analysis/data_efficiency_matrix.csv`, `analysis/context_length_x_rollout_horizon_heatmap.png`, `analysis/near_event_rollout_error_growth.png`, `analysis/fem_field_residual_panel_c89.png`, `analysis/fem_active_support_panel_c89.png`, and `analysis/decision.md`. All 120 downloaded training files match Taobo SHA-256 hashes, and the deterministic package validator passes.
