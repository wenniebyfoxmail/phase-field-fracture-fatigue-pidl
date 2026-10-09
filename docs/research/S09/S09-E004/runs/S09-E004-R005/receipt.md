# S09-E004-R005 launch receipt

- Status: running
- Producer: Taobo `GPUServer8`
- Start: 2026-10-09 17:52:02 Europe/London
- PID: `4178894`
- GPU: physical GPU 0 via `CUDA_VISIBLE_DEVICES=0`
- Commit: `11fd75d70b18165d6214d50c90adc9c9c9b522a5`
- Producer tree: clean at launch
- Packet SHA-256: `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed`
- Remote root: `/mnt/data2/drtao/wennie/S09-E004-R005_11fd75d_20261009T174900Z`
- Code: `<remote root>/code`
- Output: `<remote root>/output`
- Log: `<remote root>/logs/train.log`
- Archive root: `/mnt/data2/drtao/pidl_archives/S09-E004-R005_11fd75d_20261009T174900Z`
- Retrieval route: Taobo to Mac
- Initial health: process running; GPU 0 at 2,152 MiB and 20%; packet audit,
  receipt and frozen training sequence present.

Command:

```text
CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
python3 -u SENS_tensile/run_s09_equilibrium_operator.py
  --packet <remote root>/input/s09_e004_equilibrium_operator.npz
  --expected-packet-sha256 b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed
  --expected-commit 11fd75d70b18165d6214d50c90adc9c9c9b522a5
  --out <remote root>/output
```

## Preparation attempts

No earlier attempt entered the training loop.

- R001: Taobo-to-GitHub clone failed with TLS receive error.
- R002: complete bundle transfer was stopped after the VPN proved
  impractically slow; packet transfer had not started.
- R003: local clone from the earlier sparse E003 checkout failed on a missing
  Git object.
- R004: the first incremental bundle used a thin delta unavailable in the
  sparse checkout.
- R005: a no-delta incremental bundle restored the reviewed HEAD.  The sparse
  E003 release lacked the unchanged `source/s09_operator.py` working file, so
  that exact reviewed blob was copied separately and verified against Git blob
  `853dc099a9ad4a3b841e003dd0a04b5aeff61122`; `git status --porcelain` was
  empty before launch.
