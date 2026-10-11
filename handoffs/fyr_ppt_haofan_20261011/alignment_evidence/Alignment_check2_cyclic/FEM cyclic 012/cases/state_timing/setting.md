# Setting: FEM cycle-1 state-timing export

- Solver family: FEM / GRIPHFiTH phase-field fatigue.
- Geometry and BC: same strict soft-hist0 reverseBC Umax=0.12 reference.
- Purpose: export cycle-1 pre-history, post-history, peak, and unloaded states so FEM/PIDL comparisons do not mix state labels.
- Loading schedule: standard retained cyclic substeps, with cycle-1 states separated.
- Key finding: old FEM c1 handoff used mixed timing: `d/alpha_bar/f` from unloaded post-history refresh, and `psi_plus` from peak-to-date.
- Raw data: `./raw_data/`.
- Analysis: `./analysis/soft_hist0_fem_state_timing_selected_metrics.csv`.
- Figures/docs: `./docs/windows_fem_outbox.md` and `./docs/soft_hist0_alignment_audit_2026-05-29.md`.
