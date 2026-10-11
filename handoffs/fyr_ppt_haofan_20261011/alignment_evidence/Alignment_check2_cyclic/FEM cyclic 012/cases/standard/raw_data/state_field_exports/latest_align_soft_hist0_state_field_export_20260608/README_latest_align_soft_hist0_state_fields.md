# Latest Aligned FEM State Field Export

- Request: Mac request 2026-06-08: latest aligned FEM cycles/states with raw vs degraded stress separated
- Setting: retained-material soft diffuse precrack / hist0 reverseBC; no void slit; no duplicated crack-face nodes
- Loading: cyclic R=0, retained steps uy=[0.03 0.06 0.09 0.12 0] after unloading-prune

## Stress Definitions

- Raw stress: sigma_raw_gp = C * epsilon_gp, with C the plane-strain elastic matrix.
- Degraded/effective stress: sigma_degraded_effective_gp = sigma_minus_gp + g_stiffness_gp * sigma_plus_gp from the AMOR split used by the FEM equilibrium kernel.
- Existing VTK warning: GRIPHFiTH L2_PROJECTION VTK sigma is degraded by (1-d)^2 and is not a clean raw stress; use this MAT for raw/degraded separation.

## State Count

- n_state = 18
- states = state0_initial_unloaded_prehistory, c1_step1, c1_step2, c1_step3, c1_peak, c1_unloaded, c2_peak, c2_unloaded, c3_peak, c3_unloaded, c20_peak, c20_unloaded, c40_peak, c40_unloaded, c60_peak, c60_unloaded, c69_peak, c69_unloaded
