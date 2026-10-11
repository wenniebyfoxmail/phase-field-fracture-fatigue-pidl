# FEM cyclic 012 full stress/strain export request - 2026-06-08

## Why this is needed

The current FEM cyclic 012 `.mat` files are useful but incomplete for strict
PIDL/FEM mechanism comparison. They export element-mean history fields and
`psi_plus`, but they do not export strain/stress tensors or separate raw
stress from degraded/effective stress. That separation is essential: otherwise
we may compare PIDL `psi_raw` against a FEM quantity that has already been
degraded by `g(d)` and/or `f(alpha_bar)`.

## Current local FEM data

Available now:

- `cases/standard/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`
- `cases/n_step_2/raw_data/reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat`
- `cases/n_step_3/raw_data/reverseBC_u12_soft_hist0_nstep3_element_fields_c1_c70.mat`
- `cases/n_step_10/raw_data/reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat`
- `cases/state_timing/raw_data/state_timing_element_fields.mat`

Current compact all-cycle fields:

- `node_coords`, `connectivity`, `element_centroids`, `element_area`
- `cycles`
- `d_elem`
- `alpha_bar_elem`
- `f_fatigue_elem`
- `psi_plus_elem`

Current cycle-1 state-timing fields:

- `state0_initial_preload_prehistory`
- `cycle1_step1_pre_history_refresh`
- `cycle1_step1_post_history_refresh`
- `cycle1_step2_pre_history_refresh`
- `cycle1_step2_post_history_refresh`
- `cycle1_step3_pre_history_refresh`
- `cycle1_step3_post_history_refresh`
- `cycle1_peak_pre_history_refresh`
- `cycle1_peak_post_history_refresh`
- `cycle1_unloaded_pre_history_refresh`
- `cycle1_unloaded_post_history_refresh`

Important limitation: for cycles beyond c1, the current standard all-cycle MAT
does not separate peak and unloaded states. The old handoff has mixed timing:
`d/alpha_bar/f_fatigue` are end-of-cycle post-history fields, while `psi_plus`
is peak-to-date.

## Requested states

Use the standard FEM cyclic 012 case unless otherwise stated:

```text
state0 initial unloaded prehistory

c1:
  step1, step2, step3, peak, unloaded
  preferably both pre-history-refresh and post-history-refresh for each state

c2, c3, c20, c40, c60, c69:
  peak
  unloaded
  preferably both pre-history-refresh and post-history-refresh
```

At minimum, every exported state should carry:

- `cycle_index`
- `step_index`
- `state_label`
- `load_factor`
- `u_y`
- `is_peak_state`
- `is_unloaded_state`
- `is_pre_history_refresh`
- `is_post_history_refresh`
- `after_damage_solve`
- `after_alpha_bar_update`
- `after_f_fatigue_update`

## Requested field level

Prefer both Gauss-point and element-mean arrays.

Gauss-point arrays should use a shape like:

```text
n_state x n_elem x n_gauss
```

Tensor arrays should use:

```text
n_state x n_elem x n_gauss x component
```

with component order clearly documented as:

```text
[xx, yy, xy]
```

For element means, use:

```text
n_state x n_elem
```

or:

```text
n_state x n_elem x component
```

## Required tensor fields

Strain:

- `epsilon_xx`
- `epsilon_yy`
- `epsilon_xy`
- principal strains, at least `epsilon_1`, `epsilon_2`

Stress, explicitly separated:

- `sigma_raw_xx`, `sigma_raw_yy`, `sigma_raw_xy`
- `sigma_degraded_xx`, `sigma_degraded_yy`, `sigma_degraded_xy`
- `sigma_effective_xx`, `sigma_effective_yy`, `sigma_effective_xy`, if this
  differs from either raw or degraded stress in the GRIPHFiTH convention
- principal raw stresses, at least `sigma_raw_1`, `sigma_raw_2`
- principal degraded/effective stresses, at least `sigma_degraded_1`,
  `sigma_degraded_2`
- von Mises or equivalent stress if available

Definition request:

- `sigma_raw`: stress from the undegraded elastic law, before multiplying by
  damage degradation `g(d)` and fatigue degradation `f(alpha_bar)`.
- `sigma_degraded`: stress after the phase-field damage degradation used in the
  equilibrium solve.
- `sigma_effective`: only use this name if the code has a distinct convention;
  otherwise omit it and state that it is not distinct.

## Required energy and driver fields

Export these separately, with definitions:

- `psi_plus_raw`
- `psi_minus_raw`
- `psi_plus_degraded_by_g`
- `psi_plus_degraded_by_f`
- `psi_plus_degraded_by_f_g`
- `g_d`
- `f_fatigue`
- `g_d_times_psi_plus_raw`
- `f_fatigue_times_g_d_times_psi_plus_raw`
- `d`
- `alpha_bar`

If GRIPHFiTH/AMOR uses a different internal split, export the native names too,
but still provide a README mapping:

```text
native_name -> requested_name -> exact formula
```

## Geometry and quadrature

Export:

- `node_coords`
- `connectivity`
- `element_centroids`
- `element_area`
- `gauss_coords`
- `gauss_weights`
- local Gauss point ordering
- element type, expected Q4
- stress state, expected plane strain

## Output format

Preferred file:

```text
reverseBC_u12_soft_hist0_standard_full_gp_fields_selected_states_YYYYMMDD.mat
```

Preferred companion files:

```text
reverseBC_u12_soft_hist0_standard_full_gp_fields_selected_states_YYYYMMDD.csv
README_reverseBC_u12_soft_hist0_standard_full_gp_fields_selected_states_YYYYMMDD.md
```

The CSV should contain one row per exported state with reductions:

- maxima, p99, p999, mean for each scalar field
- near-tip integrals for `psi_plus_raw`, `g_d*psi_plus_raw`,
  `f*g_d*psi_plus_raw`, `alpha_bar`, and `f_fatigue`
- explicit flags for peak/unloaded/pre-history/post-history timing

## Non-negotiable comparison rule

Do not collapse raw and degraded stress/energy into one variable. For PIDL/FEM
comparison, the key pairing is:

- PIDL `psi_raw` vs FEM `psi_plus_raw`
- PIDL `g(alpha) * psi_raw` vs FEM `g_d * psi_plus_raw`, if comparable
- PIDL fatigue-active driver vs FEM `f_fatigue * g_d * psi_plus_raw`, if that
  is the driver actually used by FEM

If FEM's fatigue accumulator uses a different driver, export that exact driver
as a separate field and document it.
