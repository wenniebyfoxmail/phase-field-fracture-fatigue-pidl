# Precrack Fatigue Mask Complete-Export Rerun

Launch date: 2026-06-09

## Purpose

Rerun the retained-precrack PIDL fatigue/history-mask branch with complete
diagnostic exports so the result can be compared against the aligned FEM
state-field reference without missing strain/stress or gradient evidence.

## Hypothesis

Masking fatigue/history update inside the old retained precrack should reduce
the artificial old-crack-band fatigue accumulation question. The diagnostic
gate is not only `N_f`; it is whether the FEM/PIDL mismatch in history,
active driver, incremental damage energy, and mechanics fields is reduced
without breaking the aligned initial state.

## One-Factor Change

Physics and runner settings are the same as the previous precrack-fatigue-mask
run, except diagnostic export is complete:

- element diagnostics include strain and raw/effective stress fields,
- gradient diagnostics record `E_el`, `E_d`, `E_hist` and their gradient norms
  before history refresh at every training step.

Code commit:

```text
630111c diagnostics: export mechanics and gradient traces
```

## Required Exports

```text
alpha, hist_alpha, alpha_bar/hist_fat, f_fatigue, g(alpha)
psi_raw, psi_active, history_driver
E_el, E_d, E_hist
grad_E_el, grad_E_d, grad_E_hist
eps_xx, eps_yy, eps_xy, eps_eq
sigma_raw_*, sigma_effective_*
alpha snapshots
state timing steps: c1/c2/c3/c20/c40/c60/c69 peak and unloaded, plus dense near event
```

Gradient trace file expected:

```text
best_models/energy_gradient_terms_vs_cycle.npy
columns = step,E_el,E_d,E_hist,grad_E_el,grad_E_d,grad_E_hist
```

## FEM Reference

Use the aligned soft-hist0 FEM state-field export:

```text
Alignment check 2/FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/
```

## State Mapping Rule

Compare by state label, not raw cycle number.

```text
state0_initial_unloaded_prehistory = true initial state
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

For example:

```text
c1_peak      -> step 3
c1_unloaded  -> step 4
c69_peak     -> step 343
c69_unloaded -> step 344
```

## Planned Verdict Gate

The run supports the purpose only if it provides a complete archive and improves
or clarifies at least one of:

- initial alignment,
- `Delta alpha_bar` placement and overlap,
- active-driver process-zone distribution,
- `Delta E_d`,
- strain/stress residual fields,
- gradient balance among `E_el`, `E_d`, and `E_hist`.
