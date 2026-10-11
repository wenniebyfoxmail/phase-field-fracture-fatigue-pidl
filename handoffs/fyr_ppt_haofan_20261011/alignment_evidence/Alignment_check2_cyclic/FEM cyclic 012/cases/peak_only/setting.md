# Setting: FEM peak-only cyclic soft-hist0 Umax=0.12

- Solver family: FEM / GRIPHFiTH phase-field fatigue.
- Geometry and BC: reverseBC SENT, Umax=0.12, retained-material diffuse precrack.
- Material/model: AT1 + AMOR + PENALTY, `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `alpha_T=0.5`, `p=2`.
- Initial fatigue state: `alpha_bar=0`, `f_alpha=1`.
- Loading schedule: peak-only retained state `[1]`.
- Result: no penetration by c120.
- Interpretation role: one-factor control showing that retaining the unload/end-of-cycle state is decisive in FEM.
- Raw data: `./raw_data/`.
- Analysis: `./analysis/soft_hist0_alignment_audit_summary_20260529.csv` and `./docs/soft_hist0_alignment_audit_2026-05-29.md`.
- Figures: `./figures/fem_request21_cadence_summary_20260530.png`.
