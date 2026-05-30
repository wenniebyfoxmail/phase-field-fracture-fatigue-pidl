# LBFGS Polish Audit: Strict FEM-Mesh PIDL

Date: 2026-05-30

## Question

Is the late active-driver gap mainly an optimisation-quality problem in the
saved PIDL checkpoints, or does the same frozen history state return to the
same field even after a stronger optimiser polish?

## Setup

Reference archive:

```text
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/..._femmesh_softHist0
```

Mac pulled event checkpoints j68, j84, and j85, patched the polish script to
reconstruct the FEM mesh from `model_settings.txt`, then launched Taobo GPU
polish jobs:

```text
j68 on GPU3
j84 on GPU4
j85 on GPU5
```

Runner:

```text
SENS_tensile/posthoc_lbfgs_polish_audit.py
```

Summary:

```text
_analysis_fem_mechanism_20260528/lbfgs_polish_audit_summary_20260530.csv
_analysis_fem_mechanism_20260528/figures/lbfgs_polish_audit_20260530.png
```

## Result

LBFGS reduced the gradient norm but did not materially change the field or
energy reductions.

| PIDL saved index | grad norm after/before | active psi tip2 after/before | active psi p99 after/before | damage tip2 after/before | E_d after/before |
|---:|---:|---:|---:|---:|---:|
| 68 | 0.464 | 1.0002 | 1.0000 | 1.0000 | 1.0000 |
| 84 | 0.150 | 1.0005 | 1.0025 | 1.0000 | 1.0000 |
| 85 | 0.195 | 1.0006 | 1.0031 | 1.0000 | 1.0000 |

The absolute loss improvement was tiny (`~1e-6`) and the active-driver
diagnostics are effectively unchanged.

## Interpretation

This is a negative optimisation-path discriminator.  The strict FEM-mesh PIDL
event checkpoints are not obviously under-optimised in a way that LBFGS can
repair post hoc.  The large FEM/PIDL active-driver gap is therefore unlikely to
be explained by "RPROP stopped too early" at the saved state.

This supports the current mechanism reading:

```text
raw psi+ can be comparable to FEM,
damage is already saturated near the propagating band,
g(alpha) then nearly extinguishes active psi+ near the tip,
so alpha_bar and Delta E_d stay below FEM.
```

## Next Controlled Branch

The next discriminator should change the training path or representation, not
just polish the final checkpoint:

1. **Staged-alpha strict FEM-mesh run**: same physics and same FEM mesh, but
   add a controlled per-cycle schedule that gives alpha/history its own
   optimisation phase.
2. **Local-first/domain patch strict FEM-mesh run**: port the useful tip-local
   idea onto `run_fem_mesh_umax.py`, not the old sidecar runner, and score it
   with the same c20/c40/c69 and matched-event gates.

Promotion gate:

```text
alpha_bar tip2/p99 improves,
active psi+ tip2/p99 improves,
Delta E_d moves toward FEM,
damage position does not merely over-saturate the right boundary.
```
