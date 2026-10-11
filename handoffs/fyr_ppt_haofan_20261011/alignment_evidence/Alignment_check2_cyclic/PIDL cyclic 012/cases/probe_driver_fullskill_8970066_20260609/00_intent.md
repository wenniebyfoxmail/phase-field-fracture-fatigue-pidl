# probe_driver_fullskill_8970066_20260609

Launch-time case folder.

## Purpose

Rerun `probe_driver_clean_0148b7f_20260609` under the same strict FEM-mesh, soft-hist0, probe-averaged history-driver setting, but with the full diagnostic contract required by the PIDL run-analysis skill.

## One-Factor Change

Compared with the earlier clean probe-driver archive, this rerun keeps the physics/runner intent unchanged and adds missing diagnostics:

- pre-history-refresh gradient balance for `E_el`, `E_d`, and `E_hist`,
- element diagnostics including strain/stress fields,
- post-hoc mapped state exports for `state0`, c1/c2/c3/c20/c40/c60/c69 peak and unloaded states.

## Hypothesis

If the previous mismatch was only a postprocessing blind spot, the full-skill rerun should show the same trajectory but now expose where the mechanism diverges: initial state, early timing, driver update, mechanics relaxation, or gradient balance.

## FEM Reference

Primary reference: Alignment check 2 soft-hist0 FEM state/cyclewise reference, with n_step=2/soft-hist0 used for timing comparisons where needed.

State mapping for five PIDL substeps `[0.25, 0.5, 0.75, 1.0, 0.0]`:

- `cN_peak`: PIDL step `5*(N-1)+3`
- `cN_unloaded`: PIDL step `5*(N-1)+4`
- `state0_initial_unloaded_prehistory`: explicit mapped-state exporter reconstruction, not raw PIDL step 0.

## Required Exports

- `alpha`, `alpha_bar/hist_fat`, `f_fatigue`, `g(alpha)`
- `psi_raw`, `psi_active`, `history_driver`
- `E_el`, `E_d`, `E_hist`
- `grad_E_el`, `grad_E_d`, `grad_E_hist` measured pre-history-refresh
- `eps_xx`, `eps_yy`, `eps_xy`, `eps_eq`
- `sigma_raw_*`, `sigma_effective_*`
- mapped states: `state0`, c1/c2/c3/c20/c40/c60/c69 peak and unloaded states

## Gate

Do not judge by `N_f` alone. The run is useful only if it can support:

- initial alignment audit,
- early c1/c2/c3 timing audit,
- energy and gradient balance over cycles,
- residual field figures for mechanics and driver fields,
- comparison of alpha_bar/history and active driver against FEM.

## Provenance

- Branch: `codex/m2s-framework-validation`
- Commit: `8970066`
- Runner: `SENS_tensile/run_fem_mesh_probe_driver_umax.py`
- Post-hoc exporter: `SENS_tensile/export_pidl_mapped_state_fields.py`
- Training target: Taobo GPU, fresh `/mnt/data2/drtao/wennie/` run directory
- Sync mode: to be filled in `01_monitor.md`
