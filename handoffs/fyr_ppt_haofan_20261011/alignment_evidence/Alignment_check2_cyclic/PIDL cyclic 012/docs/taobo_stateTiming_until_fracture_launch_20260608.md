# Taobo stateTiming until-fracture launch - 2026-06-08

## Purpose

Run the strict FEM-mesh PIDL stateTiming cases on Taobo GPU until confirmed fracture, retaining state-timing fields and gradient-balance diagnostics.

These are producer runs. No PIDL training was run on Mac.

## Code snapshot

- Local source worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.codex/worktrees/pidl-state-timing-diagnostic`
- Commit recorded for provenance: `5fa9dd6638f4d0239014a160b4b147c3a94878ea`
- Branch: `codex/pidl-state-timing-diagnostic`
- Sync mode: Mac rsync snapshot
- Remote run root: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640`
- Remote code root: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/code`
- Remote provenance file: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/code/RUN_PROVENANCE.txt`

Note: the local worktree had one dirty documentation file, `docs/pidl_experiment_result_check_protocol_2026-06-01.md`. Runner/core files passed py_compile locally and remotely.

## Failed setup attempts

Two launch attempts exited before training:

1. Long `--tag` made the generated archive directory component exceed the filesystem filename limit.
2. Short-tag default-pretrain launch failed because `meshed_geom1.msh` is absent in the synced strict FEM-mesh snapshot.

The active runs below use a short tag and `--pretrain-mode off`, matching prior strict FEM-mesh stateTiming protocol runs on Taobo.

## Active runs

### one-peak stateTiming until fracture

- Status at launch check: running, reached `idx: 0`
- GPU: `2`
- PID: `3457226`
- Log: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/logs/stateTiming_onepeak_untilFrac_u012_N100_seed1_pretrainoff.log`
- Archive root: `/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/one_peak`
- Generated archive name includes:
  `Nphys100_Nstep100`, `stateTiming_active_degraded`, `histUpdate-post_fit`, `onepeak`, `pretrain-off`
- Command:

```bash
CUDA_VISIBLE_DEVICES=2 \
PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/one_peak \
/usr/bin/python3 -u run_fem_mesh_state_timing_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag s \
  --history-driver active_degraded \
  --history-update-timing post_fit \
  --state-cycles 0,1,2,3,20,40,60,69,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,99 \
  --gradient-balance \
  --gradient-cycles 0,1,2,3,20,40,60,69,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,99 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --pretrain-mode off
```

### FEM-like substep stateTiming until fracture

- Status at launch check: running, reached `idx: 0`
- GPU: `3`
- PID: `3457227`
- Log: `/mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/logs/stateTiming_substeps025_untilFrac_u012_Nphys120_seed1_pretrainoff.log`
- Archive root: `/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/substeps025`
- Generated archive name includes:
  `Nphys120_Nstep600`, `stateTiming_active_degraded`, `histUpdate-post_fit`, `substeps_0.25-0.5-0.75-1-0`, `pretrain-off`
- Command:

```bash
CUDA_VISIBLE_DEVICES=3 \
PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/substeps025 \
/usr/bin/python3 -u run_fem_mesh_state_timing_umax.py 0.12 \
  --n-cycles 120 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag s \
  --history-driver active_degraded \
  --history-update-timing post_fit \
  --substeps 0.25,0.5,0.75,1,0 \
  --state-cycles 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,48,49,98,99,198,199,298,299,343,344,368,369,398,399,423,424,448,449,473,474,498,499,523,524,548,549,573,574,598,599 \
  --gradient-balance \
  --gradient-cycles 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,48,49,98,99,198,199,298,299,343,344,368,369,398,399,423,424,448,449,473,474,498,499,523,524,548,549,573,574,598,599 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --pretrain-mode off
```

## Monitoring commands

```bash
ssh -F /dev/null drtao@172.16.100.2 "ps -p 3457226,3457227 -o pid,etime,stat,cmd"
ssh -F /dev/null drtao@172.16.100.2 "nvidia-smi pmon -c 1"
ssh -F /dev/null drtao@172.16.100.2 "tail -80 /mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/logs/stateTiming_onepeak_untilFrac_u012_N100_seed1_pretrainoff.log"
ssh -F /dev/null drtao@172.16.100.2 "tail -80 /mnt/data2/drtao/wennie/pf_stateTiming_until_fracture_5fa9dd6_20260608_004640/logs/stateTiming_substeps025_untilFrac_u012_Nphys120_seed1_pretrainoff.log"
```

## Completion update

Checked at Taobo time `2026-06-08 09:15 CST`.

- `stateTiming_onepeak_untilFrac_pretrainoff` completed.
  - First fracture detected: `idx/cycle 82`.
  - Confirmed stop: `idx/cycle 85`.
  - Boundary damage at detection: `alpha_bdy=1.0000`, `N_bdy>0.95=20`.
  - State-timing artifacts: 49 files in `pidl_state_timing/`.
  - Gradient artifacts: `gradient_balance/energy_gradient_balance.csv` present.
- `stateTiming_substeps025_untilFrac_pretrainoff` completed.
  - First fracture detected: `idx 408`, corresponding to the peak substep of physical cycle about `81.6` (`408/5`).
  - Confirmed stop: `idx 411`, physical cycle about `82.2` (`411/5`).
  - Boundary damage at detection: `alpha_bdy=0.9992`, `N_bdy>0.95=20`.
  - State-timing artifacts: 103 files in `pidl_state_timing/`.
  - Gradient artifacts: 69 rows in `gradient_balance/energy_gradient_balance.csv`.

Important caveat: the substep state-timing export list retained nearby checkpoints at `398/399` and would next retain `423/424`, but the run stopped at `411`. Therefore the run has event-window training outputs/checkpoint-related files through the stop step, but it does not have explicit `pidl_state_timing/*.npz` exports exactly at `408-411`. A small follow-up posthoc export or targeted resume/rerun is needed if exact event-state `pre_fit/post_fit/post_history_refresh` `.npz` files are required.
