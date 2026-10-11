# Monitor: oracle_raw_pidl_g_20260609

Status: stopped on Taobo; final download/analysis pending.

## 2026-06-09 18:27 BST / 2026-06-10 01:27 CST

- run_id: `oracle_triplet_8970066_20260609_182141`
- base commit: `897006619690a4771bad2703db14891014c8b8cb`
- sync mode: Mac rsync minimal overlay, recorded in remote `RUN_PROVENANCE.txt`
- remote code dir: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/code`
- archive root: `/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141`
- runner cwd: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/code/SENS_tensile`
- command: `CUDA_VISIBLE_DEVICES=3 PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141 python -u run_fem_mesh_oracle_field_umax.py 0.12 --oracle-kind raw_pidl_g --n-cycles-physical 80 --fem-data-dir /mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28`
- gpu: 3
- pid: `3326368`
- log: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/logs/raw_pidl_g.log`
- first health check: process running; log printed strict oracle settings; GPU memory about 2.8 GB and utilization about 40%.

## 2026-06-09 18:39 BST

- `ps`: PID `3326368` running, elapsed about `11:34`, state `Rl`.
- log tail: reached step `45` after completing unload step `44`.
- current scalar trace from log: at step `44`, `alpha_bar_max=5.6876e+01`, `f_min=0.0003`, `f_mean=0.9915`, crack-tip length about `0.0160`, no right-boundary fracture nodes.
- note: this is a monitor snapshot only; do not treat as final verdict.

## 2026-06-09 19:35 BST

- `ps`: PID `3326368` no longer active.
- log tail: boundary fracture first detected at PIDL step `343`, then confirmed and stopped at step `346`.
- state mapping: step `343` is `c69_peak`; step `344` is `c69_unloaded`.
- final visible trace at step `346`: `alpha_bar_max=8.0804e+03`, `f_min=0.0000`, `f_mean=0.9118`, crack-tip length `0.5000`, `alpha_max@bdy=1.0120`, `N_bdy>0.95=20`.
- required element-diagnostic state files and stress/strain keys are present in the live remote archive; see `03_data_capability.md`.
- note: final local download and state-mapped comparison are still pending.

## 2026-06-09 19:44-20:40 BST

- completed archive download into `raw_archive/`, copied log and provenance into `logs/` and `run_workspace/`.
- regenerated skill analysis package from local `raw_archive/`.
- final case verdict recorded in `analysis/decision.md`: `mixed`.
