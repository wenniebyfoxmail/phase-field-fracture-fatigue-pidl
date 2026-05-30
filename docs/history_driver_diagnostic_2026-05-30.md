# History-Driver Diagnostic

Date: 2026-05-30

Purpose:

```text
Test whether the strict FEM-mesh PIDL late-cycle history gap is caused by
collapse of the degraded active fatigue driver g(alpha)*psi_raw.
```

This is not a fair FEM-aligned baseline.  FEM and standard PIDL both accumulate
fatigue from a degraded driver.  These branches deliberately change only the
history-driver used to update `alpha_bar`, while leaving the variational energy
and network architecture unchanged.

Implemented runner:

```text
SENS_tensile/run_fem_mesh_history_driver_umax.py
```

Variants:

```text
raw:
  delta alpha_bar = relu(psi_raw_now - psi_raw_prev)

lagged_degraded:
  delta alpha_bar = relu(g(alpha_previous)*psi_raw_now
                         - previous_history_driver)
```

Strict controls:

```text
mesh: meshed_geom_fem_soft_hist0.msh
Umax: 0.12
seed: 1
network: MLP 8x400 TrainableReLU coeff 1.0
disabled: Williams, Fourier, exact BC, local patch, staged heads,
          adaptive sampling, tip weighting, psi hack
```

Launch:

```text
python SENS_tensile/run_fem_mesh_history_driver_umax.py 0.12 \
  --history-driver raw --n-cycles 100 --seed 1

python SENS_tensile/run_fem_mesh_history_driver_umax.py 0.12 \
  --history-driver lagged_degraded --n-cycles 100 --seed 1
```

Gate:

```text
c20/c40/c69 common probes
matched event state
alpha_bar tip2/p99/p999
raw psi tip2
active psi tip2
Delta E_d from c1
right-boundary/event count
```

## Taobo Launch

Code directory:

```text
/mnt/data2/drtao/projects/pidl-history-driver-ddd30da
```

Launched 2026-05-30/31 from commit:

```text
ddd30da Add FEM-mesh history driver diagnostics
```

Jobs:

| Variant | GPU | PID | Log |
|---|---:|---:|---|
| raw | 2 | 3167525 | `/mnt/data2/drtao/projects/pidl-history-driver-ddd30da/SENS_tensile/run_logs/femmesh_histdrv_raw_softHist0_u012_N100_seed1_20260530.log` |
| lagged_degraded | 3 | 3169666 | `/mnt/data2/drtao/projects/pidl-history-driver-ddd30da/SENS_tensile/run_logs/femmesh_histdrv_laggedDegraded_softHist0_u012_N100_seed1_20260530.log` |

Notes:

```text
The first raw launch failed before training because meshed_geom1.msh was absent
from the isolated worktree sync.  The coarse mesh was then copied into the
Taobo code directory and both jobs were relaunched.  At launch verification,
GPU2 and GPU3 each showed ~3.4 GB memory and ~40% utilisation.
```
