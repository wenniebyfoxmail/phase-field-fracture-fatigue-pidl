# Frozen-Alpha Elastic Probe Result

Setup: fixed analytic soft-hist0 alpha, displacement-only elastic optimisation, started from the residual-stiffness post-pretraining checkpoint.

## Loss

- initial logged `E_el`: `2.233275e-02`
- final logged `E_el`: `7.187365e-03`
- logged reduction: `0.3218x`

## Key PIDL/FEM22 Ratios

|                                |   coupled_resstiff_c1 |   frozen_alpha_elastic |
|:-------------------------------|----------------------:|-----------------------:|
| ('eps_eq', 'max')              |                 1.892 |                 0.2159 |
| ('eps_eq', 'tip_2l0_mean')     |                 1.086 |                 0.5806 |
| ('eps_yy', 'max')              |                 2.02  |                 0.2306 |
| ('eps_yy', 'tip_2l0_mean')     |                 1.06  |                 0.6015 |
| ('psi_active', 'max')          |                 1.676 |                 2.279  |
| ('psi_active', 'tip_2l0_mean') |                 1.01  |                 0.5098 |
| ('psi_raw', 'max')             |                 4.068 |                 0.0527 |
| ('psi_raw', 'tip_2l0_mean')    |                 2.336 |                 0.2504 |

## Interpretation

Frozen-alpha elastic optimisation removes the coupled c1 raw-energy hotspot too strongly. Compared with FEM22, frozen-alpha gives `eps_eq` tip mean 0.581x, `psi_raw` tip mean 0.250x, and `psi_raw` max 0.0527x. The coupled c1 checkpoint had the opposite problem: `eps_eq` tip mean 1.086x, `psi_raw` tip mean 2.336x, and `psi_raw` max 4.068x.

The effective active driver is mixed: frozen-alpha `psi_active` tip mean is below FEM, while its max can sit above FEM because the maximum moves into less-degraded material. Therefore max alone is not a clean gate; tip/process-zone reductions and co-location remain necessary.

The useful conclusion is that the fixed initial alpha/precrack does not force the oversharp `psi_raw` spike. The spike is introduced by the coupled elastic-damage optimisation path. But freezing alpha completely under-drives the crack line, so the answer is not permanent alpha-freezing; it is a FEM-like alternate micro-solve that controls when u/v and alpha are allowed to relax.

Next diagnostic should be a true alternate-minimisation micro-solve at c1: freeze alpha -> solve u/v, then freeze u/v -> solve alpha, repeat a few times, exporting epsilon/psi after each substage.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/frozen_alpha_elastic_20260603/2_figures/frozen_alpha_elastic_vs_fem22_field_gate.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/frozen_alpha_elastic_20260603/2_figures/frozen_alpha_elastic_vs_coupled_c1_ratios.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/frozen_alpha_elastic_20260603/2_figures/frozen_alpha_elastic_c1_tip_maps.png`
