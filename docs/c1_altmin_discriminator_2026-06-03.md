# C1 Alternate-Minimisation Discriminator

Date: 2026-06-03

## Question

The frozen-alpha elastic probe showed that fixed analytic alpha makes the c1
raw elastic driver too cold, while the normal coupled PIDL c1 field is too hot.
This suggests the first-cycle mismatch is created by the coupled optimisation
path, not by the initial precrack alone.

This probe asks:

```text
If PIDL solves c1 more like FEM alternate minimisation,
when does the psi_raw / epsilon hotspot appear?
```

## Runner

```text
SENS_tensile/run_fem_mesh_c1_altmin_probe.py
```

The runner starts from a post-pretraining strict FEM-mesh soft-hist0 checkpoint
and performs:

```text
initial_joint        evaluate current NN u/v/alpha
initial_uv           evaluate current u/v with fixed analytic hist_alpha
r1_uv                freeze alpha snapshot, optimise u/v final-head rows
r1_alpha             freeze u/v snapshot, optimise alpha final-head row
r2_uv
r2_alpha
r3_uv
r3_alpha
```

The variational terms are unchanged:

```text
E = E_el + E_d + E_hist
```

Only the optimisation path changes.  During each substage, the frozen field is
a detached snapshot.  The active output-head rows are also restricted so the
non-target field does not move by accident through the shared final head.

## Outputs

```text
element_diagnostics/c1_altmin_fields.npz
best_models/c1_altmin_trace.csv
best_models/trained_c1_altmin.pt
model_settings.txt
```

Field NPZ stores each exported state:

```text
alpha_elem, eps_xx_elem, eps_yy_elem, eps_xy_elem, eps_eq_elem,
psi_raw_elem, g_alpha_elem, psi_active_elem,
E_el_elem, E_d_elem, E_hist_elem
```

Trace CSV stores scalar and gradient diagnostics:

```text
E_el, E_d, E_hist, log10_E_total,
grad_logEel, grad_logEd, grad_logEhist,
alpha_max, psi_raw_max, psi_active_max
```

## Taobo Command

```bash
cd /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile
mkdir -p run_logs
CUDA_VISIBLE_DEVICES=<gpu> /usr/bin/python3 run_fem_mesh_c1_altmin_probe.py 0.12 \
  --rounds 3 \
  --uv-epochs 2000 \
  --alpha-epochs 2000 \
  --joint-epochs 0 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --tag softHist0_resStiff1e6_c1AltMin \
  --res-stiffness 1e-6 \
  --init-ckpt /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_eta1em06/best_models/trained_1NN_initTraining.pt \
  --log-every 250 \
  > run_logs/femmesh_c1AltMin_softHist0_u012_r3_uv2000_a2000_20260603.log 2>&1 &
```

## Gate

Compare every exported substage against FEM22 n_step2 c1 peak-load state:

```text
eps_eq, psi_raw, g_alpha, psi_active, alpha
```

Primary reductions:

```text
tip_2l0_mean, p99, p999, max, max location,
near-tip integral, corr(psi_active, alpha increment)
```

Interpretation:

```text
If r1_uv already matches frozen-alpha cold fields, then displacement-only
equilibrium is not enough to create the PIDL hotspot.

If r1_alpha creates the hotspot, the alpha solve/degradation feedback is the
first culprit.

If later uv/alpha alternations move toward FEM, the issue is coupled optimiser
timing/path trapping.

If all substages remain far from FEM, the remaining gap is representation,
BC ansatz, quadrature/projection, or objective scaling rather than coupling
order alone.
```

## Result

Taobo run completed on 2026-06-03:

```text
archive: /mnt/data2/drtao/projects/pidl-resstiff-69bb1b2-20260603/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_off_N1_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_c1AltMin_r3_uv2000_a2000_j0
```

Key scalar trace:

| state | E_el | E_d | E_hist | psi_raw_max | psi_active_max | grad_logEel | grad_logEd | grad_logEhist |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| initial_joint | 4.915e-3 | 5.461e-3 | 2.340e-5 | 2703.7 | 0.924 | 0 | 0 | 0 |
| initial_uv | 2.233e-2 | 5.085e-3 | 0 | 2703.7 | 43.38 | 0 | 0 | 0 |
| r1_uv | 7.463e-3 | 5.085e-3 | 0 | 53.95 | 0.865 | 6.50e-2 | 0 | 0 |
| r1_alpha | 7.033e-3 | 5.255e-3 | 1.071e-5 | 53.95 | 0.262 | 1.58 | 3.93 | 8.99e2 |
| r2_uv | 6.314e-3 | 5.255e-3 | 1.071e-5 | 571.6 | 3.41 | 1.02e-2 | 0 | 0 |
| r2_alpha | 5.617e-3 | 5.449e-3 | 9.025e-6 | 571.6 | 0.259 | 1.78 | 3.37 | 9.38e2 |
| r3_uv | 4.952e-3 | 5.449e-3 | 9.025e-6 | 2409.9 | 0.982 | 4.15e-3 | 0 | 0 |
| r3_alpha | 4.854e-3 | 5.480e-3 | 7.632e-6 | 2409.9 | 0.318 | 1.12 | 2.47 | 1.07e3 |

Key ratios against FEM22 n_step2 c1 peak:

| state | eps_eq tip2 | psi_raw max | psi_active tip2 | alpha max |
|---|---:|---:|---:|---:|
| initial_joint | 1.058 | 3.942 | 1.171 | 1.004 |
| r1_uv | 0.516 | 0.0787 | 0.463 | 0.940 |
| r2_uv | 0.753 | 0.833 | 0.675 | 0.988 |
| r3_uv | 1.012 | 3.513 | 1.042 | 1.003 |
| r3_alpha | 1.012 | 3.513 | 0.978 | 1.004 |

Interpretation:

```text
r1_uv: fixed-alpha displacement equilibrium cools the raw hotspot.
r1_alpha: alpha-only optimisation does not restore the raw hotspot.
r2_uv/r3_uv: raw hotspot reappears when u/v re-equilibrates around the updated alpha field.
```

This points to a coupled feedback loop rather than a one-step alpha-only error:
alpha/degradation changes the stiffness landscape, and the following uv
equilibrium step concentrates raw strain around that updated damage field.  The
large alpha-stage `grad_logEhist` values also mean irreversibility is not a
minor bookkeeping term during alpha motion; it is a dominant gradient channel in
this micro-solve.

Local analysis package:

```text
_analysis_fem_mechanism_20260528/experiments/c1_altmin_20260603/
```
