# Data Capability

Status: verified for standard analysis.

| Capability | Source | Status |
|---|---|---|
| true state0 mapped fields | `mapped_state_fields_skill/fields/pidl_state0_initial_unloaded_prehistory.npz` | available |
| c1/c2/c3/c20/c40/c60/c69 peak/unload states | `mapped_state_fields_skill/fields/*.npz` | available, 14 files |
| strain/stress fields | mapped states and element diagnostics | available |
| gradient diagnostics | `best_models/energy_gradient_terms_vs_cycle.npy` | available, shape `(392, 7)` |
| scalar histories | `best_models/*.npy` | available |
| alpha snapshots | `alpha_snapshots/` | available |
| element diagnostics | `element_diagnostics_probe_driver/*.npz` | available, 19 files |
| final checkpoint | `best_models/*.pt` | available |
| exact history-driver field | `element_diagnostics_probe_driver/*` | available at diagnostic steps |

## Field Key Audit

Mapped-state files include:

- `eps_xx_elem`, `eps_yy_elem`, `eps_xy_elem`, `eps_eq_elem`
- `sigma_raw_*`, `sigma_effective_*`, `sigma_g_raw_*`
- `psi_raw_elem`, `psi_active_elem`, `psi_plus_elem`
- alpha/fatigue fields and geometry fields

Element diagnostics additionally include:

- `psi_history_driver_elem`

For this runner, the history-driver mode is `current_active` with `probe_g_mean` reduction. Use element diagnostics when the exact saved history-driver field is required.

## Gradient Diagnostic Audit

`energy_gradient_terms_vs_cycle.npy` columns:

```text
step, E_el, E_d, E_hist, grad_E_el, grad_E_d, grad_E_hist
```

Shape: `(392, 7)`.

First row:

```text
[0, 4.3528058e-04, 4.9963174e-03, 5.8431301e-06,
 124.7709, 83.2597, 61361.5859]
```

Last row:

```text
[391, 4.9827117e-06, 5.5109207e-03, 4.1618982e-06,
 12606.6484, 70.1097, 77498.2813]
```
