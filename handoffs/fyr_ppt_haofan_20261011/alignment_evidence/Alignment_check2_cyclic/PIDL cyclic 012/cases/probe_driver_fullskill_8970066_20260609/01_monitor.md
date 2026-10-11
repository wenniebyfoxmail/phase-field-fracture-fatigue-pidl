# Monitor

Status: running corrected aligned-coarse Taobo rerun.

## Launch Record

- run_id: `pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404`
- commit: `8970066`
- branch: `codex/m2s-framework-validation`
- sync mode: `mac-git-archive-runtime-subset` from commit `8970066`
- remote code dir: `/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404/code`
- archive root: `/mnt/data2/drtao/pidl_archives/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404`
- gpu: `2`
- pid: `3273931`
- command: `/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404/launch_probe_driver_fullskill_alignedcoarse.sh`
- log: `/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404/logs/probe_driver_fullskill_alignedcoarse_u012.log`
- launch time: `2026-06-10T00:44:58+08:00` / `2026-06-09T17:44:58+01:00`

## Snapshots

### 2026-06-09 17:23 London

Taobo initial health check succeeded:

- host: `GPUServer8`
- `/mnt/data2`: 2.1T free
- CUDA available with 8 GPUs
- GPU memory used: GPU0 1570 MiB, GPU1 400 MiB, GPU2-6 4 MiB, GPU7 3530 MiB

GitHub clone to the first attempted remote directory started but remained in clone/index-pack while later SSH probes timed out. The local SSH wrapper was stopped. No training PID was created.

### 2026-06-09 17:35 London

The first actual launch from runtime-subset snapshot failed immediately before training:

```text
FileNotFoundError: meshed_geom1.msh
```

Cause: `meshed_geom1.msh` is git-ignored by `*.msh`, but it is needed as the coarse/pretraining mesh. This was a launch packaging issue, not a training result.

Action:

- synced local `upload code/SENS_tensile/meshed_geom1.msh` to remote `SENS_tensile/`,
- cleared the failed empty archive under this run's own archive root,
- relaunched on the same GPU.

### 2026-06-09 17:37 London

Corrected relaunch:

```text
PID=3263353
GPU=2
log=/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_8970066_20260609_173409/logs/probe_driver_fullskill_u012_rerun.log
```

Health snapshot:

```text
ps: PID 3263353 elapsed 00:11, STAT S
GPU2: 2770 MiB used, 42% util
```

Log confirms:

- `history driver = current_active`
- `reduction = probe_g_mean`
- `elem diag = [0, 3, 4, 8, 9, 13, 14, 98, 99, 198, 199, 298, 299, 343, 344]`
- `gradient diag = pre-history-refresh every step`
- coarse mesh resolved to remote `meshed_geom1.msh`

### 2026-06-09 17:39 London

Follow-up health snapshot:

```text
ps: PID 3263353 elapsed 01:59, STAT S
GPU2: 3394 MiB used, 36% util
```

Archive root has started:

```text
/mnt/data2/drtao/pidl_archives/pf_probe_driver_fullskill_8970066_20260609_173409/
  probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep600_U0.12_probeDriver_softHist0_stateTiming_current_active_probe_g_mean_s0.25-0.5-0.75-1-0/
    model_settings.txt
    TBruns/events.out.tfevents...
```

No cycle logs yet; still early setup/pretraining. This is expected at this elapsed time.

### 2026-06-09 17:43 London

User caught a strict-alignment issue: the previous corrected relaunch used
`meshed_geom_fem_soft_hist0.msh` for main training but still used
`meshed_geom1.msh` as the coarse/pretraining mesh. That is not acceptable for
the strict FEM-mesh rerun because pretraining can bias the initial NN field.

Action:

- verified PID `3263353` cwd/cmdline,
- stopped PID `3263353` while it was still early,
- relaunched a new clean run with both:
  - `--mesh-file meshed_geom_fem_soft_hist0.msh`
  - `--coarse-mesh-file meshed_geom_fem_soft_hist0.msh`

### 2026-06-09 17:45 London

Corrected aligned-coarse launch:

```text
run_id=pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404
PID=3273931
GPU=2
main_mesh=meshed_geom_fem_soft_hist0.msh
coarse_mesh=meshed_geom_fem_soft_hist0.msh
```

Health snapshot:

```text
ps: PID 3273931 elapsed 00:19, STAT S
GPU2: 4038 MiB used, 51% util
```

Log confirms both meshes are aligned:

```text
FEM mesh    = .../meshed_geom_fem_soft_hist0.msh
coarse mesh = .../meshed_geom_fem_soft_hist0.msh
```

### 2026-06-09 18:24 London

Heartbeat check. The heartbeat instruction still referenced obsolete PID
`3263353`; that run was intentionally stopped. Correct active PID is `3273931`.

Health snapshot:

```text
ps: PID 3273931 elapsed 39:50, STAT S
GPU2: 4056 MiB used, 61% util
old PID 3263353: not running
```

Latest log state:

```text
idx: 248; displacement/amplitude: 0.12
```

Recent diagnostics show the full-skill instrumentation is active:

```text
[GradientDiagnostics step 243 pre-history-refresh]
E=(2.767100e-03, 4.908454e-03, 4.233103e-06)
grad=(5.839927e+01, 6.843671e+01, 4.439552e+04)
```

The run has not completed yet, so no download/analysis was started.

### 2026-06-09 19:09 London

Heartbeat check: corrected aligned-coarse run completed successfully.

Process/GPU snapshot:

```text
PID 3273931: not running
GPU2: 4 MiB used, 0% util
```

Final log state:

```text
[Fracture?] cycle 388: alpha_bdy=1.0001 >= 0.95 (20 nodes). Continuing 3 confirmation cycles...
[Fracture confirmed] Stopping at cycle 391. First detected at cycle 388.
[train_exit] status=0 date=2026-06-10T01:45:18+08:00
[posthoc_exit] status=0 date=2026-06-10T01:45:40+08:00
```

Mapped-state export succeeded for:

- `state0_initial_unloaded_prehistory`
- c1/c2/c3/c20/c40/c60/c69 peak and unloaded states

Starting download and local analysis.

### 2026-06-09 19:23 London

Download and analysis completed.

Local archive status:

- diagnostic mirror size: about `2.7G`
- logs downloaded: `logs/probe_driver_fullskill_alignedcoarse_u012.log`
- provenance downloaded: `run_workspace/JOB_RECORD.txt`, `RUN_PROVENANCE.txt`, launch script

Capability verification:

- mapped-state NPZ files: `15`
- element diagnostic NPZ files: `19`
- gradient trace: `best_models/energy_gradient_terms_vs_cycle.npy`, shape `(392, 7)`
- alpha snapshots: `24` NPY files
- checkpoints present: `785`

Analysis regenerated using:

```text
/Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/scripts/regenerate_alignment_analysis.py
```

Generated:

- scalar histories
- gradient balance
- selected PIDL field montage
- FEM/PIDL residual fields for damage/history/degradation
- FEM/PIDL residual fields for energy drivers
- FEM/PIDL residual fields for strain/stress
- c1 fatigue-driver mask audit
- tables and `analysis/decision.md`

Important script fix during this heartbeat:

- the reusable analysis script had old hard-coded event steps `403/406`;
- patched it to infer event diagnostics from available `element_fields_cycle_*.npz`;
- for this aligned-coarse run, first boundary hit is step `388`, confirmed stop is step `391`.

Decision verdict: `mixed`.
