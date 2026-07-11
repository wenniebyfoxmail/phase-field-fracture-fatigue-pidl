# Hard-Recovery eta=0 Graph Residual Taobo Run

Created: 2026-07-11 14:42 BST
Status: completed, downloaded, and analysed

## Purpose

Run the frozen three-seed MLP-vs-graph discriminator on the matched
hard-recovery peak raw-driver residual. This is the eta=0 representation
baseline and runs independently of the residual-stiffness PIDL micro-run.

## Launch Record

```text
run_id: pf_graphraw_eta0_926c34c_20260711_141546
source branch: codex/m2s-framework-validation
source commit: 926c34c
sync mode: single-runner rsync snapshot from pushed commit
producer: Taobo GPUServer8
physical GPU: 6
PID: 2950237
remote root: /mnt/data2/drtao/wennie/pf_graphraw_eta0_926c34c_20260711_141546
archive root: /mnt/data2/drtao/pidl_archives/pf_graphraw_eta0_926c34c_20260711_141546
log: /mnt/data2/drtao/wennie/pf_graphraw_eta0_926c34c_20260711_141546/logs/graph_raw_eta0.log
provenance: /mnt/data2/drtao/wennie/pf_graphraw_eta0_926c34c_20260711_141546/RUN_PROVENANCE.txt
```

Frozen protocol:

```text
train cycles: 20,40,60
validation cycle: 69
sealed test cycle: 89
models: mlp,graph
seeds: 1,7,19
hidden/layers/epochs: 64/3/300
device: CUDA physical GPU6
```

## Input Provenance

- eta=0 PIDL snapshots are reused from the original server-resident
  hard-recovery archive under
  `/mnt/data2/drtao/pidl_archives/pf_hard_d1_u0_recovery_e9dc263_20260630_043100/`.
- The compact FEM/projection bundle preserves only the static FEM cell mesh,
  cycle-peak `psi_elem` for c20/c40/c60/c69/c89, and projection
  `src/dst/weight`.
- Bundle SHA256:
  `28b6210dba0e3f6ada3e80d166c29bded250d018d677b1bd4b6b970a5f497d71`.
- Remote preflight reproduced `86408` FEM cells, `344938` directed dual edges,
  and full projection coverage.

## Initial Health

At the first check, PID `2950237` was `Rl`; GPU6 used about `2516 MiB` with
`77%` utilization. `analysis_manifest.json` was present. The log may remain
quiet until model/test summaries are emitted.

The run then completed normally, GPU6 returned idle, and the full package was
downloaded. Return package SHA256:

```text
0bafa5510bb0a2e3a032670f752b535e7ff55303163689ccbe42687383ae8bda
```

Local case:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/
after_strict_setting_alignment/pidl_result/
hard_recovery_graph_raw_eta0_926c34c_20260711_141546/
```

Read-only monitor commands:

```bash
ssh -F /dev/null drtao@172.16.100.2 \
  "ps -p 2950237 -o pid,etime,stat,cmd"

ssh -F /dev/null drtao@172.16.100.2 \
  "tail -40 /mnt/data2/drtao/wennie/pf_graphraw_eta0_926c34c_20260711_141546/logs/graph_raw_eta0.log"
```

## Result Gate

Do not promote a graph claim from whole-domain MAE. The graph must beat the
parameter-matched MLP across seeds on untouched c89 in `fem_top1_clean`,
`fem_pz_1200`, and `fem_core_2400`, with improved support localization.

## Result

Verdict: **mixed / diagnostic-positive**.

- Graph beats MLP for all three seeds in all three primary c89 masks.
- Mean graph-vs-MLP log-MAE gains are `14.97%`, `14.30%`, and `10.41%` for
  `fem_top1_clean`, `fem_pz_1200`, and `fem_core_2400` respectively.
- Graph improves strongest-core support, but broad-threshold localization is
  not uniformly better than uncorrected PIDL.
- Whole-domain graph log-MAE remains slightly worse than uncorrected PIDL.

Claim boundary: neighbourhood structure exists in the eta=0 raw residual, but
representation is not established as the primary mismatch and online GNN
coupling is not promoted. Next action is the exact frozen eta=1e-3 repeat.
