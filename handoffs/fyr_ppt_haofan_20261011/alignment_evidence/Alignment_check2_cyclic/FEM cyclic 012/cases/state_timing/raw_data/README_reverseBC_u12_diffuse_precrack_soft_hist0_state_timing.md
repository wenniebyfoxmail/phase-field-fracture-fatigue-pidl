# reverseBC u=0.12 soft-hist0 state timing export

Request: `docs/handovers/windows_fem_inbox.md Request 20`.

Files:
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29\state_timing_metrics.csv`: state-level reductions and timing flags.
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29\state_timing_element_fields.mat`: element fields for each state.
- `mesh_geometry.mat`: same continuous-material mesh.

Settings:
- Base run: `SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC`; replay run: `SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_state_timing_replay`.
- Nodes/elements: 45591 / 45000; element type: Q4 quadrilateral.
- Material/fatigue: AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2, tol_irrev=1e-3, res_stiff=1e-6.
- Loading/BC: reverseBC u=0.12, R=0, fix_X top+bottom, fix_Y bottom, disp_Y top.

Timing interpretation:
- `Standard GRIPHFiTH cycle 1 has five retained substeps after unloading-prune; history is refreshed after each converged substep.`
- `cycle1_peak_pre_history_refresh is before the peak substep refresh, but after earlier loading-substep refreshes.`
- `psi_plus_elem` is the current-state tensile elastic energy density for that state.
- `psi_plus_peak_to_date_elem` is the running maximum across cycle-1 substeps up to that state.
- Initial precrack penetration guard active: 1.

Initial precrack audit:
- Precrack support nodes/elements with d>0: 5170 / 5432.
- Precrack nodal d mean/max: 0.32970086077 / 1.
- Precrack element d mean/max: 0.313181783907 / 0.905.
- Initial alpha_bar/f_alpha: 0 / 1.

Old c1 handoff comparison:
- Old handoff file: `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28\reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`.
- Old c1 timing note: Old c1 handoff stores end-of-cycle d/alpha/f with peak-over-cycle psi_plus.
- Max abs d/alpha/f difference vs `cycle1_unloaded_post_history_refresh`: 0 / 0 / 0.
- Max abs old psi vs `cycle1_peak_post_history_refresh` current psi: 0.322501078714.
- Max abs old psi vs `cycle1_unloaded_post_history_refresh` peak-to-date psi: 0.
