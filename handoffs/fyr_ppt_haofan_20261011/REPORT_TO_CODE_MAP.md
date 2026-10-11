# FYR report-to-code/data map

Status labels:

- `SCHEMATIC`: editable concept figure; no empirical dataset.
- `COMPACT_REPRO`: script plus compact tabular inputs are included.
- `SCRIPT_SUMMARY`: script and summary tables are included, but raw field or
  checkpoint inputs are external.
- `STATIC_ONLY`: use the frozen report figure; exact generating inputs were not
  preserved in a Git-safe form.
- `HISTORICAL`: preserves the FYR-era analysis and must use the later reporting
  correction when presented now.

| Report asset/group | Status | Frozen figure | Code | Included data / note |
|---|---|---|---|---|
| Chapter 3 benchmark geometry, protocol and neural-field diagrams | `SCHEMATIC` | `report_snapshot/Chapter3/Figs/` | `report_snapshot/scripts/generate_chapter3_figures.py`, `report_snapshot/scripts/generate_fyr_concept_figures.py` | Diagram parameters are encoded in the scripts. |
| Chapter 3 monotonic and initial-state alignment | `SCRIPT_SUMMARY`, `HISTORICAL` | `report_snapshot/Chapter3/Figs/PDF/c3_monotonic_fem_pidl_alignment.pdf`, `c3_initial_state_alignment.pdf` | `code_snapshot/PIDL/SENS_tensile_minimal/` comparison/export scripts | `alignment_evidence/Alignment_check_monotonic/` contains processed CSVs and audit notes. |
| Chapter 4 pre-alignment S--N sweep | `SCRIPT_SUMMARY`, `HISTORICAL` | `report_snapshot/Chapter4/Figs/PDF/c4_pre_alignment_nf_sweep.pdf` | `historical_plot_scripts/generate_figs_pidl_fem.py`, `generate_figs_sn_full.py` | Exact plotted scalar values are visible in the script/report figure; the original local `.npy` run folders are not in Git. Do not present the old event criterion as the current canonical contract. |
| Chapter 4 dispersed degradation and Umax=0.12 internal diagnostics | `SCRIPT_SUMMARY`, `HISTORICAL` | `c4_pre_alignment_dispersed_degradation.pdf`, `c4_pre_alignment_u012_internal_diagnostics.pdf` | `historical_plot_scripts/generate_figs_pidl_fem.py` | Original full per-cycle arrays are external; use the frozen figures for PPT unless a new analysis is explicitly commissioned. |
| Chapter 4 loading-protocol comparisons | `COMPACT_REPRO`, `HISTORICAL` | Chapter 4/5 protocol PDFs in `report_snapshot/` | analysis and plotting scripts under `alignment_evidence/Alignment_check2_cyclic/` | Protocol metrics and phase-front CSVs are under the FEM/PIDL `figures/protocol_comparison/` directories. |
| Chapter 4/5 energy histories and field residuals | `COMPACT_REPRO`, `HISTORICAL` | `report_snapshot/Chapter4/Figs/PDF/c4_damage_history_degradation_residuals.pdf`; Chapter 5 energy/residual PDFs | `code_snapshot/PIDL/SENS_tensile_minimal/compare_fem_pidl_cyclewise_mechanism.py`, `plot_fem_pidl_residual_fields.py` | Main tables are under `alignment_evidence/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/tables/`. |
| Chapter 4 projected residual figures | `SCRIPT_SUMMARY`, `HISTORICAL` | `projected_residual_*` and `tail_dense_projected_*` under `report_snapshot/Chapter4/Figs/PDF/` | `current_field_evidence/analysis_fem_grid_projection_residuals.py` | Summary, projection-quality and tail tables are included. Full projected `.npz` arrays are excluded from Git and remain in the local archive. |
| Chapter 4 method-outcome and variable-map graphics | `SCHEMATIC` / `STATIC_ONLY` | `c4_pre_alignment_method_outcomes_clean.pdf`, `c4_phase_field_variable_map.png` | no verified single generator retained in the frozen remote snapshot | Use the frozen assets; do not infer new numerical claims from them. |
| Chapter 5 history-driver and process-zone comparisons | `COMPACT_REPRO`, `HISTORICAL` | `c5_history_driver_definition_reductions.pdf`, `c5_delta_alpha_bar_process_zone_alignment.pdf` | audit/comparison scripts under `code_snapshot/PIDL/SENS_tensile_minimal/` | Relevant reductions and overlap tables are in `alignment_evidence/.../latest_align_state_field_comparison_20260608/tables/` and `most_comparable_fem_pidl_deep_dive_20260608/tables/`. |
| Chapter 5 future-work roadmap and architecture diagrams | `SCHEMATIC` | `report_snapshot/Chapter5/Figs/PDF/` | `report_snapshot/Chapter5/Figs/source/c5_wp3_technical_roadmap.tex` and Overleaf figure scripts | These are proposals, not completed experimental evidence. |

## Provenance warning for the two historical plot scripts

`historical_plot_scripts/generate_figs_pidl_fem.py` and
`generate_figs_sn_full.py` are the best-available working copies found in the
shared checkout. At packaging time the first script differed from its last
committed 2026-04-16 version. Its SHA-256 is recorded in `SHA256SUMS`, but an
exact clean Git commit identity for the working copy is not claimed. Therefore
the frozen report PDFs, not a newly rerun plot, are authoritative for PPT use.

## Raw-data escalation route

If Haofan needs to recompute a full-field figure rather than reuse/restyle it,
request the named raw archive from Wennie. Do not substitute a newer experiment
or infer the missing field from a compact table.

