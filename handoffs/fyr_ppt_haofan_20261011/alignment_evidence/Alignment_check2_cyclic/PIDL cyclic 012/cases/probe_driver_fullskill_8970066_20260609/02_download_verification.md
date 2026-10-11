# Download Verification

Status: complete enough for analysis.

## Local Paths

- case: `/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/PIDL cyclic 012/cases/probe_driver_fullskill_8970066_20260609`
- raw archive: `raw_archive/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep600_U0.12_probeDriver_softHist0_stateTiming_current_active_probe_g_mean_s0.25-0.5-0.75-1-0`
- logs: `logs/probe_driver_fullskill_alignedcoarse_u012.log`
- provenance: `run_workspace/JOB_RECORD.txt`, `run_workspace/RUN_PROVENANCE.txt`, `run_workspace/launch_probe_driver_fullskill_alignedcoarse.sh`

## Remote Provenance

- remote root: `/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404`
- archive root: `/mnt/data2/drtao/pidl_archives/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404`
- commit: `8970066`
- branch: `codex/m2s-framework-validation`
- GPU: `2`
- PID: `3273931`
- sync mode: `mac-git-archive-runtime-subset`

## Download Notes

The first full `rsync` pulled the large checkpoint-heavy archive first and was stopped after the required scalar/gradient/checkpoint/element-diagnostic files had arrived but before mapped-state fields. A targeted diagnostic sync then downloaded `mapped_state_fields_skill/`, logs, and run provenance.

This means the local archive is not claimed as a byte-for-byte full mirror of the remote 2.5 GB archive, but it contains the required analysis products.

## Verification

- local raw archive size: about `2.7G`
- logs size: about `160K`
- run workspace provenance size: about `12K`
- mapped-state manifest found: yes
- mapped-state summary found: yes
- mapped-state NPZ files: `15`
- element diagnostic NPZ files: `19`
- gradient diagnostic file: `best_models/energy_gradient_terms_vs_cycle.npy`
- alpha snapshot NPZ files: `24`
- checkpoint files found: `785`

## Final Log Check

The log confirms normal completion:

```text
[Fracture?] cycle 388: alpha_bdy=1.0001 >= 0.95 (20 nodes). Continuing 3 confirmation cycles...
[Fracture confirmed] Stopping at cycle 391. First detected at cycle 388.
[train_exit] status=0 date=2026-06-10T01:45:18+08:00
[posthoc_exit] status=0 date=2026-06-10T01:45:40+08:00
```

## Missing Or Qualified Artifacts

- The local archive is a diagnostic mirror, not a verified complete byte-for-byte mirror of every remote checkpoint/log artifact.
- Mapped-state NPZ files contain `psi_raw_elem` and `psi_active_elem`; the exact `psi_history_driver_elem` key is present in element diagnostics at the exported diagnostic steps, not in mapped-state files.
