# Split-Trunk FEM-Mesh Discriminator

Date checked on Mac: 2026-06-02

## Why This Note Exists

The split-trunk run was launched and archived on Taobo, but the local Mac branch
did not have a clear GitHub-tracked record of the result.  This note pins the
Taobo evidence so we do not accidentally propose the same test again.

## Source

Remote workspace:

```text
/mnt/data2/drtao/projects/pidl-split-trunk-c1e8ac9
```

Remote archive:

```text
/mnt/data2/drtao/pidl_archives/split_trunk_c1e8ac9/
hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_tsuv10split_stagedAlpha_splitTrunk_uv750-RPROP0.0001_a750-RPROP1e-05_j10000
```

Remote log:

```text
/mnt/data2/drtao/projects/pidl-split-trunk-c1e8ac9/SENS_tensile/run_logs/femmesh_splitTrunk_stagedHead_uv10_headgrad_u012_N100_seed1_20260601.log
```

The runner was `SENS_tensile/run_fem_mesh_staged_alpha_umax.py` from the Taobo
workspace.  The code there enables a `SplitTrunkNet` with independent `uv_net`
and `alpha_net`.  During staged training the log reports:

```text
[StagedAlpha] uv-head stage: uv_net branch active
[StagedAlpha] alpha-head stage: alpha_net branch active
```

So this is not merely the older row-head staging proxy.

## Settings

From remote `model_settings.txt`:

| setting | value |
|---|---|
| mesh | `meshed_geom_fem_soft_hist0.msh` |
| Umax | 0.12 |
| n_cycles | 100 |
| seed | 1 |
| uv stage | 750 epochs |
| alpha stage | 750 epochs |
| joint stage | 10000 epochs |
| uv optimizer | RPROP |
| alpha optimizer | RPROP |
| uv lr | 1e-4 |
| alpha lr | 1e-5 |
| split_trunk | True |
| diagnostic cycles | 0,1,2,3,20,40,69,80,99 |
| gradient balance | True |

Comparison row-head archive from the same protocol:

```text
/mnt/data2/drtao/pidl_archives/staged_head_730101a/
hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_tsuv10lr_stagedAlpha_uv750-RPROP0.0001_a750-RPROP1e-05_j10000
```

## Event Summary

| run | first boundary hit | confirmed stop | verdict |
|---|---:|---:|---|
| row-head staged | 80 | 83 | similar life window to baseline; field gap remains |
| true split-trunk | 77 | 80 | slightly earlier event; no mechanism closure |

## Split-Trunk Scalar Check

From remote scalar arrays:

| quantity | j68 | final j80 |
|---|---:|---:|
| alpha_bar max | 2.3180 | 2.3181 |
| alpha_bar mean | 0.2851 | 0.3004 |
| f_min | 0.1259 | 0.1259 |
| x_tip_alpha | 0.3900 | 0.5000 |
| Kt | 16.68 | 357.05 |
| E_el | 1.410e-3 | 7.810e-7 |

Remote protocol summary also recorded post-history state metrics:

| run | cycle | alpha_max | alpha_bar_max | f_min | psi_raw_max | psi_active_max | E_el | E_d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| split-trunk | 0 | 0.9995 | 0.4286 | 1.0000 | 2788.39 | 0.4286 | 0.004787 | 0.005433 |
| split-trunk | 20 | 1.0001 | 2.3161 | 0.1261 | 2801.66 | 0.5116 | 0.004224 | 0.005610 |
| split-trunk | 40 | 1.0002 | 2.3172 | 0.1260 | 2836.54 | 0.4753 | 0.003244 | 0.006112 |
| split-trunk | 69 | 1.0002 | 2.3180 | 0.1259 | 2640.48 | 0.4579 | 0.001340 | 0.007293 |
| split-trunk | 80 | 1.0002 | 2.3181 | 0.1259 | 2525.40 | 0.0128 | 0.000001 | 0.007970 |
| row-head | 69 | 1.0005 | 8.3728 | 0.0127 | 2680.71 | 0.3943 | 0.001514 | 0.007075 |
| row-head | 80 | 1.0004 | 8.9956 | 0.0111 | 2467.21 | 0.0645 | 0.000006 | 0.007836 |

## Gradient Gate

At cycle 80 pre-alpha-history-refresh:

| run | E_el | E_d | E_hist | contrib_E_el_grms | contrib_E_d_grms | contrib_E_hist_grms |
|---|---:|---:|---:|---:|---:|---:|
| split-trunk | 7.81e-7 | 7.970e-3 | 4.33e-6 | 3.05e-3 | 1.92e-2 | 1.71e-2 |
| row-head | 5.73e-6 | 7.836e-3 | 4.24e-6 | 8.59e-3 | 2.43e-2 | 2.03e-2 |

## Interpretation

The user's memory was correct: a true split-trunk/separate staged optimizer
branch was tried on Taobo.  It should be treated as a useful negative
discriminator, not as an untested next idea.

What it changed:

- `alpha_bar_max` became much smaller than row-head staging near the event.
- It reached the boundary slightly earlier, first at cycle 77 and confirmed at
  cycle 80.
- The final event still shows elastic collapse (`E_el` near zero) and active
  driver collapse (`psi_active_max` drops to about 0.0128 at cycle 80).

What it did not fix:

- It did not recover the FEM-like active-driver/history trajectory.
- It did not remove the late boundary-event mechanism.
- It did not close the core aligned FEM/PIDL field gap.

Decision: do not propose "separate u/v and alpha trunks or optimizers" as a new
experiment unless the design is materially different from this Taobo branch.
