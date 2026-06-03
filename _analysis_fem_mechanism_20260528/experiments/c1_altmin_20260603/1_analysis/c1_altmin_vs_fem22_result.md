# C1 Alt-Min vs FEM22 Result

## Key Scalar Trace

|   stage_index | label         |       E_el |        E_d |      E_hist |   log10_E_total |   grad_logEel |   grad_logEd |   grad_logEhist |   alpha_max |   psi_raw_max |   psi_active_max |
|--------------:|:--------------|-----------:|-----------:|------------:|----------------:|--------------:|-------------:|----------------:|------------:|--------------:|-----------------:|
|             0 | initial_joint | 0.0049153  | 0.00546076 | 2.34007e-05 |        -1.98299 |    0          |      0       |           0     |    1.00054  |     2703.68   |         0.923909 |
|             0 | initial_uv    | 0.0223328  | 0.00508514 | 0           |        -1.56197 |    0          |      0       |           0     |    0.936667 |     2703.68   |        43.3818   |
|             1 | r1_uv         | 0.00746278 | 0.00508514 | 0           |        -1.90143 |    0.0650392  |      0       |           0     |    0.936667 |       53.9486 |         0.865002 |
|             2 | r1_alpha      | 0.00703283 | 0.00525494 | 1.07074e-05 |        -1.91015 |    1.58496    |      3.9317  |         898.651 |    0.98508  |       53.9486 |         0.261502 |
|             3 | r2_uv         | 0.00631392 | 0.00525494 | 1.07074e-05 |        -1.93631 |    0.0101993  |      0       |           0     |    0.98508  |      571.627  |         3.41172  |
|             4 | r2_alpha      | 0.00561733 | 0.00544874 | 9.02547e-06 |        -1.95565 |    1.77875    |      3.36942 |         938.213 |    1.00041  |      571.627  |         0.259428 |
|             5 | r3_uv         | 0.0049519  | 0.00544874 | 9.02547e-06 |        -1.98256 |    0.00414614 |      0       |           0     |    1.00041  |     2409.92   |         0.981586 |
|             6 | r3_alpha      | 0.00485396 | 0.0054797  | 7.63203e-06 |        -1.98543 |    1.12241    |      2.46986 |        1071.66  |    1.00061  |     2409.92   |         0.317675 |

## Key FEM Ratios

| state | eps_eq tip2 | psi_raw max | psi_active tip2 | alpha max |
|---|---:|---:|---:|---:|
| initial_joint | 1.058 | 3.942 | 1.171 | 1.004 |
| initial_uv | 1.058 | 3.942 | 1.634 | 0.9395 |
| r1_uv | 0.5158 | 0.07865 | 0.4628 | 0.9395 |
| r1_alpha | 0.5158 | 0.07865 | 0.3796 | 0.988 |
| r2_uv | 0.7526 | 0.8334 | 0.6753 | 0.988 |
| r2_alpha | 0.7526 | 0.8334 | 0.6602 | 1.003 |
| r3_uv | 1.012 | 3.513 | 1.042 | 1.003 |
| r3_alpha | 1.012 | 3.513 | 0.9779 | 1.004 |

## Interpretation

- The first fixed-alpha uv solve cools the raw hotspot strongly: `psi_raw_max` falls from the pretrained coupled value to the same order as the frozen-alpha diagnostic.
- The first alpha-only solve does not restore the raw hotspot. It mainly changes alpha/dissipation under a very large `grad_logEhist` signal.
- The raw hotspot reappears during later uv re-equilibration after alpha has moved: `r2_uv` raises `psi_raw_max`, and `r3_uv` returns it close to the original coupled hotspot.
- This points to a feedback loop: alpha update changes degradation/stiffness, then the uv equilibrium stage relocates/concentrates raw strain around that updated damage field.

## Figures

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_20260603/2_figures/c1_altmin_scalar_trace.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_20260603/2_figures/c1_altmin_vs_fem22_key_ratios.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_20260603/2_figures/c1_altmin_tip_maps.png`
