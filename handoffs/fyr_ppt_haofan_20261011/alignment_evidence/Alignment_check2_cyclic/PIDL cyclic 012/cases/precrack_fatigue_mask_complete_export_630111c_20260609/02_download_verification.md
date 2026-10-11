# Download Verification

Status: complete locally after resumed rsync.

## Remote Archive

```text
remote archive: /mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_complete_630111c_20260609_122200
remote workspace: /mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_complete_630111c_20260609_122200
remote archive size: 2.5G
remote archive file count: 1346
```

## Local Files Present

```text
logs/precrack_fatigue_mask_complete_export_u012.log
run_workspace/JOB_RECORD.txt
run_workspace/JOB_RECORD_final.txt
raw_archive/pfmask_hl8.../best_models/checkpoint_step_406.pt
raw_archive/pfmask_hl8.../best_models/energy_gradient_terms_vs_cycle.npy
raw_archive/pfmask_hl8.../element_diagnostics_precrack_fatigue_mask/element_fields_cycle_0406.npz
```

The large archive rsync was resumed from Taobo and completed locally.

```text
local raw_archive size: 2.8G
local raw_archive file count: 1347
```

The local file count is one higher than the remote count because of local
metadata such as `.DS_Store`.

## Local Verification

Final checkpoint and diagnostics were verified locally:

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

## Finish Result

```text
first boundary hit: step 403
confirmed stop: step 406
final alpha_bar_max: 2.7180
final f_min: 0.0966
final f_mean: 0.8900
final Kt: 82.45
```
