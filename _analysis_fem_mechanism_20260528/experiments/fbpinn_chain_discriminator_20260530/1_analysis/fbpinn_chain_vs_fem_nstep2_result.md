# FBPINN-Chain vs FEM n_step2 Result

Reference: FEM Request21 `n_step=2 [1,0]`, projected by nearest element centroid onto PIDL diagnostic elements.

## Scalar Timing

| case              |   n_saved |   first_boundary_hit |   last_index |   x_tip_alpha_j68 |   x_tip_alpha_last |   alpha_bar_max_j68 |   alpha_bar_max_last |   f_min_j68 |   f_min_last |   Kt_j68 |   Kt_last |   E_el_j68 |   E_el_last |   FEM_nstep2_Nf |   FEM_c69_alpha_bar_elem_max |   FEM_c69_f_fatigue_min |   FEM_c69_Kt_proxy |
|:------------------|----------:|---------------------:|-------------:|------------------:|-------------------:|--------------------:|---------------------:|------------:|-------------:|---------:|----------:|-----------:|------------:|----------------:|-----------------------------:|------------------------:|-------------------:|
| PIDL FBPINN-chain |       100 |                  nan |           99 |             0.256 |              0.406 |             10.6931 |              14.5379 |  0.00798174 |   0.00442207 |  10.5769 |   16.6188 | 0.00254137 |      0.0013 |              70 |                      18.4591 |                0.017283 |            11.5568 |

## c69 Field Gate Ratios

| field        | metric       |   PIDL_over_FEM |
|:-------------|:-------------|----------------:|
| alpha_bar    | domain_mean  |         1.131   |
| alpha_bar    | max          |         0.5869  |
| alpha_bar    | p99          |         0.2279  |
| alpha_bar    | tip_2l0_mean |         0.5525  |
| damage_alpha | domain_mean  |         0.8235  |
| damage_alpha | max          |         0.9734  |
| damage_alpha | p99          |         0.9899  |
| damage_alpha | tip_2l0_mean |         1.041   |
| g_alpha      | domain_mean  |         1.005   |
| g_alpha      | max          |         1.004   |
| g_alpha      | p99          |         1.003   |
| g_alpha      | tip_2l0_mean |         0.9167  |
| psi_active   | domain_mean  |         2.612   |
| psi_active   | max          |         1.082   |
| psi_active   | p99          |         0.7283  |
| psi_active   | tip_2l0_mean |         0.03743 |
| psi_raw      | domain_mean  |         1.16    |
| psi_raw      | max          |         1.224   |
| psi_raw      | p99          |         0.07787 |
| psi_raw      | tip_2l0_mean |         1.37    |

## Reading

FBPINN-chain changes the failure mode: it does not hit the right boundary by j99, unlike the strict baseline/local-patch cases.  That is useful negative/diagnostic evidence because local subdomain authority can suppress boundary saturation.

It does not close the FEM mechanism.  At the matched c69 field gate, the crack-tip `alpha_bar` remains far below FEM and the active degraded driver remains much smaller than FEM.  The residual field also shows the active driver is off-location: FBPINN creates an interior active-psi packet around the middle of the crack path, while the FEM n_step2 field is already concentrated near the right process region.  The branch therefore trades the old boundary-saturation failure for slow/underdriven crack advance.

Decision: do not rerun the same FBPINN-chain as a solution.  Use it as evidence that stronger local representation affects propagation mode, then test a true split-trunk/alternating solve only if it includes head-wise gradients and the same c20/c40/c69 field gate.

Generated figures:
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/fbpinn_chain_discriminator_20260530/2_figures/fbpinn_chain_vs_fem_nstep2_field_gate.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/fbpinn_chain_discriminator_20260530/2_figures/fbpinn_chain_vs_fem_nstep2_c69_residual_fields.png`
