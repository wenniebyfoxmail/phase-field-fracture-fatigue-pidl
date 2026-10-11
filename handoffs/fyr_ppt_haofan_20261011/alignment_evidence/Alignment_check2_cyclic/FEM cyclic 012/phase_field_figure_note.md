# FEM phase-field figure note

Generated on 2026-06-07 for the cyclic Umax=0.12 loading-step package.

## Purpose

These figures show the FEM phase-field/damage variable `d` for the key loading-step experiments. They are meant to answer: which FEM loading-step cases actually propagate the precrack to the right boundary, and how does the phase-field state look at the stored initial and event/final states?

## Data source

The figures use the case-local raw FEM HDF5 MATLAB exports:

- `cases/standard/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`
- `cases/n_step_2/raw_data/reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat`
- `cases/n_step_3/raw_data/reverseBC_u12_soft_hist0_nstep3_element_fields_c1_c70.mat`
- `cases/n_step_10/raw_data/reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat`
- `cases/peak_only/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_element_fields_c1_c120.mat`
- `cases/state_timing/raw_data/state_timing_element_fields.mat`

The plotted variable is `d_elem`, using `node_coords` and `connectivity` for FEM mesh patch plots. FEM coordinates were shifted from the handoff `[0,1]` frame into the PIDL-compatible `[-0.5,0.5]` frame.

## Figure outputs

- `figures/key_phase_field/fem_phase_field_initial_and_fracture_final_20260607.png`
- `figures/key_phase_field/fem_phase_field_initial_and_fracture_final_20260607.pdf`
- `figures/key_phase_field/fem_phase_field_state_timing_initial_c1_substeps_20260607.png`
- `figures/key_phase_field/fem_phase_field_state_timing_initial_c1_substeps_20260607.pdf`
- `figures/key_phase_field/fem_standard_phase_field_initial_event_20260607.png`
- `figures/key_phase_field/fem_n_step_2_phase_field_initial_event_20260607.png`
- `figures/key_phase_field/fem_n_step_3_phase_field_initial_event_20260607.png`
- `figures/key_phase_field/fem_n_step_10_phase_field_initial_event_20260607.png`
- `figures/key_phase_field/fem_peak_only_phase_field_initial_event_20260607.png`

## Scope and caveats

- For the main loading-step cases, the earliest stored full-field state is c1, so the montage labels it as `initial stored c1`.
- The separate state-timing figure includes the true c0 state and cycle-1 retained load states.
- FEM standard and n_step10 fracture at c69; n_step2 and n_step3 fracture at c70.
- The peak-only case does not fracture by c120, so its final panel is labelled as a no-fracture final state rather than an event state.
- All panels use the same `d` colour scale from 0 to 1.
