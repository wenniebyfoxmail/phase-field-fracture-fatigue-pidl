# Residual-Stiffness PIDL vs FEM22 Strain Diagnostic

Setup: PIDL residual-stiffness branch compared to FEM22 nstep2 whole-field peak-load states.

Timing convention: PIDL saved index `j` maps to FEM cycle `c=j+1`; FEM state is the loaded peak substep, using the later duplicate peak state after history refresh. Strain is unchanged across the duplicate pre/post history states.

## c1 Ratios

| metric       |   eps_eq |   eps_xx |    eps_xy |   eps_yy |   psi_raw |
|:-------------|---------:|---------:|----------:|---------:|----------:|
| max          |  1.892   |   0.2895 |    0.1579 |  2.02    | 4.068     |
| p99          |  0.02042 |   1.205  |    1.028  |  0.01834 | 0.0003501 |
| tip_2l0_mean |  1.086   |   0.971  | 5054      |  1.06    | 2.336     |

## Interpretation

The early `psi_raw` mismatch is already visible at the strain level, but not as a large error in the mean imposed strain. At c1 the tip-region equivalent strain is only 1.086x FEM, while equivalent-strain max is 1.892x and `psi_raw` max is 4.068x. That is consistent with strain energy amplifying localized strain extrema roughly quadratically.

`eps_xy` mean ratios are not physically meaningful because the FEM tip mean is close to zero; use p99/max and the field map instead for shear.

The stronger conclusion is therefore field-shape/localization: PIDL and FEM begin with similar damage/history averages, but PIDL has a sharper strain/energy hotspot.

A large PIDL `psi_raw_max` should therefore be read as a strain-localization diagnostic, not by itself as effective crack-driving work. The effective driver still depends on co-location with `g(alpha)` and the history update.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_epsilon_vs_fem22_field_gate.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_epsilon_vs_fem22_extrema.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_epsilon_vs_fem22_ratios.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_epsilon_vs_fem22_values.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/resstiff_alignment_20260603/2_figures/resstiff_epsilon_vs_fem22_c1_tip_maps.png`

Largest PIDL extrema locations are saved in the extrema CSV for checking whether high strain/psi is inside damaged material or the active process zone.
