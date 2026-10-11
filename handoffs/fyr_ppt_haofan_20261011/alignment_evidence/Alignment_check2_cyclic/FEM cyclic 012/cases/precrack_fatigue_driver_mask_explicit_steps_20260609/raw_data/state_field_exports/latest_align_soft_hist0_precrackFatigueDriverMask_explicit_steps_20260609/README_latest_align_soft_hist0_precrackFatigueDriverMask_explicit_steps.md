# Latest Aligned FEM Precrack-Fatigue-Mask Explicit-Step Export

- Request: Mac Requests 22/23, 2026-06-09: PIDL-equivalent precrack fatigue-driver mask and explicit five-substep export
- Setting: retained-material soft diffuse precrack / hist0 reverseBC; no void slit; no duplicated crack-face nodes
- Loading: cyclic R=0, retained five-substep schedule load=[0.25 0.50 0.75 1.00 0.00], uy=[0.03 0.06 0.09 0.12 0]
- State count: 346
- Audit rows: 21

## Step Mapping

fem_global_step = 5*(cycle - 1) + (substep - 1); c1_peak=3, c1_unloaded=4, c69_peak=343, c69_unloaded=344

## Mask Definition

- Policy: PIDL-equivalent mask_fatigue=true, mask_energy=false; mechanics, displacement, strain, raw psi_plus, and H/fracture history remain unmasked.
- Region: x <= 0.5 and |y - 0.5| <= 2*ell = 0.02
- Mask elements: 5000
- Implementation: Post-refresh fatigue-history state enforcement. The AT1_PENALTY_FATIGUE MEX does not expose separate energy and fatigue-driver inputs; masking strain_en_undgr inside the phase-field solve would also mask the variational damage energy and violate mask_energy=false.

## Definitions

- Raw stress: sigma_raw_gp = C * epsilon_gp, with C the plane-strain elastic matrix.
- Degraded/effective stress: sigma_degraded_effective_gp = sigma_minus_gp + g_stiffness_gp * sigma_plus_gp from the AMOR split used by the FEM equilibrium kernel.
- Fatigue fields: alpha_bar_gp/f_fatigue_gp/masked_Dalpha_gp are post-mask fatigue-history states. raw_alpha_bar_gp/raw_f_fatigue_gp/raw_Dalpha_gp are the unmasked refresh candidate stored for audit.
- Existing VTK warning: GRIPHFiTH L2_PROJECTION VTK sigma is degraded by (1-d)^2 and is not a clean raw stress; use this MAT for raw/degraded separation.

- Storage policy: All 346 states are written as element-mean fields plus nodal u/d and mesh/GP geometry. GP fields are computed during export before element averaging, but full all-state GP tensors are intentionally not written to keep the handoff tractable for OneDrive/Mac.

## Files

- latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat
- latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv
- mesh_geometry.mat
- precrack_fatigue_driver_mask_region_audit.csv
- INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask.m
- INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
- solve_fatigue_fracture.m
- export_latest_align_precrack_mask_explicit_steps.m
- run_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.log
