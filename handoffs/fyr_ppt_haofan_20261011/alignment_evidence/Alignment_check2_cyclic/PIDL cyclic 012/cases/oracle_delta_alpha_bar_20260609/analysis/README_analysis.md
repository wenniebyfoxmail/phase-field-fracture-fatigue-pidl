# Analysis README

This package was regenerated from source data for `oracle_delta_alpha_bar_20260609` after applying
the PIDL run-analysis workflow state-label mapping rule.

## Scope

The local raw PIDL archive, complete diagnostic NPZ exports, gradient trace,
and aligned FEM reference are available. Generated figures and tables were
rebuilt after deleting the previous analysis outputs to avoid counter-label
confusion.

## State Mapping

Compare by state label, not raw cycle number:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

Thus `c1_peak` is FEM cycle 1 substep 4 and PIDL global step 3.
PIDL step 4 is `c1_unloaded`, not `c1_peak`.

## Local Figures And Tables

| Figure | Paired table | Meaning |
|---|---|---|
| `figures/pidl_scalar_histories.png` | `tables/pidl_scalar_trace.csv` | PIDL scalar histories over the run |
| `figures/pidl_energy_terms_over_steps.png` | `tables/pidl_gradient_trace.csv` | PIDL `E_el`, `E_d`, and `E_irres/E_hist` over global steps |
| `figures/pidl_gradient_balance.png` | `tables/pidl_gradient_trace.csv` | Pre-history-refresh energy gradients and gradient ratios |
| `figures/pidl_selected_field_montage.png` | `tables/pidl_selected_state_reductions.csv` | PIDL-only selected fields and reductions |
| `figures/residual_fields_damage_history_degradation_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL damage/history/degradation fields and residuals on the FEM grid |
| `figures/residual_fields_energy_drivers_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL energy-driver fields and residuals on the FEM grid |
| `figures/residual_fields_strain_stress_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL strain/stress fields and residuals on the FEM grid |
| `figures/fem_pidl_state_mapped_peak_residuals.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | Compact mixed FEM/PIDL residual summary using corrected counter mapping |
| `figures/c1_fatigue_driver_mask_audit.png` | `tables/c1_fatigue_driver_mask_audit.csv` | c1 fatigue/history driver comparison in the tip-x0 band and left precrack line band |
| no figure | `tables/precrack_line_region_audit.csv` | Left precrack-line regional audit for all mapped peak states |

## Key Observations

The run reached first boundary hit at step 344 and confirmed fracture at step 344.
Final scalar values are: history max `19.5322`,
history mean `0.345204`, f_min `0.00249197`,
f_mean `0.920031`, and Kt `nan`.

At the confirmed stop, the gradient balance remains history-dominated:

```text
grad_E_hist = 7.158979e+04
grad_E_el   = 0.000000e+00
grad_E_d    = 7.983163e+01
```

For c1 peak after corrected mapping, the fatigue factor itself matches
trivially (`abs_residual_mean = 0`), because both
FEM and PIDL still have fatigue factor 1 at the first peak. The fatigue/history
driver does not exactly match: PIDL mean `0.00680035`
versus projected FEM mean `0.00680035`, with mean
absolute residual `1.74102e-10` and p99 absolute
residual `1.86265e-09`.

For c1 peak, the audit separates the tip-centered `x0` band from the left
precrack line band. In the left precrack line band
`x <= 0.5, |y - 0.5| <= 0.014`, the history-driver means are
PIDL `0.0159985` and FEM
`0.0159985`, with mean absolute
residual `4.87381e-10`.
This is the real FEM/PIDL comparison, not a masked-FEM oracle.

## Remaining Limitations

- PIDL `step0_loaded_audit` is not a verified true unloaded prehistory state.
- PIDL triangle fields are area-averaged onto FEM element cells.
- The peak residual figure is diagnostic; polished manuscript figures should
  still add overlap metrics, unloaded-state panels, incremental energy, and
  fuller mechanics-field interpretation.

<!-- original_vs_state_mapped_residual_audit -->

Additional original-index audit:

- `tables/original_vs_state_mapped_residual_audit.csv`
- `figures/original_vs_state_mapped_residual_audit.png`

This audit compares the corrected state mapping against common wrong raw-index assumptions:
FEM row index as PIDL global step, FEM physical cycle as PIDL global step, and FEM substep
number as PIDL global step. It is included only as a mapping sanity check. The corrected
state-mapped residuals remain the evidence used for FEM/PIDL alignment claims.
