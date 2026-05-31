# Inverse Problem Experiments

Date: 2026-05-31

## Question

Can an outer inverse loop recover a meaningful fatigue parameter from FEM
field observations once the comparison is made on the latest fair alignment:
strict FEM-mesh soft-hist0 PIDL versus soft-hist0 reverseBC FEM?

## Current Target And Baseline

FEM target:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
/mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
N_f = 69
```

Properties:

```text
reverseBC
retained-material diffuse mesh
soft AT1/PIDL-like precrack profile
initial alpha_bar = 0
initial f_alpha = 1
```

PIDL baseline:

```text
strict FEM-mesh soft-hist0 MLP
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/..._femmesh_softHist0
```

The clean comparison protocol is FEM cycle `c` mapped to PIDL saved index
`j = c - 1`.

## Implementation

Branch and commit:

```text
codex/inverse-femmesh-soft-hist0
215c3bd Add FEM-mesh inverse alphaT retry
```

Runner:

```text
SENS_tensile/run_fem_mesh_inverse_alphaT_umax.py
```

Remote run:

```text
/mnt/data2/drtao/projects/pidl-femmesh-inverse-alphaT-215c3bd
GPU 5
PID 4163602
log:
SENS_tensile/run_logs/inverse_alphaT_femmesh_softHist0_u012_N100_K69_seed1_gpu5_20260531_1707.log
archive:
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aTlearnInit0.25_N100_R0.0_Umax0.12_femmesh_softHist0_inverseAlphaT_K69_lamA1_tolir0.005_maskboundary_or_crack_fixedEirrev
```

Inverse variable:

```text
alpha_T trainable
init = 0.25
bounds = [0.05, 2.0]
fixed E_irrev / tol_ir = 5e-3
alpha target loss against FEM d_elem
mask = boundary_or_crack
K = 69
PIDL j -> FEM c = j + 1
```

Diagnostic guardrail:

```text
element_diagnostics saves:
psi_raw_elem
psi_active_elem = g(alpha) * psi_raw_elem
g_alpha_elem
```

This was necessary because older PIDL `psi_plus_elem` diagnostics were the
active fatigue driver, not raw undegraded tensile energy.

## Result

The run finished early:

| quantity | result |
|---|---:|
| first boundary fracture | PIDL `j=11` |
| confirmed stop | PIDL `j=14` |
| FEM target | `N_f=69` |
| learned `alpha_T` | collapsed to lower bound `0.05` from about `j=5` onward |

This is not material recovery.  It is parameter compensation: the inverse
problem finds the cheapest scalar route by pushing `alpha_T` to its lower bound
and forcing a premature damage path.

## Raw/Active Split

Posthoc command produced:

```text
SENS_tensile/run_logs/inverse_alphaT_femmesh_softHist0_raw_active_probe.csv
```

Selected ratios on common probes:

| mapping | raw `psi+` tip_2l0 PIDL/FEM | active `g(alpha) psi+` tip_2l0 PIDL/FEM | interpretation |
|---|---:|---:|---|
| FEM c10 -> PIDL j9 | 8.06 | 0.057 | raw energy is high, active driver is killed |
| FEM c12 -> PIDL j11 | 6.20 | 0.167 | near boundary-fracture onset, active remains too low |
| FEM c15 -> PIDL j14 | 4.46 | 0.259 | confirmed-fracture state still active-driver deficient |

The run therefore confirms the user warning: distinguishing raw and degraded
psi is essential.  Looking only at raw `psi+` would suggest PIDL has enough
driver; looking at active `g(alpha)*psi+` shows the coupled damage/degradation
feedback remains wrong.

## Decision

Scalar `alpha_T` inversion is currently ill-posed for this PIDL model.  It can
match or overshoot fracture timing by lowering the fatigue threshold, but it
does not repair the local field mechanism.

Current bottleneck:

```text
active/degraded driver + local fatigue history feedback
not raw psi amplitude alone
not FEM/PIDL mesh alignment
not reverseBC/reference mismatch
not scalar fatigue threshold calibration
```

## Next Use

Do not treat inverse `alpha_T` collapse as a calibrated material parameter.
Use this result as a discriminator:

1. Any future inverse problem must regularise or fix `alpha_T` if the target is
   field-path recovery rather than event-time compensation.
2. Success must be judged by raw/active split, `alpha_bar`, and `Delta E_d`, not
   only by `N_f`.
3. If a future representation-local method repairs active-driver/history
   alignment, rerun the same inverse script as a post-repair identifiability
   check.
