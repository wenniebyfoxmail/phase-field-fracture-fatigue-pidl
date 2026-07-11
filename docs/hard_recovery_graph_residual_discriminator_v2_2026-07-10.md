# Hard-Recovery Graph Residual Discriminator v2

Date: 2026-07-10

Status: eta=0 multi-seed result complete; diagnostic-positive with localization
caveats. Frozen eta=1e-3 comparison pending.

## Mechanism Question

After separating the dominant c89 degradation collapse, does the semantically
matched peak raw-driver residual still contain neighbourhood information that a
pointwise model cannot explain?

This is a secondary representation diagnostic. It does not replace the
residual-stiffness micro-run and cannot establish active-driver or full
mechanism closure.

## Audit Of The Legacy Script

The 2026-06-16 prototype remains useful as historical c69 evidence, but it is
not suitable for the current hard-recovery comparison:

- it is bound to the soft-hist0 c20/c40-to-c69 mapping;
- it synthesizes a FEM active target from cycle-peak raw `psi` and unloaded
  damage, which mixes state semantics;
- it uses centroid kNN instead of the archived mesh topology;
- it projects FEM fields by nearest centroid instead of the accepted
  polygon-overlap map;
- it has no validation cycle, early stopping, or multi-seed stability check;
- its field metrics do not use the current denominator-safe c89 masks;
- graph and MLP initialization was not explicitly paired by seed.

## v2 Design

Entry point:

```text
SENS_tensile/analyze_hard_recovery_graph_residual_discriminator.py
```

The v2 discriminator uses:

- the exact dual graph of the `86408` archived FEM quad cells;
- `344938` directed shared-edge adjacencies;
- the accepted polygon-overlap projection from PIDL elements to FEM cells;
- hard-recovery peak mapping `cN_peak = 1 + 5*(N-1) + 3`;
- c20/c40/c60 for training, c69 for validation, and untouched c89 for test;
- only the matched peak-raw target
  `log10(FEM raw psi) - log10(PIDL raw psi)`;
- a residual GraphSAGE-style model and a parameter-matched pointwise MLP;
- paired initialization for each seed;
- robust Huber loss, gradient clipping, validation early stopping, and
  multi-seed aggregation;
- whole-domain plus `fem_top1_clean`, `fem_pz_1200`, and `fem_core_2400`
  metrics;
- support coverage, Jaccard overlap, and centroid-distance diagnostics.

No `torch_geometric` dependency is required. The implementation is pure
PyTorch plus the repository's existing NumPy/SciPy/meshio stack.

## Gate

A representation signal is supported only if the graph model consistently
beats the parameter-matched MLP on untouched c89 in denominator-safe high-FEM
driver masks and improves support localization. Whole-domain MAE improvement
alone is insufficient.

If graph advantage is seed-unstable, confined to background cells, or absent
from c89 high-driver masks, close the representation branch as negative.

Even a positive raw-driver result remains secondary while active support is
collapsed. After the eta micro-run returns, rerun the frozen protocol on the
eta result and compare graph advantage before and after the intervention.

## Verification

Mac-safe checks completed:

- Python compilation: pass;
- five unit tests covering hard-recovery mapping, dual adjacency, overlap
  projection, parameter matching, and feature transforms: pass;
- existing-archive dry-run: pass, with full projection coverage;
- one-epoch, one-seed, hidden-8 code-path smoke: pass in about 3 seconds.

The one-epoch output is tooling evidence only and must not be interpreted as a
scientific GNN verdict.

## eta=0 Taobo Result

The frozen three-seed run completed on Taobo from source commit `926c34c`.
Local result endpoint:

```text
local_archive/after_strict_setting_alignment/pidl_result/
hard_recovery_graph_raw_eta0_926c34c_20260711_141546/analysis/decision.md
```

On untouched c89, graph log-MAE was lower than the parameter-matched MLP for
all three seeds in all primary high-driver masks. Mean graph-vs-MLP gains were:

- `14.97%` in `fem_top1_clean`;
- `14.30%` in `fem_pz_1200`;
- `10.41%` in `fem_core_2400`.

The localization result is mixed. The graph consistently improves over MLP,
and restores some support in the strongest FEM core, but it does not uniformly
improve over the uncorrected PIDL field at broader thresholds. Whole-domain
graph log-MAE also remains slightly worse than uncorrected PIDL.

Decision: the eta=0 raw residual contains reproducible neighbourhood signal,
but this does not establish an independent representation bottleneck or justify
online GNN coupling. Keep the exact protocol frozen for eta=1e-3.

## Full Offline Producer Command

Run on a producer or approved analysis machine, not as PIDL training on Mac:

```bash
python3 SENS_tensile/analyze_hard_recovery_graph_residual_discriminator.py \
  --pidl-diag-dir <PIDL_ELEMENT_DIAGNOSTICS_DIR> \
  --fem-psi-dir <FEM_PSI_FIELDS_DIR> \
  --fem-vtk <FEM_STATIC_MESH_VTK> \
  --projection-map <POLYGON_OVERLAP_MAP_NPZ> \
  --out-dir <RESULT_PACKAGE_DIR> \
  --train-cycles 20,40,60 \
  --val-cycles 69 \
  --test-cycles 89 \
  --models mlp,graph \
  --seeds 1,7,19 \
  --hidden 64 \
  --layers 3 \
  --epochs 300
```

Required scientific assets are `decision.md`, `tables/seed_metrics.csv`,
`tables/graph_advantage_by_seed.csv`, `tables/support_metrics.csv`, and
`figures/c89_graph_vs_mlp.pdf`.
