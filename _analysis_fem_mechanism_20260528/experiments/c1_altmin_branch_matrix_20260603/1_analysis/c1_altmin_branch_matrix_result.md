# C1 Alt-Min Branch Matrix Result

## Final UV-State Summary

| branch            | selected_uv   |   psi_raw_max |   psi_active_max |   alpha_max_after_alpha |   grad_logEhist_after_alpha |   eps_eq_tip2_ratio |   psi_raw_max_ratio |   psi_active_tip2_ratio |   alpha_max_ratio |
|:------------------|:--------------|--------------:|-----------------:|------------------------:|----------------------------:|--------------------:|--------------------:|------------------------:|------------------:|
| baseline_r3_a2000 | r3_uv         |       2409.92 |         0.981586 |                 1.00061 |                     1071.66 |             1.01174 |             3.51348 |                 1.04188 |           1.00342 |
| shortAlpha_a200   | r3_uv         |       2519.08 |         0.620027 |                 1.0006  |                     1051.22 |             1.03429 |             3.67263 |                 1.06906 |           1.00345 |
| shortAlpha_a500   | r3_uv         |       2422.88 |         1.05074  |                 1.0006  |                     1024.38 |             1.01247 |             3.53238 |                 1.04634 |           1.00342 |
| smallStagger_r6   | r6_uv         |       2643.46 |         0.350268 |                 1.00063 |                     1149.38 |             1.05142 |             3.85396 |                 1.04836 |           1.00364 |
| alphaLR1e6_r6     | r6_uv         |       2642.22 |         0.35232  |                 1.00064 |                     1094.29 |             1.0507  |             3.85216 |                 1.05204 |           1.00365 |

## Interpretation

- Shortening alpha from 2000 to 200 or 500 epochs does not stop the final uv re-equilibration from rebuilding the raw hotspot.
- Smaller repeated uv/alpha blocks also do not suppress the feedback; by the final uv stage, `psi_raw_max` returns to the same order as the original coupled c1 hotspot.
- Lowering alpha RPROP lr to `1e-6` has little effect, consistent with RPROP sign-based updates and/or the alpha stage still being dominated by the irreversibility gradient channel.
- The useful conclusion is negative but sharp: the feedback loop is robust to simple alpha softening and small stagger schedules. The next lever should target the alpha irreversibility/update formulation or the local stiffness/degradation response, not just epoch scheduling.

## Figures

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_branch_matrix_20260603/2_figures/c1_altmin_branch_scalar_matrix.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_branch_matrix_20260603/2_figures/c1_altmin_branch_final_ratios.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/c1_altmin_branch_matrix_20260603/2_figures/c1_altmin_branch_final_summary.csv`
