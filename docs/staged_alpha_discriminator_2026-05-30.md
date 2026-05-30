# Staged-Alpha FEM-Mesh Discriminator

Date: 2026-05-30

## Question

Can the strict FEM-mesh PIDL gap be reduced by changing the per-cycle
optimisation path while keeping the same mesh, same soft-hist0 initialisation,
same variational energy, and same fatigue law?

This tests whether the gap is partly a coupled-optimisation path problem, not a
mesh/reference/timing problem and not a final-checkpoint polish problem.

## Implementation

Runner:

```text
SENS_tensile/run_fem_mesh_staged_alpha_umax.py
```

Trainer hook:

```text
source/model_train.py
fatigue_dict["staged_alpha"]
```

Schedule per fatigue cycle:

```text
1. uv-head stage: train only output rows 0 and 1
2. alpha-head stage: train only output row 2
3. joint stage: normal full-network RPROP
```

The current MLP has one shared trunk, so this is a head-staging proxy for FEM
alternate minimisation.  It does not change the physics loss.

## Intended Taobo Launch

```bash
cd /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile
mkdir -p run_logs
PIDL_ARCHIVE_DIR=/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile \
CUDA_VISIBLE_DEVICES=0 /usr/bin/python3 run_fem_mesh_staged_alpha_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0 \
  --fracture-confirm-cycles 3 \
  --plot-every 20 \
  --uv-head-epochs 750 \
  --alpha-head-epochs 750 \
  --joint-epochs 10000 \
  > run_logs/femmesh_stagedAlpha_softHist0_u012_N100_seed1_20260530.log 2>&1 &
```

Expected archive suffix:

```text
_femmesh_softHist0_stagedAlpha_uv750_a750_j10000
```

## Promotion Gate

Compare against strict FEM-mesh baseline under the same j=c-1 mapping and
matched-event mapping:

```text
c20/c40/c69 and event j84/j85
damage_alpha tip2/p99
alpha_bar tip2/p99
psi_plus_raw tip2/p99
psi_plus_active tip2/p99
Delta E_d
right-boundary saturation check
```

Positive sign:

```text
active psi+ and alpha_bar move toward FEM without only over-saturating the
right boundary.
```

Negative sign:

```text
N_f or crack position changes, but active psi+ and Delta E_d remain near the
strict FEM-mesh baseline.
```

## Launch Status

Prepared and pushed.  Taobo launch was not completed at this time because SSH
to `172.16.100.2:22` timed out from the Mac shell.
