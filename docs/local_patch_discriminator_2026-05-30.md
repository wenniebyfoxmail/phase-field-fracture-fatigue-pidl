# Local-Patch FEM-Mesh Discriminator

Date: 2026-05-30

## Question

Can a compact, independently trained crack-tip patch improve the strict
FEM-mesh soft-hist0 field gap while keeping the same variational energy,
fatigue law, history timing, mesh, and event criterion?

This is the next discriminator after head-staging failed.  It asks whether the
local tip mechanism needs stronger representation/local optimisation authority,
not merely a different global output-head schedule.

## Implementation

Runner:

```text
SENS_tensile/run_fem_mesh_local_patch_umax.py
```

Core representation:

```text
raw_output = global_MLP(x,y) + chi(r) * local_patch_MLP((x-x_tip)/wr, (y-y_tip)/wr)
chi(r) = max(1 - r^2 / wr^2, 0)^2
```

Default discriminator:

```text
FEM mesh: meshed_geom_fem_soft_hist0.msh
Umax: 0.12
N cycles: 100
wr: 0.10
patch: all outputs, 3 hidden layers, 80 neurons
per-cycle schedule: patch-only warm-up 1500 RPROP epochs -> joint RPROP 10000 epochs
element diagnostics: c20, c40, c69, dense/event states
```

The patch network is registered inside `field_comp.net`, so normal
`trained_1NN_*.pt` checkpoints include both global and local-patch weights.
`posthoc_mesh_probe_alignment.py` and `export_pidl_element_diagnostics.py` now
reconstruct local-patch archives from `model_settings.txt`.

## What This Is Not

This is not a new physical loss, not local loss reweighting, and not a full
FBPINN/multi-subdomain solver.  It is the minimal strict test of a
domain-decomposed/tip-local representation with real optimiser authority.

## Gate

Score against FEM standard/n_step10 c69 and matched-event fields using the same
gate as the staged-head matrix:

```text
damage tip2/p99
alpha_bar tip2/p99
raw psi+ tip2/p99
active psi+ tip2/p99
Delta E_d
right-boundary saturation check
alpha snapshots / residual fields
```

Positive sign:

```text
alpha_bar and active psi+ move toward FEM near the crack tip, and Delta E_d
increases for the right reason, without merely saturating the right boundary.
```

Negative sign:

```text
N_f or scalar alpha_bar changes, but active psi+ remains near zero relative to
FEM and the alpha field still propagates as a coherent centerline/boundary band.
```

## Taobo Launch Command

```bash
cd /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile
mkdir -p run_logs
CUDA_VISIBLE_DEVICES=<gpu> /usr/bin/python3 run_fem_mesh_local_patch_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --wr 0.10 \
  --output-mode all \
  --patch-hidden-layers 3 \
  --patch-neurons 80 \
  --patch-warm-epochs 1500 \
  --joint-epochs 10000 \
  > run_logs/femmesh_localPatch_all_wr010_softHist0_u012_N100_seed1_20260530.log 2>&1 &
```

Expected archive suffix:

```text
_femmesh_softHist0_localPatch_all_wr0.1_h3_n80_warm1500_j10000
```
