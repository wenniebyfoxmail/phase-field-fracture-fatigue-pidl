# History-Driver Discriminator

Date: 2026-06-02 Mac / 2026-06-03 Taobo

## Question

Under the strict FEM-mesh soft-hist0 setting, is PIDL starving the fatigue
history because the coupled cycle-end alpha field kills
`g(alpha) * psi_raw` before the history accumulator sees the local work?

## Code Commit

Mac/GitHub commit:

```text
23402f9 experiment: add history driver discriminator
```

Taobo worktree:

```text
/mnt/data2/drtao/projects/pidl-history-driver-23402f9-20260603
```

The worktree is detached at `23402f9`. Mesh files were copied from the existing
strict-alignment Taobo workspace:

```text
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/meshed_geom1.msh
/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/meshed_geom_fem_soft_hist0.msh
```

## Modes

| mode | history update driver | purpose |
|---|---|---|
| `current_active` | `g(alpha_current) * psi_raw_current` | default PIDL sanity control |
| `lagged_g` | `g(hist_alpha_previous) * psi_raw_current` | tests whether current-cycle alpha relaxation kills the driver too early |
| `raw` | `psi_raw_current` | diagnostic ceiling only; not a proposed physical fatigue law |

The variational energy minimisation is unchanged. Only the post-solve
fatigue-history refresh driver is changed.

## Taobo Launch

Launched from:

```text
/mnt/data2/drtao/projects/pidl-history-driver-23402f9-20260603/SENS_tensile
```

Timestamp:

```text
20260603_011115
```

| mode | GPU | PID | log |
|---|---:|---:|---|
| `current_active` | 2 | 1056279 | `run_logs/femmesh_histDriver_current_active_u012_N100_seed1_20260603_011115.log` |
| `lagged_g` | 3 | 1056280 | `run_logs/femmesh_histDriver_lagged_g_u012_N100_seed1_20260603_011115.log` |
| `raw` | 4 | 1056281 | `run_logs/femmesh_histDriver_raw_u012_N100_seed1_20260603_011115.log` |

Archives:

```text
..._N100_R0.0_Umax0.12_femmesh_softHist0_current_active
..._N100_R0.0_Umax0.12_femmesh_softHist0_lagged_g
..._N100_R0.0_Umax0.12_femmesh_softHist0_raw
```

Element diagnostics are enabled at PIDL saved indices:

```text
0, 1, 2, 19, 39, 68
```

These map to FEM cycles:

```text
c1, c2, c3, c20, c40, c69
```

## Gate

Score against FEM Request21 `n_step=2 [1,0]` and the existing strict reference
protocol. The important gates are:

```text
alpha_bar, Delta alpha_bar, psi_raw, g(alpha), psi_active, Delta E_d
```

at:

```text
c1 / c2 / c3 / c20 / c40 / c69
```

Useful sign:

```text
lagged_g raises Delta alpha_bar and psi_active toward FEM without making raw
driver or damage simply explode at the precrack boundary.
```

Negative sign:

```text
lagged_g/raw only shift N_f or saturate alpha_bar while still failing the
field-level active-driver/history gate.
```
