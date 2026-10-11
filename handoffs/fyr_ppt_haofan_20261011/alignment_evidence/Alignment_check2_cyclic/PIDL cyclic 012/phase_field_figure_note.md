# PIDL phase-field figure note

Generated on 2026-06-07 for the cyclic Umax=0.12 loading-step package.

## Purpose

These figures show the PIDL phase-field variable `alpha` for the key aligned PIDL cases. They are meant to show the initial state, the one-peak baseline post-fracture snapshots, and the available final snapshots for loading-step diagnostics.

## Data source

The one-peak and explicit-cycle figures use case-local `alpha_snapshots/*.npy` files. Each snapshot is stored as columns:

```text
x, y, alpha
```

The FEM-like substep diagnostic also uses `alpha_snapshots/*.npy`; detailed element-level timing exports are additionally available in `raw_data/pidl_state_timing/*.npz`.

## Figure outputs

- `figures/key_phase_field/pidl_one_peak_phase_field_initial_post_fracture_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_initial_post_fracture_20260607.pdf`
- `figures/key_phase_field/pidl_substep_controls_phase_field_initial_final_20260607.png`
- `figures/key_phase_field/pidl_substep_controls_phase_field_initial_final_20260607.pdf`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0000_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0080_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0082_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0083_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0084_20260607.png`
- `figures/key_phase_field/pidl_one_peak_phase_field_c0085_20260607.png`

## Scope and caveats

- The one-peak strict FEM-mesh baseline is plotted at c0, c80, c82, c83, c84, and c85.
- c82 is labelled as the first-hit/post-fracture onset snapshot; c85 is the confirmed fracture snapshot for this archived baseline.
- The explicit-cycle `[0,0.5,1,0.5,0]` run did not fracture by 40 physical cycles, so the control figure shows its initial and final stored snapshots.
- The long FEM-like substep diagnostic is plotted at the initial and final available stored snapshots. It is a diagnostic/control, not the frozen baseline.
- All panels use the same `alpha` colour scale from 0 to 1.
