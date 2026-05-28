# FEM Request: Cyclewise Mechanism Data for PIDL Comparison

Date: 2026-05-28

We have started a definition-aware FEM/PIDL comparison using the reverseBC
u=0.12 FEM handoff. The current FEM data at c40/c70 is useful, but it is not
enough to claim cycle-to-cycle mechanism agreement or disagreement. Please
export cyclewise FEM mechanism data through the available final cycle
(currently c74 for reverseBC u=0.12).

## Main Question

We want to know whether PIDL and FEM make the same crack-growth choice cycle by
cycle:

- where the crack tip is,
- where damage/history/psi concentrate,
- how wide the process zone is,
- how `E_el` relaxes and `E_d` grows,
- whether the fatigue driver and local weakening co-move with the crack tip.

## Required Cyclewise Scalar CSV

Please export one row per available cycle, with consistent definitions:

- `cycle`
- `E_el`, `E_d`, `total_energy`
- `d_max`, `d_mean`, `d_p99`, `d_p999`
- `alpha_bar_monitor_max` from `monitorcycle.dat` if available
- `alpha_bar_elem_max`, `alpha_bar_elem_p999`, `alpha_bar_elem_p99`, `alpha_bar_elem_mean`
- `f_fatigue_min`, `f_fatigue_p001`, `f_fatigue_mean`
- `psi_plus_elem_max`, `psi_plus_elem_p999`, `psi_plus_elem_p99`, `psi_plus_elem_mean`
- `psi_tip_top10_mean`, `psi_nominal_mean`, `Kt_proxy = sqrt(psi_tip_top10_mean / psi_nominal_mean)`
- location `(x,y)` of:
  - max `d`
  - max `alpha_bar_elem`
  - min `f_fatigue_elem`
  - max `psi_plus_elem`
- crack-tip metrics:
  - `x_tip_d095`, `y_tip_d095`
  - `x_tip_d090`, `y_tip_d090`
  - `x_tip_d050`, `y_tip_d050`
- process-zone width metrics near the tip:
  - `width_y_d050_near_tip`
  - `width_y_d090_near_tip`
  - `n_elem_d050_near_tip`
  - `n_elem_d090_near_tip`
- right-boundary penetration diagnostics:
  - `right_boundary_d095_count`
  - `right_boundary_d095_yspan`

For the nominal `Kt` denominator, please use the same proxy as PIDL for now:
element centroids satisfying `abs(y) > 0.3` and `x > -0.3`, unless FEM has a
better established nominal region. If using a different nominal region, record
it explicitly.

## Full Field Export

If storage is acceptable, please export compact per-cycle element fields for all
cycles c1-c74:

- `d_elem`
- `alpha_bar_elem`
- `f_fatigue_elem`
- `psi_plus_elem`
- `element_centroids`
- `element_area`

If all-cycle fields are too large, please export at least:

```text
c1, c10, c20, c30, c40, c50, c60, c70, c74
```

and keep the scalar CSV for every cycle.

## Definition Metadata Needed

Please include a README stating:

- whether `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`, and `psi_plus_elem` are
  Gauss-point values, element means over Gauss points, nodal projections, or
  monitor values;
- whether the fields are peak-loaded, unloaded, post-history-update, or
  post-cycle-end snapshots;
- why `monitorcycle.dat:max_alpha_bar` differs from exported
  `alpha_bar_elem` max;
- mesh node/element counts and whether the mesh is identical to the previous
  reverseBC u=0.12 handoff;
- material and fatigue parameters: `E`, `nu`, `Gc`, `ell`, `alpha_T`, `p`,
  AT1/AT2, split, penalty settings.

## Why This Matters

The current comparison suggests that FEM and PIDL may have similar late crack-tip
position but very different local fatigue-history concentration and local
weakening. We need cyclewise FEM metrics to test whether that is true over the
whole trajectory or only at c40/c70.
