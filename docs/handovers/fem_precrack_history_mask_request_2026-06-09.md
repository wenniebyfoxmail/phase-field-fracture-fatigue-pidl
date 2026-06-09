# FEM Request 22 Patch Note: PIDL-Equivalent Precrack Fatigue-Driver Mask

**Date:** 2026-06-09  
**Direction:** Mac-PIDL -> Windows-FEM  
**Purpose:** run a FEM counterfactual that matches the actual PIDL
`mask_fatigue=True, mask_energy=False` mechanism, so we can test whether the
left-precrack-line mismatch is caused by fatigue-driver masking rather than a
PIDL/FEM mechanics error.

## Correction To Earlier Helper

Do **not** use the earlier standalone helper named
`apply_precrack_history_mask.m`. It has been withdrawn because a simple
post-refresh reset can be misunderstood as the whole PIDL mechanism.

The actual PIDL run did not naturally produce a zero old-crack-line fatigue
history. It was launched with an explicit fatigue mask:

```text
runner: run_fem_mesh_precrack_fatigue_mask_umax.py
history_driver_mode: current_active
void_notch_mask: {'enable': True, 'x_max': 0.0, 'half_width': 0.02,
                  'mask_energy': False, 'mask_fatigue': True}
purpose: retained precrack benchmark; variational energy kept,
         fatigue/history masked in the precrack corridor
```

PIDL centered coordinates use:

```text
x <= 0.0 and |y| <= 0.02
```

The corresponding FEM plate-coordinate mask is:

```text
x <= 0.5 and |y - 0.5| <= 0.02
```

Since `ell = 0.01`, this is also `|y - 0.5| <= 2*ell`.

## What PIDL Actually Does

In PIDL, `mask_energy=False` means the retained precrack corridor still remains
in the variational mechanics/fracture energy. Damage and mechanics are **not**
removed from the solve.

With `mask_fatigue=True`, PIDL masks only the fatigue path:

```python
psi_plus_elem[mask] = 0.0
psi_plus_prev[mask] = 0.0
hist_fat = update_fatigue_history(hist_fat, psi_history_elem, psi_plus_prev, ...)
hist_fat[mask] = 0.0
f_fatigue[mask] = 1.0
```

So the masked old precrack line keeps retained damage/mechanics, but cannot
accumulate `hist_fat`/`alpha_bar` or fatigue degradation.

## Required FEM Variant

Start from the strict standard reference:

```text
INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
solve_fatigue_fracture.m
u_max = 0.12
standard five-substep retained schedule [0.25, 0.5, 0.75, 1.0, 0.0]
soft AT1-like retained precrack
initial alpha_bar = 0
initial f_alpha = 1
```

Create a new variant named, for example:

```text
SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask
```

Only change the fatigue-driver/history mask policy. Do not change mesh,
material, loading, BCs, precrack damage profile, `alpha_T`, `ell`, `Gc`,
`tol_irrev`, or residual stiffness.

## FEM Implementation Requirement

The preferred FEM implementation is:

1. Compute/store the raw mechanics and raw `psi_plus` exactly as the standard
   FEM run does.
2. Before the fatigue-history increment is committed, force the fatigue-driver
   increment to zero on the old precrack-line mask.
3. After the history refresh candidate is computed, enforce:

```matlab
history_vars(mask,:,2) = 0.0;  % alpha_bar / fatigue history
history_vars(mask,:,3) = 0.0;  % Dalpha / fatigue increment-like field
history_vars(mask,:,4) = 1.0;  % f_alpha undegraded
```

4. Keep `history_vars(:,:,1)` unchanged if it is the fracture/damage history
   `H`, because PIDL `mask_energy=False` keeps mechanics/fracture energy active.

If GRIPHFiTH's `assembly_pf_fh` does not expose the fatigue-driver input before
history refresh, then the post-refresh enforcement above is acceptable as a
counterfactual for exported `alpha_bar` and `f_alpha`, but the README must say:

```text
fatigue-driver mask implemented as post-refresh state enforcement;
raw unmasked Dalpha/psi_plus also exported for audit
```

## Mask Definition

After `precrack_centroids` is built in the INPUT file, add:

```matlab
precrack_fatigue_driver_mask_enabled = true;
precrack_fatigue_driver_mask_elem = ...
    (precrack_centroids(:,1) <= L_crack + 1e-12) & ...
    (abs(precrack_centroids(:,2) - 0.5) <= 2 * ell + 1e-12);

fprintf('[INPUT] precrack fatigue-driver mask elems = %d (x<=%.3g, |y-0.5|<=%.3g)\n', ...
    nnz(precrack_fatigue_driver_mask_elem), L_crack, 2*ell);

diffuse_precrack_metadata.precrack_fatigue_driver_mask_enabled = ...
    precrack_fatigue_driver_mask_enabled;
diffuse_precrack_metadata.precrack_fatigue_driver_mask = ...
    'PIDL-equivalent: mask_fatigue=True, mask_energy=False on old left precrack line';
diffuse_precrack_metadata.precrack_fatigue_driver_mask_plate = ...
    'x <= 0.5, |y - 0.5| <= 2*ell; mechanics/H/psi kept for audit';
diffuse_precrack_metadata.precrack_fatigue_driver_mask_n_elem = ...
    nnz(precrack_fatigue_driver_mask_elem);
```

