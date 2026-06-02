# PIDL vs FEM n_step=2 Timing Audit

Reference: FEM Request21 `n_step=2`, retained load factors `[1, 0]`, `N_f=70`.
PIDL mapping: FEM cycle `c` compared with PIDL saved checkpoint `j=c-1`.

## Key Ratios

| cycle | alpha_bar tip2 | Delta alpha_bar tip2 | psi_raw tip2 | g(alpha) tip2 | psi_active tip2 | Delta E_d |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.982 | 0.982 | 2.26 | 0.9909 | 0.9995 | nan |
| 2 | 0.9787 | 0.9754 | 2.202 | 0.9879 | 0.9929 | -1.928 |
| 3 | 0.9765 | 0.972 | 2.181 | 0.9856 | 0.99 | -3.881 |
| 20 | 0.9875 | 0.3421 | 0.8879 | 0.994 | 1.252 | 0.1122 |
| 40 | 0.825 | 0.0982 | 1.012 | 0.9809 | 0.3018 | 0.2057 |
| 69 | 0.4615 | 0.008976 | 1.501 | 0.968 | 0.02015 | 0.2726 |

## Reading

PIDL is intended as a cyclic 0-to-peak update where unload does not add positive `Delta psi`; it is therefore conceptually closer to FEM `[1,0]` than to FEM peak-only `[1]`, but it still does not solve a separate unloaded equilibrium field.

This table should be read as a mechanism audit, not as a new fracture-cycle claim. `Delta E_d` is undefined at c1 because both references are zeroed at c1; later rows measure the incremental dissipated-energy growth relative to the same c1 convention.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_cadence_mechanism_full.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_cadence_mechanism_compact.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_cadence_mechanism_ratios.png`
