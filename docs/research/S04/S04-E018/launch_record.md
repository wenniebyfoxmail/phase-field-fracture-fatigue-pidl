# E018 r2 Run Ready and launch — 2026-10-13

Status: **RUNNING** (live process/GPU evidence; final metrics pending).

- Exact reviewed producer commit: e67d9701419fbb891ce570edd3530bf68aae5f4e, detached clean checkout from verified Mac git bundle.
- Prior gates: r2 planning PASS; exact-commit Code Ready PASS; E017 Evidence PASS on pinned result commit d489d0ed1c59e82e68c0d676fc87e69115635c2d.
- Producer: Taobo drtao@172.16.100.2; root `/mnt/data2/drtao/wennie/S04-E018-global-local-e67d970-20261013T111326Z`.
- Submitted UTC: 2026-10-13T11:19:15Z; detached dispatcher PID1977956.
- First run: `S04-E018-global-local-e67d970-20261013T111326Z-R001-c20s4-control-s7`; training PID1977967.
- Initial health: dispatcher alive after68s, actual reviewed runner active; GPU0 4632MiB used /19450MiB free,95% utilization. Subsequent first1000-step monitor is finite: full UV=.01856076, damage conditional=.11197712, background conditional=.01206821, sampled loss=.0003110791; GPU97% after139s. This intermediate checkpoint does not vote on scientific success.
- Frozen matrix: c20/c60/c83 × control/localized, seed7, alpha.7 (11469 damage/4915 background),10000steps, final-only. All six runs fresh; no warmstart, checkpoint substitution or scientific retry.
- Live preflight: `/`96G, `/mnt/data2`670G, `/mnt/data3`914G available; primary mount verified; GPU0 had2682MiB used and0% utilization with>8GiB free. Other processes preserved.
- Runtime: Torch2.7.0+cu126, RTX4090, CUDA available.
- All three exact NPZ SHA hashes matched the frozen references; `--validate-only` PASS on c20/c60/c83 with reference rho_u 4.939e-11/4.802e-11/4.406e-11. Validation does not enter training.
- Explicit `CUDA_VISIBLE_DEVICES=0`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`; task-owned TMPDIR/XDG/TORCH cache under root/cache.
- Sequential detached dispatcher logs: root/logs/dispatcher.log, each run root/logs/<run_id>.log; outputs root/runs/<run_id>; archives `/mnt/data2/drtao/pidl_archives/<run_id>`.
- Six ordinals: R001 c20control, R002 c20localized, R003 c60control, R004 c60localized, R005 c83control, R006 c83localized. Fresh output/archive checks precede each launch; fail-closed shell exits on failure.
- After all6, frozen aggregator runs against all3 exact references and reviewed code commit; no automatic producer retry/budget extension.

## Commands

Dispatcher source is preserved next to this record. Launch was `nohup bash <root>/dispatcher.sh > <root>/logs/dispatcher.log 2>&1 < /dev/null &`; SSH disconnect does not stop training. A run enters the reviewed runner with `--state <state> --arm <arm> --alpha 0.7 --seed 7 --reference <root>/inputs/<state>.npz --out <root>/runs/<id> --run-id <id> --expected-commit e67d9701419fbb891ce570edd3530bf68aae5f4e --archive-root /mnt/data2/drtao/pidl_archives/<id> --log-path <root>/logs/<id>.log --device cuda`.

## Next completion audit

Require all6 final receipts, checkpoint/archive/prediction identities, final-step monitoring agreement, matched initialization and sampling, full/damage/background errors and branch magnitudes/cancellation. Compare matched arms and frozen E017 alpha.7 context; ratios cannot rescue a failed absolute gate. E018 is a representation package comparison, not individual causal separation of coordinates/window/branches. No E018 success, coupled FEM reproduction, Stage2 or teacher qualification yet.

## Completion snapshot 2026-10-13

All6 final10000 completed; latest finish UTC 2026-10-13T13:25:29.390750+00:00. Dispatcher exited MATRIX_EXECUTION_COMPLETED. Frozen aggregator rerun returns6valid/no missing/no integrity errors. Local independent saved-array regional recomputation and actual remote output/archive checkpoint audit PASS. Primary GLOBAL_LOCAL_THREE_STATE_UV_FIT_SCREEN_FAIL, useful matched-control component improvement retained; see result.md. Evidence review pending at this snapshot.
