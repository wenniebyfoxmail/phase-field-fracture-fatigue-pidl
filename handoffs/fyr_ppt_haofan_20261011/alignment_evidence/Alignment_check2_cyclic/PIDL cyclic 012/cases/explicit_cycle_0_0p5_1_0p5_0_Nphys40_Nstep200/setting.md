# Setting: PIDL explicit cycle [0, 0.5, 1, 0.5, 0] Umax=0.12

- Solver family: PIDL / Deep Ritz neural phase-field fatigue.
- Boundary/loading: reverseBC Umax=0.12.
- Loading schedule: explicit substeps `[0, 0.5, 1, 0.5, 0]` per physical cycle.
- Run length: `Nphys=40`, `Nstep=200`.
- Raw model setting: `explicit_cycle_substeps=5`, `explicit_cycle_factors=[0.0, 0.5, 1.0, 0.5, 0.0]`.
- Result: no fracture by 40 physical cycles.
- Interpretation role: controlled timing diagnostic; locally available full `E_el` and `alpha_bar` traces, but not a full posthoc `E_d` decomposition.
- Raw data: `./raw_data/`.
- Optimisation evidence: `./raw_data/TBruns/` and `./raw_data/intermediate_models/` are present as copied from the local archive, but both are empty in that source.
- Analysis: `./analysis/soft_hist0_alignment_audit_summary_20260529.csv`.
- Figures: `./figures/pidl_explicit_substep_energy_diagnostic_20260607.png`.
