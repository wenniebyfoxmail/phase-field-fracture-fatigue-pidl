# Frozen-Alpha Elastic Discriminator

Date: 2026-06-03

## Question

Does the first PIDL/FEM `psi_raw` mismatch come from the elastic displacement
solve itself, before alpha evolution and fatigue-history feedback can amplify
anything?

## Why This Is New

Previous strict FEM-mesh tests included head-staging, split trunks, local
patches, discontinuity/enrichment, history-driver variants, and residual
stiffness.  Those still allowed coupled alpha evolution during the cycle or
tested full fatigue trajectories.

This discriminator freezes alpha to the analytic soft-hist0 initial precrack
and optimises only the displacement field through elastic energy:

```text
alpha = hist_alpha_init fixed
loss = log10(sum_e area_e * psi_elastic(u,v,alpha_fixed)) + weight_decay
```

It is therefore a c1 elastic-field test, not a fatigue model change.

## Runner

```text
SENS_tensile/run_fem_mesh_frozen_alpha_elastic_probe.py
```

Outputs:

```text
element_diagnostics/frozen_alpha_elastic_fields.npz
best_models/frozen_alpha_elastic_loss.csv
best_models/trained_frozen_alpha_elastic.pt
model_settings.txt
```

The field NPZ contains:

```text
eps_xx, eps_yy, eps_xy, eps_trace, eps_eq,
psi_raw, g_alpha, psi_active, alpha_fixed, E_el
```

## Taobo Launch Plan

Use the residual-stiffness branch's post-pretraining checkpoint as the initial
network so the test starts from the same pretraining state as the current
strict residual-stiffness PIDL run.

```bash
cd /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile
mkdir -p run_logs
CUDA_VISIBLE_DEVICES=<gpu> /usr/bin/python3 run_fem_mesh_frozen_alpha_elastic_probe.py 0.12 \
  --epochs 10000 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0_resStiff1e6_frozenAlphaElastic \
  --res-stiffness 1e-6 \
  --init-ckpt /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_eta1em06/best_models/trained_1NN_initTraining.pt \
  --log-every 250 \
  > run_logs/femmesh_frozenAlphaElastic_softHist0_u012_ep10000_20260603.log 2>&1 &
```

## Gate

Compare against FEM22 nstep2 c1 peak-load state:

```text
eps_xx, eps_yy, eps_xy, eps_trace, eps_eq,
psi_raw, psi_active
```

Primary reductions:

```text
tip_2l0_mean, domain_mean, p99, p999, max, location of max
```

Positive sign:

```text
Frozen-alpha elastic PIDL moves eps_eq/psi_raw much closer to FEM22 than the
coupled first-cycle PIDL checkpoint.
```

This would mean the coupled alpha solve/history path creates the hotspot.

Negative sign:

```text
Frozen-alpha elastic PIDL still has the same sharp strain/psi hotspot.
```

This would put the root cause in the displacement representation, boundary
ansatz, quadrature/projection, or optimiser basin for the elastic field.

## Result

Taobo run completed on 2026-06-03:

```text
archive: /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_off_N1_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_frozenAlphaElastic_ep10000
E_el: 2.233275e-02 -> 7.187365e-03
```

Key c1 peak ratios against FEM22 nstep2:

| field/metric | coupled residual-stiffness c1 | frozen-alpha elastic |
|---|---:|---:|
| eps_eq tip2 mean | 1.086 | 0.581 |
| eps_eq max | 1.892 | 0.216 |
| psi_raw tip2 mean | 2.336 | 0.250 |
| psi_raw max | 4.068 | 0.0527 |
| psi_active tip2 mean | 1.010 | 0.510 |
| psi_active max | 1.676 | 2.279 |

Interpretation:

```text
fixed alpha does not force the oversharp raw-energy hotspot.
coupled c1 is too hot in raw strain/psi.
frozen-alpha elastic is too cold along the crack line.
```

So the likely culprit is not the initial alpha/precrack alone and not simply
the displacement network being unable to smooth the field.  The mismatch is
created by the coupled elastic-damage optimisation path at the first loaded
solve.  Next test should be a true c1 alternate-minimisation micro-solve:

```text
freeze alpha -> solve u/v
freeze u/v -> solve alpha
repeat a few substages
export epsilon/psi/alpha after every substage
```
