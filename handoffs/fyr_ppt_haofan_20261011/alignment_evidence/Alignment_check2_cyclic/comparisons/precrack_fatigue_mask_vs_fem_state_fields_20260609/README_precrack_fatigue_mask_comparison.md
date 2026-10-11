# Precrack-Fatigue-Mask PIDL vs FEM State-Field Comparison

Date: 2026-06-09

## Purpose

Compare the finished Taobo PIDL run
`pf_precrack_fatigue_mask_clean_ad085f3_20260608_192326` against the aligned
soft-hist0 FEM state-field export using the same state-timing convention as the
latest alignment comparison.

This is a driver/history comparison, not a full mechanical-field comparison,
because the precrack-mask PIDL element diagnostics do not export strain or
stress fields.

## Sources

PIDL archive:

```text
Alignment check 2/PIDL cyclic 012/cases/precrack_fatigue_mask_ad085f3_20260608/raw_archive/
```

PIDL log:

```text
Alignment check 2/PIDL cyclic 012/cases/precrack_fatigue_mask_ad085f3_20260608/logs/precrack_fatigue_mask_current_active_u012.log
```

FEM reference:

```text
Alignment check 2/FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/
```

## State Mapping

PIDL used explicit substeps:

```text
[0.25, 0.5, 0.75, 1.0, 0.0]
```

The comparison maps:

```text
c1_peak      -> PIDL step 0003
c1_unloaded  -> PIDL step 0004
c2_peak      -> PIDL step 0008
c2_unloaded  -> PIDL step 0009
c3_peak      -> PIDL step 0013
c3_unloaded  -> PIDL step 0014
c20_peak     -> PIDL step 0098
c20_unloaded -> PIDL step 0099
c40_peak     -> PIDL step 0198
c40_unloaded -> PIDL step 0199
c60_peak     -> PIDL step 0298
c60_unloaded -> PIDL step 0299
c69_peak     -> PIDL step 0343
c69_unloaded -> PIDL step 0344
```

PIDL centroids are shifted by `+0.5` in `x` and `y`, then area-averaged from
90,000 PIDL triangles onto 45,000 FEM quadrilateral cells.

## Field Definitions

The PIDL run stores fatigue history as `hist_fat_elem`; this comparison treats
that field as the PIDL counterpart of FEM `alpha_bar_elem`.

Compared fields:

```text
damage:         FEM d_elem                 vs PIDL alpha_elem
alpha_bar:      FEM alpha_bar_elem         vs PIDL hist_fat_elem
f_fatigue:      FEM f_fatigue_elem         vs PIDL f_fatigue_elem
g_stiffness:    FEM g_stiffness_elem       vs PIDL g_alpha_elem
psi_raw:        FEM psi_plus_elem          vs PIDL psi_raw_elem
psi_active:     FEM g_psi_plus_elem        vs PIDL psi_active_elem
history_driver: FEM g_psi_plus_elem        vs PIDL psi_history_driver_elem
```

## Outputs

Figures:

```text
figures/precrack_mask_energy_histories.png
figures/precrack_mask_state_scalar_reductions.png
figures/precrack_mask_residual_fields_peak_states.png
figures/precrack_mask_delta_history_overlap.png
```

Tables:

```text
tables/precrack_mask_state_scalar_reductions.csv
tables/precrack_mask_field_error_metrics.csv
tables/precrack_mask_delta_history_overlap.csv
tables/precrack_mask_mapping_diagnostics.csv
```

## First Read

The scalar history increment integrals are much closer than the older baseline:

```text
c1:        PIDL/FEM Delta alpha_bar integral = 0.888
c1->c20:   PIDL/FEM Delta alpha_bar integral = 0.986
c20->c40:  PIDL/FEM Delta alpha_bar integral = 0.990
c40->c69:  PIDL/FEM Delta alpha_bar integral = 1.045
```

But this does not mean the mechanisms match. The residual-field montage shows
that the spatial placement of history, degradation, raw driver, and active
driver still differs around the crack tip and retained precrack band.

Important caveat: strain/stress residuals are not available in this PIDL
archive, so this package should be read alongside the earlier full
state-field comparison when judging mechanical relaxation.
