# Setting: FEM n_step=3 cyclic soft-hist0 Umax=0.12

- Solver family: FEM / GRIPHFiTH phase-field fatigue.
- Geometry and BC: reverseBC SENT, Umax=0.12, retained-material diffuse precrack.
- Material/model: AT1 + AMOR + PENALTY, `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `alpha_T=0.5`, `p=2`.
- Initial fatigue state: `alpha_bar=0`, `f_alpha=1`.
- Loading schedule: retained states approximately `[0.5, 1, 0]`.
- Result: right-boundary penetration at `N_f=70`.
- Raw data: `./raw_data/`.
- Analysis: `./analysis/request21_fem_nstep/fem_request21_field_reductions_long.csv`, `fem_request21_c69_summary.csv`, and `fem_request21_event_summary.csv`.
- Figures: `./figures/fem_request21_cadence_summary_20260530.png` and `./figures/fem_request21_event_ratio_heatmap_20260530.png`.
