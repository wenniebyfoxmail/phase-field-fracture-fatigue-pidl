# Mesh-GNN Residual Discriminator

Date: 2026-06-16

Status: **legacy soft-hist0 diagnostic only**. Do not use this c69 experiment
as the current hard-recovery representation test. The c89 replacement is
documented in `docs/hard_recovery_graph_residual_discriminator_v2_2026-07-10.md`.

## Question

Can local mesh-neighbourhood information explain the strict FEM/PIDL field
residual for the two currently failing mechanism fields:

- active driver `g(alpha) * psi_plus_raw`
- fatigue history `alpha_bar`

This is a cheap offline discriminator before changing the PIDL training loop.
It does not add a new physics term and it does not run PIDL training.

## Tool

```text
SENS_tensile/analyze_mesh_gnn_residual_discriminator.py
```

The script:

1. Loads strict soft-hist0 FEM combined element fields.
2. Uses existing PIDL checkpoints or existing `element_fields_cycle_*.npz`
   files.
3. Projects FEM targets to PIDL element centroids.
4. Trains a small pure-PyTorch mesh residual model:

```text
features = coordinates + PIDL alpha/history/f/psi/strain/energy fields
edges    = k-nearest PIDL element-centroid neighbours
target   = log(FEM field) - log(PIDL field)
```

It trains both:

- `graph`: neighbourhood aggregation through kNN graph edges
- `mlp`: same features without graph aggregation

The MLP baseline matters.  If graph and MLP perform similarly, the useful
signal is in local scalar state features, not in mesh topology.

## Default Command

Use the Mac scientific Python, not the system Python:

```bash
cd "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code"
/Users/wenxiaofang/miniconda3/bin/python3 \
  SENS_tensile/analyze_mesh_gnn_residual_discriminator.py \
  --train-cycles 20,40 \
  --test-cycles 69 \
  --targets psi_active,alpha_bar \
  --models graph,mlp \
  --epochs 300
```

The current soft-hist0 comparison convention is used by default:

```text
FEM c20 -> PIDL j19
FEM c40 -> PIDL j39
FEM c69 -> PIDL j68
```

Outputs are written under:

```text
_analysis_fem_mechanism_20260528/experiments/mesh_gnn_residual_discriminator_20260616/
```

## Gate

Positive sign:

- held-out c69 log residual error drops substantially relative to raw PIDL;
- corrected `psi_active` and `alpha_bar` improve the near-tip/process-zone
  metrics, not just domain mean;
- graph beats MLP, suggesting that local mesh neighbourhood carries useful
  information beyond scalar per-element features.

Negative sign:

- training cycles fit but held-out c69 does not improve;
- corrected fields only fix scalar magnitude while keeping the wrong location;
- graph offers no advantage over MLP.

## Interpretation

If positive, the next online experiment should be a residual sidecar whose
authority is limited to the history/driver channel, with the same field-level
gate as the FBPINN-chain branch.  If negative, do not spend GPU time wiring a
GNN into the PIDL training loop; keep the focus on history/degradation timing
or a stronger physics-consistent representation.

## First Offline Pass

Mac command, shortened from the default for a first check:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  SENS_tensile/analyze_mesh_gnn_residual_discriminator.py \
  --train-cycles 20,40 \
  --test-cycles 69 \
  --targets psi_active,alpha_bar \
  --models graph,mlp \
  --epochs 150 \
  --hidden 32 \
  --layers 2
```

Held-out c69 log-error result:

| target | model | log MAE before | log MAE after | readout |
|---|---:|---:|---:|---|
| `psi_active` | graph | 0.498 | 0.364 | improves by 26.8% |
| `psi_active` | MLP | 0.498 | 0.466 | improves by 6.6% |
| `alpha_bar` | graph | 0.0116 | 0.0479 | worse |
| `alpha_bar` | MLP | 0.0116 | 0.0283 | worse |

Field-gate readout:

- For `psi_active`, graph has a real neighbourhood signal.  It improves the
  held-out residual more than the MLP and moves right-band mean closer to FEM
  (`1.58x -> 0.92x` FEM).  But it still leaves the near-tip active driver far
  below FEM (`tip_2l0_mean 0.029x -> 0.088x` FEM), so this is not field closure.
- For `alpha_bar`, the correction is negative.  The PIDL right-band history is
  already close to FEM, and the graph over-corrects it while barely improving
  the tip deficit.

Current interpretation: a mesh-neighbourhood residual sidecar is plausible for
diagnosing/correcting `psi_active` location and magnitude, but not as a direct
`alpha_bar` correction.  The next useful version would target only
`psi_active`, include stricter held-out cycles or leave-one-run-out validation,
and check whether improved active-driver residuals actually translate into
better downstream history when coupled online.