## Solver Patch Location

Apply the mask at the converged-substep history refresh point. In the current
solver this is around the call:

```matlab
[~, ~, ~, history_vars_old] = assembly_pf_fh(...
    sys.MESH, sys.DOFS, sys.GEOM.t,...
    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
    p_field, p_field_old, strain_en_undgr,...
    sys.stress_state.as_number,...
    history_vars_old...
);
```

For the counterfactual state, enforce only the fatigue-history slots:

```matlab
if exist('precrack_fatigue_driver_mask_enabled', 'var') && ...
        precrack_fatigue_driver_mask_enabled
    history_vars_old(precrack_fatigue_driver_mask_elem,:,2) = 0.0;
    history_vars_old(precrack_fatigue_driver_mask_elem,:,3) = 0.0;
    history_vars_old(precrack_fatigue_driver_mask_elem,:,4) = 1.0;
end
```

If a raw history candidate is available, please store it separately before this
enforcement so Mac can compare:

```text
raw_alpha_bar_elem / masked_alpha_bar_elem
raw_Dalpha_elem / masked_Dalpha_elem
raw_f_alpha_elem / masked_f_alpha_elem
raw_psi_plus_elem
```

## Exports Required

Please export the same state-field package format as:

```text
latest_align_soft_hist0_state_field_export_20260608
```

Prefer combining this with Request 23 so every converged five-substep state is
saved. At minimum include:

```text
state0_initial_unloaded_prehistory
c1_step1, c1_step2, c1_step3, c1_peak, c1_unloaded
c2_peak, c2_unloaded
c3_peak, c3_unloaded
c20_peak, c20_unloaded
c40_peak, c40_unloaded
c60_peak, c60_unloaded
c69_peak, c69_unloaded
```

Required files:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_state_fields.mat
latest_align_soft_hist0_precrackFatigueDriverMask_state_index.csv
mesh_geometry.mat
precrack_fatigue_driver_mask_region_audit.csv
README_latest_align_soft_hist0_precrackFatigueDriverMask.md
INPUT_*.m
solve_fatigue_fracture.m
export script(s)
run log
```

The MAT should include the same fields as the previous export:

```text
d_elem, alpha_bar_elem, f_fatigue_elem, g_stiffness_elem
psi_plus_elem, g_psi_plus_elem, f_g_psi_plus_elem
epsilon_elem, principal_stress_raw_elem, principal_stress_degraded_effective_elem
sigma_raw_elem, sigma_degraded_effective_elem
element_centroids, element_area
```

Also include raw-vs-masked fatigue diagnostics when available.

## Region Audit CSV

Please include `precrack_fatigue_driver_mask_region_audit.csv` with rows for:

```text
c1_peak, c2_peak, c3_peak, c20_peak, c40_peak, c60_peak, c69_peak
```

and regions:

```text
left_precrack_line_audit: x <= 0.5 and |y - 0.5| <= 0.014
mask_support: x <= 0.5 and |y - 0.5| <= 2*ell
outside_left_precrack_line_audit
```

For each state/region, report:

```text
d_mean, d_max
alpha_bar_mean, alpha_bar_max
f_fatigue_mean, f_fatigue_min
raw_Dalpha_mean, raw_Dalpha_max
masked_Dalpha_mean, masked_Dalpha_max
psi_plus_raw_mean, psi_plus_raw_max
g_psi_plus_raw_mean, g_psi_plus_raw_max
f_g_psi_plus_masked_mean, f_g_psi_plus_masked_max
area, n_elem
```

Expected sanity after the mask:

```text
left_precrack_line_audit alpha_bar_mean approximately 0
left_precrack_line_audit alpha_bar_max  approximately 0
left_precrack_line_audit f_fatigue_mean approximately 1
left_precrack_line_audit f_fatigue_min  approximately 1
masked_Dalpha on the mask approximately 0
raw psi_plus may remain nonzero
```

Raw `psi_plus` may remain nonzero. That is expected because PIDL
`mask_energy=False` keeps mechanics/energy active; only fatigue accumulation is
masked.

## Acceptance Criteria

Mac can accept the FEM package if:

1. Same mesh, material, BCs, loading, soft precrack profile, and stop rule as
   the standard soft-hist0 reference.
2. README states this is a PIDL-equivalent `mask_fatigue=True,
   mask_energy=False` counterfactual.
3. The mask blocks fatigue-history accumulation but does not overwrite damage,
   raw mechanics, raw `psi_plus`, or fracture/damage history `H`.
4. State index uses the same physical labels as the previous aligned export,
   and preferably the explicit Request 23 global-step mapping.
5. Region audit verifies zero/near-zero `alpha_bar`, `Dalpha`, and `f=1` on the
   left precrack line at peak states.
6. Outputs are enough for Mac to run:

```text
PIDL precrack-mask vs original FEM
PIDL precrack-mask vs FEM PIDL-equivalent fatigue-driver-mask oracle
```

## Suggested Output Folder

```text
~/Downloads/_pidl_handoff_v2/latest_align_soft_hist0_precrackFatigueDriverMask_20260609/
```
