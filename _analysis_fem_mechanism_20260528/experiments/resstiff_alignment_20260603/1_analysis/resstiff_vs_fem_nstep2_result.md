# Residual-Stiffness Alignment Discriminator

Setup: strict FEM-mesh soft-hist0 PIDL, with only `g(alpha)` changed to `(1-alpha)^2 + 1e-6`.

Timing convention: PIDL saved index `j` is compared to FEM n_step2 cycle `c=j+1`. Therefore PIDL `cycle_0000` is not pristine FEM state0; it maps to FEM c1.

## Event

- first boundary hit: PIDL j82
- confirmed stop: PIDL j85
- FEM n_step2 reference: N_f about c70

## Early Tip-2l0 Ratios

|        |   alpha_bar |   delta_alpha_bar |   g_alpha |   psi_active |   psi_raw |
|:-------|------------:|------------------:|----------:|-------------:|----------:|
| (0, 1) |      0.9924 |            0.9924 |    0.9918 |        1.01  |     2.336 |
| (1, 2) |      0.9895 |            0.9866 |    0.9908 |        1.004 |     2.272 |
| (2, 3) |      0.9872 |            0.9825 |    0.9879 |        1.001 |     2.255 |
| (3, 4) |      0.9876 |            0.9889 |    0.9871 |        1.01  |     2.258 |

## c69 Tip-2l0 Ratios

|          |   alpha_bar |   g_alpha |   psi_active |   psi_raw |
|:---------|------------:|----------:|-------------:|----------:|
| (68, 69) |      0.4762 |    0.9639 |      0.04191 |     1.527 |

## Interpretation

Adding FEM-style residual stiffness does not close the mechanism gap. It preserves a nonzero `g_alpha` floor in fully damaged elements, but the active process-zone comparison is still governed by spatial co-location: raw tensile energy, degradation, and fatigue increments do not line up FEM-like near the tip.

The run still shows late active-driver collapse. At PIDL j82-j85, `psi_raw_max` remains around 2.4e3 while `psi_active_max` is only about 1.2e-2 because the raw-psi maximum sits in nearly fully damaged material where `g_alpha` is near the residual floor.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_vs_fem_nstep2_field_gate.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_vs_fem_nstep2_scalars.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_vs_fem_nstep2_extrema.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_vs_fem_nstep2_field_gate.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_scalar_alpha_bar_psi_raw.png`
