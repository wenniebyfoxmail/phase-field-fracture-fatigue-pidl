# Setting: FEM standard cyclic soft-hist0 Umax=0.12

- Solver family: FEM / GRIPHFiTH phase-field fatigue.
- Geometry and BC: reverseBC SENT, Umax=0.12, retained-material diffuse precrack.
- Material/model: AT1 + AMOR + PENALTY, `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `alpha_T=0.5`, `p=2`.
- Initial fatigue state: `alpha_bar=0`, `f_alpha=1`.
- Loading schedule: standard retained cyclic substeps `[0.25, 0.5, 0.75, 1, 0]`.
- Result: right-boundary penetration at `N_f=69`.
- Raw data: `./raw_data/`.
- Analysis: `./analysis/`, especially `request21_fem_nstep/fem_request21_field_reductions_long.csv` and `aligned_fem_pidl_energy_tiers.csv`.
- Figures: `./figures/fem_request21_cadence_summary_20260530.png`, `./figures/fem_request21_field_reductions_20260530.png`, and `./figures/energy_over_cycle_fem_pidl_substep_comparison_20260607.png`.
