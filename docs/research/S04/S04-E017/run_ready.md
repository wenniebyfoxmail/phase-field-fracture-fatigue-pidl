# E017 producer preparation 2026-10-12

- authorized exact commit: ed3adcef880e711aed175578a7da7861cfb746aa
- producer: Taobo / GPUServer8
- active root: /mnt/data2/drtao/wennie/S04-E017-alpha-ed3adce-20261012T170600Z-bundle
- detached dispatcher PID:820617
- current execution state: RUNNING; all four SHA and remote validate-only checks passed
- plan:12 fresh state-alpha runs, sequential GPU0, seed7, final10000 only
- GPU0 readiness snapshot:1065MiB resident use, utilization0%; existing services preserved
- archive roots: /mnt/data2/drtao/pidl_archives/<root>-R001..R012-<state>-a<ratio>-s7
- logging: active root/logs/dispatcher.log and one per-run log
- transfer: c20/c60/c83 copied from original E013 verified inputs; c40 transfer complete and exact SHA verified
- snapshot route: git bundle from Mac, exact reviewed commit; no source change
- startup:wait at most1800 seconds for exact commit and all4 expected SHA checks;
  then require clean code, /mnt/data2 mounted, GPU0 free memory>8192MiB, CUDA health,
  and four reference --validate-only checks before first optimizer step.
- no training/scientific outcome is claimed from the dispatcher start.

The original GitHub-clone preparation root without '-bundle' is retained. Its
redundant local c40 transfer was cancelled after checking its exact cmdline,
elapsed time and cwd; no producer training was entered there and no remote
service was stopped. The active transfer/dispatcher use only the bundle root.
No automatic retry of a numerical result; missing preparation exits as a
preparation failure. No E018 training is chained to this dispatcher.

First training unit R001 c20s4 alpha.5 seed7, PID826874, GPU0~2776MiB/~95%
utilization. This is live execution evidence only; all12 final outcomes pending.
