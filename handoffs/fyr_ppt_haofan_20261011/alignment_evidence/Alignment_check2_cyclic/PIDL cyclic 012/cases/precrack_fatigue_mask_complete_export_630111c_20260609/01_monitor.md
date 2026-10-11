# Monitor

Status: clean rerun finished on Taobo; full archive downloaded locally.

## Local Case

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/PIDL cyclic 012/cases/precrack_fatigue_mask_complete_export_630111c_20260609
```

## Remote Job

First attempt failed before training because the git checkout contains only
`meshed_geom_fem_soft_hist0.msh`, while the default pretraining mesh setting
looked for missing `meshed_geom1.msh`.

Failed setup-only attempt:

```text
run_id: pf_precrack_fatigue_mask_complete_630111c_20260609_121100
pid: 2276352
log: /mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_complete_630111c_20260609_121100/logs/precrack_fatigue_mask_complete_export_u012.log
failure: FileNotFoundError: meshed_geom1.msh
```

Second attempt was stopped deliberately during setup because it used the FEM
main mesh as the pretraining mesh. It was alive, but less comparable to the
previous precrack-mask run:

```text
run_id: pf_precrack_fatigue_mask_complete_630111c_20260609_121700
pid: 2278473
action: stopped after cwd/cmdline verification
reason: relaunch with restored meshed_geom1.msh pretraining mesh
```

Active clean rerun:

```text
run_id: pf_precrack_fatigue_mask_complete_630111c_20260609_122200
commit: 630111c6bc86a56003ec584b7a366166921c39d4
branch: codex/m2s-framework-validation
sync mode: remote-copy-from-previous-git-clone-plus-mesh-rsync
remote code dir: /mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_complete_630111c_20260609_122200/code
archive root: /mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_complete_630111c_20260609_122200
gpu: 2
pid: 2283945
command: CUDA_VISIBLE_DEVICES=2 PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_complete_630111c_20260609_122200 /usr/bin/python3 -u run_fem_mesh_precrack_fatigue_mask_umax.py 0.12 --n-cycles-physical 120 --seed 1 --mesh-file meshed_geom_fem_soft_hist0.msh --history-driver-mode current_active --fracture-confirm-cycles 3 --plot-every 20
log: /mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_complete_630111c_20260609_122200/logs/precrack_fatigue_mask_complete_export_u012.log
launch time: Tue Jun  9 12:22 PM CST 2026
initial health: PID alive after launch, GPU 2 active, log shows coarse mesh meshed_geom1.msh and main mesh meshed_geom_fem_soft_hist0.msh
```

## Finish Snapshot

Checked on 2026-06-09.

```text
PID 2283945: no longer running
first boundary hit: step 403
confirmed stop: step 406
final alpha_bar_max: 2.7180
final f_min: 0.0966
final f_mean: 0.8900
final crack tip: (0.5000, 0.0000)
final alpha_max@right_boundary: 1.0001
final N_bdy>0.95: 20
final Kt at step 406: 82.45
```

Important gradient snapshot from final step:

```text
step 406
E_el=3.1607738e-06
E_d=5.6196349e-03
E_hist=4.3637092e-06
grad_E_el=3.425286e+03
grad_E_d=5.824216e+01
grad_E_hist=7.387356e+04
```

The complete-export diagnostics exist locally after archive resume:

```text
best_models/energy_gradient_terms_vs_cycle.npy shape = (407, 7)
element_diagnostics_precrack_fatigue_mask/element_fields_cycle_0406.npz
final element diagnostic keys include eps_xx_elem, eps_eq_elem,
sigma_raw_principal_1_elem, sigma_effective_principal_1_elem,
psi_raw_elem, psi_active_elem, and E_hist_elem.
```

Download status:

```text
logs/JOB_RECORD copied locally
full archive remote size: 2.5G, 1346 files
local raw_archive after resumed rsync: 2.8G, 1347 files
local count includes one metadata file beyond the remote file count
verified local: checkpoint_step_406.pt
verified local: energy_gradient_terms_vs_cycle.npy shape = (407, 7)
verified local: element_fields_cycle_0406.npz
```
