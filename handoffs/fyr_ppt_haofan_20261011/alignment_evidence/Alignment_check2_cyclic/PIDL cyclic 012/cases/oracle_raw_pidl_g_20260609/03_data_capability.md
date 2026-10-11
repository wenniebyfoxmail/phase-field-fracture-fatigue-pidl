# Data Capability: oracle_raw_pidl_g_20260609

Status: downloaded, verified, and analysis-regenerated on 2026-06-09.

Launch configuration and live remote audit:

- state-timing element diagnostics: expected for steps `0, 3, 4, 8, 9, 13, 14, 98, 99, 198, 199, 298, 299, 343, 344`.
- true unloaded `state0_initial_unloaded_prehistory`: not expected by default; PIDL step 0 is load factor `0.25`, not true state0.
- strain/stress fields: verified present in every currently exported element-diagnostic file.
- gradient diagnostics: expected, pre-history-refresh, every step and on key states.
- alpha snapshots: expected every 20 steps and dense/fracture states.
- scalar histories: expected in `best_models/`.
- element diagnostics: expected in `element_diagnostics_oracle_raw_pidl_g/`.
- final checkpoint/model: verified, `checkpoint_step_346.pt` and `trained_1NN_346.pt`.

Remote audit detail:

- archive path: `/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141/oracle_raw_pidl_g_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc80_Nstep400_U0.12_oracle_raw_pidl_g_full_s0.25-0.5-0.75-1-0/element_diagnostics_oracle_raw_pidl_g/`
- element `.npz` files audited: 17 currently exported files, including required state steps `0000, 0003, 0004, 0008, 0009, 0013, 0014, 0098, 0099, 0198, 0199, 0298, 0299, 0343, 0344`; extra live exports `0345, 0346` were also present.
- missing required keys: none.
- non-finite values in required arrays: none.
- local archive verification: 1161 files, about 2.149 GiB; see `02_download_verification.md`.
- generated analysis includes scalar histories, gradient balance, selected fields, state-mapped FEM/PIDL residual maps, energy-driver residuals, and strain/stress residual figures.

Verified required element arrays:

- geometry/state: `elem_x`, `elem_y`, `area_elem`, `cycle`.
- damage/history/fatigue: `alpha_elem`, `hist_fat_elem`, `g_alpha_elem`, `f_fatigue_elem`.
- energy/driver: `psi_raw_elem`, `psi_active_elem`, `psi_history_driver_elem`, `psi_plus_elem`, `psi_plus_prev_elem`, `E_el_elem`, `E_d_elem`, `E_hist_elem`, `residual_abs_Eel_Ed`.
- strain: `eps_xx_elem`, `eps_yy_elem`, `eps_xy_elem`, `eps_trace_elem`, `eps_eq_elem`, `eps_principal_1_elem`, `eps_principal_2_elem`.
- raw stress: `sigma_raw_xx_elem`, `sigma_raw_yy_elem`, `sigma_raw_xy_elem`, `sigma_raw_principal_1_elem`, `sigma_raw_principal_2_elem`.
- effective stress: `sigma_effective_xx_elem`, `sigma_effective_yy_elem`, `sigma_effective_xy_elem`, `sigma_effective_principal_1_elem`, `sigma_effective_principal_2_elem`.
- oracle input: `delta_alpha_bar_input_elem` recorded as a common diagnostic slot; for this run it should remain zero/non-operative.

Important caveat:

The oracle uses peak FEM cycle fields with explicit five-substep PIDL mapping. Intermediate `psi`/energy-like values are load-factor-squared elastic approximations, not true FEM substep exports. Irreversible fields are not scaled this way.
