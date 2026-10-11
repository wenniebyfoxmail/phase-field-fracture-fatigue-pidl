# Probe-Averaged Fatigue Driver Run - 2026-06-09

## Purpose

Test whether PIDL's fatigue-history mismatch is partly caused by reducing the
nonlinear degradation factor as:

```text
g(mean(alpha_nodes)) * psi_raw_elem
```

instead of the more FEM-like element probe reduction:

```text
mean_q[g(alpha_q)] * psi_raw_elem
```

This run changes only the post-fit fatigue-history driver. It does not change
the Deep Ritz variational energy, architecture, mesh, loading amplitude, or
fracture criterion.

## Code

- Branch: `codex/m2s-framework-validation`
- Commit: `0148b7f`
- Runner: `SENS_tensile/run_fem_mesh_probe_driver_umax.py`
- Core hook: `source/compute_energy.py::get_psi_plus_per_elem`

## Taobo Job

| field | value |
|---|---|
| run_id | `pf_probe_driver_clean_0148b7f_20260609_012725` |
| sync mode | `mac-rsync-selected` |
| remote code dir | `/mnt/data2/drtao/wennie/pf_probe_driver_clean_0148b7f_20260609_012725/code` |
| archive root | `/mnt/data2/drtao/pidl_archives/pf_probe_driver_clean_0148b7f_20260609_012725` |
| GPU | `2` |
| PID | `1813014` |
| log | `/mnt/data2/drtao/wennie/pf_probe_driver_clean_0148b7f_20260609_012725/logs/probe_driver_current_active_u012.log` |

Command:

```bash
CUDA_VISIBLE_DEVICES=2 \
PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_probe_driver_clean_0148b7f_20260609_012725 \
/usr/bin/python3 -u run_fem_mesh_probe_driver_umax.py 0.12 \
  --n-cycles-physical 120 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --fracture-confirm-cycles 3 \
  --plot-every 20
```

Confirmed settings from launch log:

- substeps: `[0.25, 0.5, 0.75, 1.0, 0.0]`;
- FEM mesh: `meshed_geom_fem_soft_hist0.msh`;
- history driver: `current_active`;
- reduction: `probe_g_mean`;
- void/precrack mask: disabled;
- diagnostics steps: `[0, 3, 4, 8, 9, 13, 14, 98, 99, 198, 199, 298, 299, 343, 344]`.

## Evaluation Gate

Compare to the strict mapped FEM/PIDL state-field package using:

- `raw_driver = psi+`;
- `active_driver = g * psi+`;
- `fatigue_effective_driver = f * g * psi+`;
- `alpha_bar`, `f(alpha_bar)`, `g(alpha)`, and `Delta alpha_bar`;
- mapped states: state0, c1/c2/c3 peak and unloaded, c20/c40/c60/c69 peak
  and unloaded.

Success would mean `active_driver` and `Delta alpha_bar` move closer to FEM
without only changing N_f bookkeeping.
