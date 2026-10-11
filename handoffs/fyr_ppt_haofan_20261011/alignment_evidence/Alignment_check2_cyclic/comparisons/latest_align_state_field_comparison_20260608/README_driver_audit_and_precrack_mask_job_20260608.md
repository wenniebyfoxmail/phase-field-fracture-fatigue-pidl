# Driver Audit And Precrack-Mask Job - 2026-06-08

## Question

Are FEM and PIDL already using the same fatigue-history driver in the retained
soft-precrack benchmark?

Current answer: not safely. The archived PIDL strict run records
`history_driver_mode: active_degraded/current_active`, meaning the fatigue
history increment is driven by `g(alpha_current) * psi_raw_current`. The FEM
field export lets us compare three candidate drivers on the same mapped states:

- `raw`: undegraded tensile energy, `psi_plus` / `psi_raw`.
- `active_g`: degraded active driver, `g(alpha) * psi_plus`.
- `fatigue_active`: fatigue-effective driver, `f(alpha_bar) * g(alpha) * psi_plus`.

## Key Result

In the left retained precrack band, PIDL has larger raw tensile energy than FEM,
but much smaller degraded/active driver:

| cycle | region | driver | FEM area mean | PIDL area mean | PIDL/FEM |
|---:|---|---|---:|---:|---:|
| 1 | left_precrack_band | raw | 63.9208 | 131.711 | 2.0605 |
| 1 | left_precrack_band | active_g | 0.004853 | 0.001297 | 0.2673 |
| 20 | left_precrack_band | raw | 74.7383 | 149.727 | 2.0033 |
| 20 | left_precrack_band | active_g | 0.005880 | 0.000478 | 0.0813 |
| 40 | left_precrack_band | raw | 76.6375 | 167.439 | 2.1848 |
| 40 | left_precrack_band | active_g | 0.015588 | 0.000316 | 0.0202 |
| 69 | left_precrack_band | raw | 72.3062 | 176.965 | 2.4474 |
| 69 | left_precrack_band | active_g | 0.020863 | 0.000166 | 0.0079 |

So the mismatch is not simply that PIDL has too little raw `psi+`. The mismatch
appears after degradation is applied. In the old precrack band, PIDL's
`g(alpha)` almost switches off the fatigue driver, while FEM still reports
non-trivial active/effective driver there.

## Interpretation

If the initial crack is meant to be an ultimate old crack, then letting
`alpha_bar` and `f(alpha_bar)` continue evolving inside that band is probably
not the clean benchmark. The retained-material variational energy can remain,
but the fatigue-history update inside the initial precrack should be tested as
masked/frozen.

This is different from the old void-notch PIDL diagnostic:

- old void-like mask: `mask_energy=True`, `mask_fatigue=True`;
- new retained precrack mask: `mask_energy=False`, `mask_fatigue=True`.

## New Taobo Job

Runner added in Git:

`upload code/SENS_tensile/run_fem_mesh_precrack_fatigue_mask_umax.py`

Commits:

- `4905a70` adds the runner.
- `ad085f3` shortens archive directory names after the first launch failed
  before training due to filesystem filename length.

Running job:

| field | value |
|---|---|
| run_id | `pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326` |
| commit | `ad085f3` |
| branch | `codex/m2s-framework-validation` |
| sync mode | `mac-rsync-selected` |
| remote code dir | `/mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326/code` |
| archive root | `/mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326` |
| GPU | `2` |
| PID | `1138972` |
| log | `/mnt/data2/drtao/wennie/pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326/logs/precrack_fatigue_mask_current_active_u012.log` |

Command:

```bash
CUDA_VISIBLE_DEVICES=2 \
PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326 \
/usr/bin/python3 -u run_fem_mesh_precrack_fatigue_mask_umax.py 0.12 \
  --n-cycles-physical 120 \
  --seed 1 \
  --mesh-file meshed_geom_fem_soft_hist0.msh \
  --history-driver-mode current_active \
  --fracture-confirm-cycles 3 \
  --plot-every 20
```

Confirmed launch settings from the Taobo log:

- substeps: `[0.25, 0.5, 0.75, 1.0, 0.0]`;
- FEM mesh: `meshed_geom_fem_soft_hist0.msh`;
- history driver: `current_active`;
- precrack mask: `x <= 0.0`, `|y| <= 0.02`;
- `mask_energy=False`;
- `mask_fatigue=True`;
- diagnostics steps: `[0, 3, 4, 8, 9, 13, 14, 98, 99, 198, 199, 298, 299, 343, 344]`.

## Evaluation Gate

When the run finishes, compare against the latest aligned FEM/PIDL archive at
the same mapped states:

- state0, c1/c2/c3 peak and unloaded;
- c20, c40, c60, c69 peak and unloaded where available;
- `alpha`, `alpha_bar`, `f(alpha_bar)`, `g(alpha)`, `psi_raw`,
  `g*psi_raw`, `f*g*psi_raw`;
- `E_el`, `E_d`, `E_irrev`, and gradient norms where available;
- residual fields on the common FEM grid, especially in the old precrack band
  and the current crack-tip/process-zone region.
