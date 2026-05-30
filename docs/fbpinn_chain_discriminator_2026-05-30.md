# FBPINN-Chain FEM-Mesh Discriminator

Date: 2026-05-30

## Question

Can a true domain-decomposed representation reduce the strict FEM-mesh
soft-hist0 field gap, after the additive one-patch local correction was
weak/negative?

## Design

Runner:

```text
SENS_tensile/run_fem_mesh_fbpinn_umax.py
```

Representation:

```text
out_global = global_MLP(x, y)
out_local_i = local_MLP_i((x-x_i)/wr, y/wr)
chi_i = max(1 - r_i^2/wr^2, 0)^2
out_local = sum_i chi_i*out_local_i / sum_i chi_i
beta = min(sum_i chi_i, 1)
raw_output = (1-beta)*out_global + beta*out_local
```

Default branch:

```text
strict FEM mesh: meshed_geom_fem_soft_hist0.msh
Umax: 0.12
N cycles: 100
subdomains: 6 overlapping patches along x=0.00 -> 0.45, y=0
wr: 0.12
patch net: 3 hidden layers x 80 neurons
per-cycle schedule: patch-only warm-up 1500 -> joint RPROP 10000
diagnostics: c20/c40/c69 + dense/event states
```

This is still the same variational energy and fatigue law.  The only change is
representation and optimiser authority: inside local windows, the local
subdomain nets carry the raw field instead of acting as small residual
corrections.

## Gate

Use the same field-level gate as the strict FEM-mesh benchmark:

```text
damage/alpha field
alpha_bar
raw psi0
active driver g(alpha)*psi0
Delta E_d
right-boundary saturation
alpha snapshots and residual-field visualisation
```

Future PIDL diagnostics now save both:

```text
psi_raw_elem
psi_active_elem
```

because the older `psi_plus_elem` name was actually the active fatigue driver.

## Taobo Launch Command

```bash
cd /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile
mkdir -p run_logs
CUDA_VISIBLE_DEVICES=<gpu> /usr/bin/python3 run_fem_mesh_fbpinn_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --n-patches 6 \
  --x-start 0.0 \
  --x-end 0.45 \
  --wr 0.12 \
  --patch-hidden-layers 3 \
  --patch-neurons 80 \
  --patch-warm-epochs 1500 \
  --joint-epochs 10000 \
  > run_logs/femmesh_fbpinnChain_n6_wr012_softHist0_u012_N100_seed1_20260530.log 2>&1 &
```

Expected archive suffix:

```text
_femmesh_softHist0_fbpinnChain_n6_wr0.12_x0.0to0.45_h3_n80_warm1500_j10000
```
