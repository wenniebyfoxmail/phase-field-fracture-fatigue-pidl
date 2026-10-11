# S09-E006-R002 producer receipt

- Run ID: `S09-E006-R002_ae01790_20261012T062400CST`
- Producer: Taobo `GPUServer8`
- PID: `3706152`
- GPU: physical GPU 0 via `CUDA_VISIBLE_DEVICES=0`
- Exact commit: `ae01790c10c644657fe9a8aea2f1087505144959`
- Producer tree: clean at launch
- Protocol: `v2-gradient-balanced-pareto-rescue`
- Runtime: 105.704 s
- Peak CUDA allocation: 659,393,024 bytes
- Execution: succeeded
- Producer-reported scientific status: supports; requires Evidence Ready review
- Remote root:
  `/mnt/data2/drtao/wennie/S09-E006-R002_ae01790_20261012T062400CST`
- Remote archive:
  `/mnt/data2/drtao/pidl_archives/S09-E006-R002_ae01790_20261012T062400CST`
- Local retrieval:
  `local_archive/experiments/S09-E006/runs/S09-E006-R002/`

Frozen identities all matched:

| Asset | SHA-256 |
|---|---|
| E004 packet | `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed` |
| step-300 checkpoint | `1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e` |
| E004 sequence | `ee1884ae1a81813334641faaacc0e44151d23cb4f36e35948ec656fd20c976f5` |
| E004 reference metrics | `202be98d2be46c702196a7f05d4571789097a297aea3f99870dd66379ae6e62f` |

All three arms completed 700 updates from identical start model and optimizer
hashes.  The seven-value data-only replay gate passed.  All ten retrieved
output files passed the remote SHA-256 manifest; key hashes include:

| File | SHA-256 |
|---|---|
| `metrics.json` | `3d9373546932d17720b74e46430856495891c442282681e185dbfe9812589b72` |
| `receipt.json` | `9a9a160d6a4b52471b57e62d469fe23c185c883b0b0658a6115c097271ccc20e` |
| `updates.csv` | `f1533028453d0501629b1e579deb80ed018c0131dd465f2e9a7f76dfbda8d7d0` |
| `final_fields.npz` | `d55ac5dc9880b3243f72c2f44530caf8bc70c4464ebf09858a815fec23435955` |
| `balanced_beta_0p25_final.pt` | `1abb0e73a576349924341a46209d158482123478448e8bee333c713a5ad18b2a` |
