# Monitor: oracle_delta_alpha_bar_20260609

Status: stopped on Taobo; downloaded and analyzed.

## 2026-06-09 18:27 BST / 2026-06-10 01:27 CST

- run_id: `oracle_triplet_8970066_20260609_182141`
- base commit: `897006619690a4771bad2703db14891014c8b8cb`
- sync mode: Mac rsync minimal overlay, recorded in remote `RUN_PROVENANCE.txt`
- remote code dir: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/code`
- archive root: `/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141`
- runner cwd: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/code/SENS_tensile`
- command: `CUDA_VISIBLE_DEVICES=5 PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141 python -u run_fem_mesh_oracle_field_umax.py 0.12 --oracle-kind delta_alpha_bar --n-cycles-physical 80 --fem-data-dir /mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28`
- gpu: 5
- pid: `3326370`
- log: `/mnt/data2/drtao/wennie/oracle_triplet_8970066_20260609_182141/logs/delta_alpha_bar.log`
- first health check: process running; log printed strict oracle settings; GPU memory about 2.8 GB and utilization about 42%.

## 2026-06-09 18:39 BST

- `ps`: PID `3326370` running, elapsed about `11:34`, state `Rl`.
- log tail: reached step `48` after completing step `47`.
- current scalar trace from log: at step `47`, `alpha_bar_max=1.6548e+00`, `f_min=0.2154`, `f_mean=0.9986`, crack-tip length about `0.0120`, no right-boundary fracture nodes.
- note: this is a monitor snapshot only; do not treat as final verdict.

## 2026-06-09 19:35 BST

- `ps`: PID `3326370` still running, elapsed about `01:08:26`, state `Rl`.
- log tail: reached PIDL step `372`; no right-boundary fracture nodes in the latest visible tail.
- latest visible trace at step `371`: `alpha_bar_max=1.9532e+01`, `f_min=0.0025`, `f_mean=0.9200`, crack-tip length `0.4600`, `alpha_max@bdy=-0.0034`, `N_bdy>0.95=0`.
- required element-diagnostic state files and stress/strain keys are present in the live remote archive; see `03_data_capability.md`.
- note: this is a monitor snapshot only; final local download and comparison remain pending.

## 2026-06-09 19:44-20:40 BST

- `ps`: PID `3326370` no longer active.
- log tail: reached PIDL step `399`, the final step for `Nstep=400`; no boundary fracture was visible in the final tail.
- final visible trace at step `399`: `alpha_bar_max=1.9532e+01`, `f_min=0.0025`, `f_mean=0.9200`, crack-tip length `0.4700`, `alpha_max@bdy=0.2599`, `N_bdy>0.95=0`.
- completed archive download into `raw_archive/`, copied log and provenance into `logs/` and `run_workspace/`.
- regenerated skill analysis package from local `raw_archive/`.
- final case verdict recorded in `analysis/decision.md`: `negative`.
