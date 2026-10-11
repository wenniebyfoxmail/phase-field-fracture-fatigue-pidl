# Data Capability

Status: local archive resumed and verified.

This is a retrospective audit of the case folder on 2026-06-09. The Taobo run
completed, and the large raw archive was resumed from Taobo into the local
`raw_archive/` folder after the first workflow pass.

## Local Archive Audit

| Capability | Local status | Evidence |
|---|---:|---|
| complete log | present | `logs/precrack_fatigue_mask_complete_export_u012.log` |
| run records | present | `run_workspace/JOB_RECORD.txt`, `run_workspace/JOB_RECORD_final.txt` |
| alpha snapshots | present | includes scheduled and dense near-event snapshots through cycle 406 |
| scalar histories | present | `best_models/*_vs_cycle.npy`, plus `analysis/tables/pidl_gradient_trace.csv` |
| selected state reductions | present | `analysis/tables/pidl_selected_state_reductions.csv` |
| PIDL-only figures | present | `analysis/figures/pidl_*.png`, `analysis/figures/pidl_*.pdf` |
| final checkpoint | present | `best_models/checkpoint_step_406.pt` |
| final element diagnostics NPZ | present | `element_diagnostics_precrack_fatigue_mask/element_fields_cycle_0406.npz` |
| raw state-timing element fields | present | selected states and dense near-event NPZ files |
| strain/stress fields | present | final NPZ contains required mechanics fields |
| gradient diagnostics | present | `best_models/energy_gradient_terms_vs_cycle.npy`, shape `(407, 7)` |
| FEM/PIDL residual inputs in one place | ready for analysis | FEM reference and PIDL raw NPZ are both local |

Local raw archive size at audit time:

```text
raw_archive file count: 1347
raw_archive size: 2.8G
remote archive file count: 1346
remote archive size: 2.5G
```

The one-file count difference is explained by local metadata such as `.DS_Store`.

## Remote Verification Carried Forward

The remote verification in `02_download_verification.md` has now been checked
locally:

```text
best_models/checkpoint_step_406.pt: present
best_models/energy_gradient_terms_vs_cycle.npy: present, shape (407, 7)
element_diagnostics_precrack_fatigue_mask/element_fields_cycle_0406.npz: present
```

The final diagnostic NPZ includes the complete export fields:

```text
eps_xx_elem
eps_eq_elem
sigma_raw_principal_1_elem
sigma_effective_principal_1_elem
psi_raw_elem
psi_active_elem
E_hist_elem
```

## Analysis Consequence

The current local package now supports the full FEM/PIDL residual comparison in
principle. The existing `analysis/` figures remain PIDL-only because they were
generated before this archive resume; the FEM/PIDL residual package still needs
to be run against the local FEM reference.
