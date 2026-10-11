# Setting: PIDL one-peak FEM-mesh soft-hist0 Umax=0.12

- Solver family: PIDL / Deep Ritz neural phase-field fatigue.
- Geometry and mesh: strict FEM-derived soft-hist0 mesh.
- Boundary/loading: reverseBC-aligned Umax=0.12, one peak solve per physical cycle.
- Loading schedule: one retained peak state per cycle.
- Fatigue/history driver: baseline active degraded history.
- Run length: N100 nominal.
- Result: first boundary hit around c82, confirmed around c85 in the strict FEM-mesh baseline.
- Raw data: `./raw_data/`.
- Optimisation evidence: `./raw_data/TBruns/` and `./raw_data/intermediate_models/` are present as copied from the local archive, but both are empty in that source.
- Analysis: `./analysis/femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv`, `aligned_fem_pidl_energy_tiers.csv`, and `soft_hist0_alignment_audit_summary_20260529.csv`.
- Figures: `./figures/energy_over_cycle_fem_pidl_substep_comparison_20260607.png`.
