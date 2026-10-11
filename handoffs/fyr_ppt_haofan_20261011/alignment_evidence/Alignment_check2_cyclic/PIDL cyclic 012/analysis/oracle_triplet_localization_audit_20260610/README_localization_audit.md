# Oracle Triplet Localization Audit

Purpose:

This is a separate post-hoc localization audit for the three oracle PIDL runs.
It uses the already downloaded archives and the corrected state mapping:

```text
cN_peak -> PIDL step 5*(N-1)+3
```

States audited:

```text
c1_peak, c20_peak, c40_peak, c60_peak, c69_peak
```

Fields audited:

```text
alpha, history/alpha_bar, fatigue depletion, stiffness degradation,
psi_active, eps_yy, sigma_effective_1
```

Method:

- PIDL triangle fields are shifted into the FEM frame with `x+0.5, y+0.5`.
- PIDL triangle fields are area-averaged onto the FEM quadrilateral centroid grid.
- The audit records global maxima, top-1% localization centroids, band means/integrals,
  right-boundary-band evidence, and FEM/PIDL top-1% and top-5% localization overlap.
- For `f_fatigue` and `g(alpha)`, localization means low values, so the score is based
  on depletion/degradation rather than the raw maximum.

Key c69 history evidence:

- FEM c69 history max: `19.5322`
- raw_pidl_g c69 history max: `4943.89`
- active_fem c69 history max: `10.7107`
- delta_alpha_bar c69 history max: `19.5322`

Key interpretation:

- `raw_pidl_g` reaches the FEM fracture timing but with strongly over-amplified history.
- `active_fem` improves early active/history agreement but still does not localize enough
  boundary fracture at c69.
- `delta_alpha_bar` matches history almost exactly, including at c69, but still does not
  reproduce penetration; therefore history magnitude alone is not the missing ingredient.
- The remaining mechanism is the coupled localization loop: stress/strain localization,
  active driver, damage update, stiffness degradation, and next-cycle redistribution.

Mechanism note from the c69 montage:

- `active_fem` and `delta_alpha_bar` both show strong right-side effective-stress
  localization, but their damage/history fields do not convert that right-side
  stress concentration into boundary penetration.
- This points away from "history scalar is missing" and toward the damage solve /
  degradation-feedback part of the loop: the stress field can localize, but the
  irreversible damage/stiffness update does not follow FEM strongly enough.
- `raw_pidl_g` is the opposite failure mode: it forces penetration, but by
  amplifying history far beyond FEM.

Selected c69 top-1% localization IoU:

| run | history IoU | psi_active IoU | sigma_effective_1 IoU |
|---|---:|---:|---:|
| raw_pidl_g | 0.7053 | 0.1674 | 0.0341 |
| active_fem | 0.8948 | 0.1214 | 0.0000 |
| delta_alpha_bar | 1.0000 | 0.0358 | 0.0000 |

Outputs:

- `tables/localization_peak_metrics.csv`
- `tables/process_zone_overlap_metrics.csv`
- `tables/right_boundary_band_metrics.csv`
- `figures/process_zone_overlap_iou.png`
- `figures/localization_peak_and_boundary_metrics.png`
- `figures/c69_peak_localization_montage.png`
