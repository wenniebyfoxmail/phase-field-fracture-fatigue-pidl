# State Mapping Audit

FEM and PIDL use different counters for the same physical cyclic state.
FEM labels the first physical cycle as `cycle=1` and records the peak
load as cycle substep `4`; PIDL starts the five-substep load sequence at
global step `0`, so the same first-cycle peak is PIDL global step `3`.

Correct PIDL mapping:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

Examples:

```text
c1_peak:      FEM cycle 1 substep 4 -> PIDL global step 3
c1_unloaded:  FEM cycle 1 substep 5 -> PIDL global step 4
c69_peak:     FEM cycle 69 substep 4 -> PIDL global step 343
c69_unloaded: FEM cycle 69 substep 5 -> PIDL global step 344
```

Do not compare FEM `c1_peak` to PIDL step 4. PIDL step 4 is
`c1_unloaded` for this schedule.

The generated residual maps use this mapping, shift PIDL centroids into
the FEM frame with `FEM_x = PIDL_x + 0.5` and `FEM_y = PIDL_y + 0.5`,
then area-average PIDL triangle fields onto the FEM quadrilateral element grid.

Projection summary:

- PIDL points: 90000
- FEM centroids: 45000
- mean PIDL-to-FEM nearest distance: 0.00193513
- p99 nearest distance: 0.00376483
- PIDL triangles per FEM cell: 2 to 2

Generated outputs:

- `tables/state_mapping_audit_fem_pidl.csv`
- `tables/state_mapping_projection_summary.json`
- `tables/fem_pidl_state_mapped_residual_metrics.csv`
- `tables/c1_fatigue_driver_mask_audit.csv`
- `tables/precrack_line_region_audit.csv`
- `figures/residual_fields_damage_history_degradation_peak_states.png`
- `figures/residual_fields_energy_drivers_peak_states.png`
- `figures/residual_fields_strain_stress_peak_states.png`
- `figures/fem_pidl_state_mapped_peak_residuals.png`
- `figures/c1_fatigue_driver_mask_audit.png`
