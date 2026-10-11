# Most aligned PIDL vs standard FEM figure note - 2026-06-08

## Purpose

These figures compare the current most aligned PIDL field/front case against the standard FEM case.

The PIDL case selected for field/front alignment is:

```text
cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600
```

This is selected because its stored FEM-like substep alpha snapshots are the
current until-fracture loading-step/timing control against standard FEM.

## Figure outputs

```text
most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.png
most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.pdf
most_aligned_pidl_standard_fem_metrics_20260608.png
most_aligned_pidl_standard_fem_metrics_20260608.pdf
most_aligned_pidl_selection_summary_20260608.csv
```

## Visual convention

The phase-field figure uses a shared centred domain:

```text
x in [-0.5, 0.5], y in [-0.5, 0.5]
```

FEM element centroids were exported in `[0, 1] x [0, 1]`, so both x and y are shifted by `-0.5` before plotting. PIDL alpha snapshots are already centred in `[-0.5, 0.5] x [-0.5, 0.5]`.

Both rows use the same colour scale, `0 <= phase field <= 1`, and the cyan contour marks the high-damage/front threshold 0.95.

## Why the earlier backgrounds looked different

The earlier FEM and PIDL phase-field plots were drawn from different stored field supports: FEM uses element-centroid fields, while PIDL uses nodal alpha snapshots. The earlier FEM visual convention also did not centre both axes consistently. The new figure fixes the visual comparison by using the same centred domain, extent, colour map, and colour limits.

## Why the new FEM fracture does not have the same apparent width as the notch

The plotted FEM crack is a diffuse phase-field damage zone, not a geometric slit. Its visible width depends on the regularisation length `ell=0.01`, the mesh/element display, interpolation, and the colour threshold used for viewing. The notch/precrack is the initial seeded damage region; the propagating fracture should be compared by a threshold contour or front position, not by expecting the coloured band to have the same apparent width as the notch aperture.

## Caveat

The field/front comparison uses the PIDL FEM-like substep snapshots. The energy
panel uses the available aligned FEM/PIDL energy tiers in the organized PIDL
analysis folder, which are sparse at c1, c20, c40, and c69.
