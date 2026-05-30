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

## Taobo Launch

```bash
cd /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile
mkdir -p run_logs
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

Initial branch launched on Taobo after SSH recovered:

```text
PID: 1261309
GPU: 3
log: /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/run_logs/femmesh_stagedAlpha_softHist0_u012_N100_seed1_20260530.log
```

Initial check: process alive after about one minute; GPU3 compute and memory are
active.  The log had not flushed yet, so progress should be checked by process,
GPU, and archive files until stdout starts writing.

Additional matrix branches:

```text
alpha-head-only:
  PID: 1267928
  GPU: 5
  schedule: uv0 -> alpha1500 -> joint10000
  log: /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/run_logs/femmesh_alphaHeadOnly_softHist0_u012_N100_seed1_20260530.log

uv-head-only:
  PID: 1276196
  GPU: 0
  schedule: uv1500 -> alpha0 -> joint10000
  log: /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/run_logs/femmesh_uvHeadOnly_softHist0_u012_N100_seed1_20260530.log

head-stages-only:
  PID: 1276197
  GPU: 1
  schedule: uv750 -> alpha750 -> joint0
  log: /mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/run_logs/femmesh_headStagesOnly_softHist0_u012_N100_seed1_20260530.log
```

Health check after launch: all four PIDs were alive.  GPU0/GPU1/GPU3/GPU5
showed active compute/memory.  Logs had not flushed yet.

## Result

All four jobs completed.

Scalar/event summary:

| branch | schedule | first right-boundary detection | confirmed/last | c69 alpha_bar max | c69 Kt | final alpha_bar max |
|---|---|---:|---:|---:|---:|---:|
| strict FEM-mesh baseline | joint only | j82 | j85 | 9.94 | 14.29 | 11.39 |
| staged-alpha | uv750 -> alpha750 -> joint10000 | j80 | j83 | 7.59 | 15.19 | 8.35 |
| alpha-head-only | uv0 -> alpha1500 -> joint10000 | j80 | j83 | 7.54 | 15.38 | 8.04 |
| uv-head-only | uv1500 -> alpha0 -> joint10000 | j81 | j84 | 8.52 | 14.69 | 9.89 |
| head-stages-only | uv750 -> alpha750 -> joint0 | no event | j99 end | 29.00 | 7.58 | 41.03 |

Field-level gate against FEM n_step10 c69 on common probes:

| branch/state | damage tip2 | alpha_bar tip2 | raw psi+ tip2 | active psi+ tip2 | Delta E_d |
|---|---:|---:|---:|---:|---:|
| baseline fixed j68 | 1.01 | 0.37 | 1.58 | 0.023 | 0.25 |
| staged fixed j68 | 1.07 | 0.35 | 1.57 | 0.019 | 0.29 |
| alpha fixed j68 | 1.07 | 0.35 | 1.56 | 0.020 | 0.29 |
| uv fixed j68 | 1.00 | 0.37 | 1.55 | 0.023 | 0.25 |
| staged event j83 | 1.09 | 0.35 | 1.65 | 0.003 | 0.43 |
| alpha event j83 | 1.09 | 0.35 | 1.65 | 0.003 | 0.44 |
| uv event j84 | 1.01 | 0.37 | 1.65 | 0.007 | 0.40 |
| no-joint last j99 | 0.74 | 4.13 | 0.06 | 4.81 | -0.14 |

Diagnostic figure:

```text
_analysis_fem_mechanism_20260528/figures/staged_head_discriminator_gate_summary_20260530.png
```

## Interpretation

Head-staging alone is not the missing mechanism.  The branches with a final
joint solve still leave `alpha_bar` tip2 at only about 0.35-0.37x FEM and
active `psi+` tip2 near zero.  Their event states increase `Delta E_d` to
about 0.40-0.44x FEM, but this comes with boundary saturation and still does
not restore local active-driver/history feedback.

The no-joint branch is pathological: `alpha_bar` becomes huge, but crack
propagation stalls (`x_tip` stays at 0), raw `psi+` near the tip collapses, and
incremental `E_d` is negative relative to FEM.  This confirms the final joint
elastic-damage relaxation is necessary, but not sufficient.

Current decision: close head-staging as a useful negative discriminator.  The
next test should strengthen local representation/authority rather than add more
head-stage schedules.
