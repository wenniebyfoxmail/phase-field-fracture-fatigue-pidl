# FEM standard vs PIDL FEM-like substep deep dive, 2026-06-08

Most comparable pair: FEM `standard` and PIDL `stateTiming_substeps025_untilFrac_Nphys120_Nstep600`.

Correction: FEM `peak_only` is not cyclic loading; it is a no-unload control and should not be interpreted as a cyclic cadence variant.

Cycle mapping used here: FEM cycle `c` maps to PIDL peak substep `5*c-2` for mechanical drivers and PIDL cycle-end substep `5*c-1` for damage/history variables.

Stress/strain caveat: tensor stress and tensor strain are not exported in these organized files. Figures therefore use `psi_plus`, PIDL `psi_raw`, PIDL `psi_active`, and `Kt_proxy` as scalar mechanical-driver proxies.

For `E_d density` residual panels, FEM elementwise `E_d` density was not exported in this organized FEM MAT file; the panel uses a zero FEM placeholder and should be read only as a PIDL localisation map, not a true FEM-PIDL residual.

Generated figures:
- `delta_alpha_bar_process_zone_alignment.png`
- `energy_Eel_Ed_Ehist_over_cycles.png`
- `parameter_driver_metrics_over_cycles.png`
- `residual_fields_c01_pidl_minus_fem.png`
- `residual_fields_c20_pidl_minus_fem.png`
- `residual_fields_c40_pidl_minus_fem.png`
- `residual_fields_c69_pidl_minus_fem.png`

Generated tables:
- `delta_alpha_bar_process_zone_overlap_metrics.csv`
- `pidl_substep_sampled_energy_by_fem_cycle.csv`
- `pidl_substep_sampled_parameter_metrics_by_fem_cycle.csv`
