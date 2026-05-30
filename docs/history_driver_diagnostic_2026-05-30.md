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
