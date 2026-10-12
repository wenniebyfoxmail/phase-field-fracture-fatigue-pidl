# S09-E007-R001-beta025-u0125 producer receipt

- Producer: Taobo `GPUServer8`
- PID: `721785`
- GPU: physical GPU 0 via `CUDA_VISIBLE_DEVICES=0`
- Exact commit: `4b26b6eea41ab433435532ded23b3c463de8d1ff`
- Producer tree: clean at launch
- Protocol: `v2-frozen-beta025-u0125-holdout`
- Runtime: 7.499063 s
- Peak CUDA allocation: 179,020,800 bytes
- Optimizer steps: 0
- Execution: succeeded; 146 durable arm-cycle records; last cycle 73
- Producer scientific status: `positive`, subject to Evidence Ready review
- Remote output: `/mnt/data2/drtao/wennie/S09-E007-R001-beta025-u0125`
- Remote archive: `/mnt/data2/drtao/pidl_archives/S09-E007-R001-beta025-u0125`
- Local retrieval: `local_archive/experiments/S09-E007/runs/S09-E007-R001-beta025-u0125/`
- Separate stdout log: none; the short runner was executed in a foreground SSH
  session and was silent after the launch preflight line. The durable attempt
  marker, receipt and per-cycle JSONL provide execution progress.

Frozen input identities:

| Asset | SHA-256 |
|---|---|
| U0.125 packet | `447c372bb675521ba8c17f2e33c9d71f4efba096995722e6279fcc9cfc7810ed` |
| beta=0.25 candidate | `1abb0e73a576349924341a46209d158482123478448e8bee333c713a5ad18b2a` |
| data-only comparator | `4bb51840da4fe6cfd845b436e4cea5a59a5ff02e32a59bc2b29eb9451a3ef804` |

The 11 producer files were hashed independently in the live output, remote
archive and local retrieval; all three inventories matched exactly. Key hashes:

| File | SHA-256 |
|---|---|
| `cycle_metrics.csv` | `7bc05e5b457e00b5abbd2aaef404ea5c4c7052ed83b732902e01ce8d794f44fa` |
| `cycle_progress.jsonl` | `57bcaafd349d25a4040c840b45aeb0f2deb73666860661d325c849820a63e10f` |
| `metrics.json` | `3679f22710dde9c7eaa0927b8b4f6b00413b4483964e1aed2f7b3382b319c190` |
| `receipt.json` | `27f5201819635d632a264ca52c369d78d9b5814663032e7365a37281158dcc7f` |
| `selected_fields.npz` | `ee1c8bcc29a66063824738905bc65ab57e23bdd61b2eb9e4b3652114bf68e390` |

The permanent packet build marker records one successful scientific unsealing,
with packet SHA-256 `447c372b...10ed`; the permanent Taobo attempt marker records
one successful scientific evaluation. The earlier local routing failure was
separately classified as eligible for one operational retry because no remote
marker, output or prediction existed.
