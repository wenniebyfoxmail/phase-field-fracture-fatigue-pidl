# S09-E006-R001 preflight-failure receipt

- Run ID: `S09-E006-R001_ae01790_20261012T062213CST`
- Producer: Taobo `GPUServer8`, intended physical GPU 0
- Commit: `ae01790c10c644657fe9a8aea2f1087505144959`
- Status: **PREFLIGHT_FAIL**
- Optimizer updates: 0
- Training loop entered: no
- Output directory/receipt/checkpoint created: no
- Log:
  `local_archive/experiments/S09-E006/runs/S09-E006-R001/logs/pareto_rescue.log`
- Remote archive:
  `/mnt/data2/drtao/pidl_archives/S09-E006-R001_ae01790_20261012T062213CST`

The preceding audit-only import created two task-owned, untracked
`__pycache__` directories.  The runner's clean-checkout guard rejected the
checkout before output creation.  Only those caches were removed.  The
independent reviewer authorised one fresh R002 replacement; R001 is not a
scientific result or a completed execution.
