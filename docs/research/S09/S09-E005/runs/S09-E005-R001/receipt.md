# S09-E005-R001 receipt

- Status: execution succeeded; retrieval verified; independent Evidence Ready
  PASS after the round-1 evidence-integrity blockers were corrected
- Producer: Taobo `GPUServer8`
- Run time: 2026-10-12 05:54 CST (2026-10-11 22:54 Europe/London)
- PID: `3667270`
- GPU: physical GPU 0 via `CUDA_VISIBLE_DEVICES=0`
- Exact execution commit: `79f238e0cd2ddd7a31d994f79c6d05410fd8151a`
- Producer tree: clean at launch
- Packet SHA-256:
  `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed`
- Checkpoint SHA-256:
  `1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e`
- Remote root:
  `/mnt/data2/drtao/wennie/S09-E005-R001_79f238e_20261012T055500CST`
- Output: `<remote root>/S09-E005-R001_79f238e_20261012T055500CST_output`
- Log: `<remote root>/logs/gradient_audit.log`
- Remote archive:
  `/mnt/data2/drtao/pidl_archives/S09-E005-R001_79f238e_20261012T055500CST`
- Local retrieval:
  `local_archive/experiments/S09-E005/runs/S09-E005-R001/`
- Runtime: 2.125 s; peak CUDA allocation 652,857,856 bytes
- Output completeness: 16/16 states, finite PASS, declared blocks PASS
- No-update identity: PASS; model state hash unchanged and checkpoint file hash
  unchanged

Retrieved output hashes:

| File | SHA-256 |
|---|---|
| `gradient_audit.json` | `bd9d441d5a047f4a338ec9dbfaa32f4524d47a8e5b396d293d98a7144676b6bf` |
| `gradient_audit.csv` | `c205e791b929017f762381f07234e3cabbdd858a11d7bfb02164d1fd0cb82375` |
| `receipt.json` | `4864bd32c01acd0ae983d4b67a8c4edc27d40d350442474c5bfa7a62c9f9e4c6` |
| `gradient_audit.log` | `e34177e18d50689b1d96918491a44e9b6978f614700378950da8166b9d751236` |

Independent review: `../../evidence_review.md`.  The corrected evidence archive
SHA-256 is
`e4c187346e720e80aa4c1034de7c88b5eb4484bb29d4e1491d0bbefc1522d977`.
