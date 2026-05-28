# FEM Old-vs-Fine Cyclewise Reference Check

Date: 2026-05-28

## Purpose

Before comparing PIDL against the new fine FEM export, we need to check whether
the FEM reference itself is stable. This note compares the two reverseBC
u=0.12 FEM cyclewise mechanism exports over their common window, c1-c69.

## Inputs

Old FEM cyclewise export:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28/reverseBC_u12_cyclewise_mechanism_metrics.csv
```

New fine FEM cyclewise export:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_fine_reverseBC_u12_cyclewise_mechanism_2026-05-28/fine_reverseBC_u12_cyclewise_mechanism_metrics.csv
```

Generated outputs:

```text
_analysis_fem_mechanism_20260528/fem_old_vs_fine_cyclewise_reference_comparison.csv
_analysis_fem_mechanism_20260528/fem_old_vs_fine_cyclewise_reference_summary.csv
_analysis_fem_mechanism_20260528/figures/fem_old_vs_fine_cyclewise_reference_comparison.png
_analysis_fem_mechanism_20260528/figures/fem_old_vs_fine_cyclewise_reference_comparison.pdf
```

## Mesh / Export Difference

Both exports use the same scalar definitions, but they are not the same mesh:

| FEM export | Cycles | Nodes | Elements | Element type |
|---|---:|---:|---:|---|
| old reverseBC | c1-c74 | 77900 | 77730 | Q4 |
| new fine reverseBC | c1-c69 | 10401 | 10261 | Q4 |

So this is a real FEM reference comparison, not just the same run repackaged.

## Event Timing

| Event | Old FEM | New fine FEM |
|---|---:|---:|
| last exported cycle | 74 | 69 |
| first right-boundary `d >= 0.95` | 74 | 69 |
| first `x_tip_d095 >= 0.49` | 74 | 69 |

The new fine FEM reference reaches the right boundary about five cycles earlier
than the old export.

## Selected Cycle Values

| Cycle | Old `E_el` | Fine `E_el` | Old `E_d` | Fine `E_d` | Old hist max | Fine hist max | Old `f_min` | Fine `f_min` | Old `Kt` | Fine `Kt` | Old `x_tip` | Fine `x_tip` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.004856 | 0.004862 | 5.08e-7 | 2.27e-7 | 1.288 | 0.609 | 4.67e-1 | 7.81e-1 | 12.14 | 8.86 | NaN | NaN |
| 10 | 0.004640 | 0.004680 | 0.000371 | 0.000310 | 29.566 | 8.813 | 3.06e-3 | 2.04e-2 | 467.02 | 154.99 | 0.0182 | 0.0130 |
| 40 | 0.003174 | 0.003121 | 0.002160 | 0.002304 | 103.071 | 80.830 | 2.96e-4 | 5.54e-4 | 1591.51 | 868.75 | 0.1842 | 0.1917 |
| 69 | 0.001249 | 0.000059 | 0.004610 | 0.005589 | 212.334 | 126.288 | 2.62e-4 | 1.65e-4 | 3330.61 | 4101.52 | 0.4142 | 0.4990 |

Median fine/old ratios over c10-c69:

| Metric | Fine / old median |
|---|---:|
| `E_el` | 0.984 |
| absolute `E_d` | 1.065 |
| incremental `E_d` from c1 | 1.065 |
| `alpha_bar_elem_max` | 0.584 |
| `alpha_bar_elem_mean` | 0.896 |
| `f_fatigue_min` | 1.877 |
| `psi_plus_elem_max` | 0.184 |
| `Kt_proxy` | 0.541 |

## Interpretation

The two FEM references agree well on integrated elastic energy for most of the
shared trajectory and are close on integrated damage/fracture energy. This
means the global energy scale is reasonably stable across the two FEM
references.

The local quantities are less stable:

- fine FEM has lower local history peaks for most of the run,
- fine FEM has higher `f_min` during the early/middle part, meaning weaker
  local degradation there,
- fine FEM has much lower `psi_plus_elem_max` and `Kt_proxy` before late
  fracture,
- near the end, fine FEM accelerates and reaches the right boundary by c69,
  while old FEM is still at `x_tip_d095 ~= 0.414` at c69 and reaches the
  boundary at c74.

So the new FEM export should not replace the old one silently. It should be
used as a second FEM reference. Agreement between old and fine FEM on global
energy does not imply agreement on local mechanism amplitudes.

## Consequence For PIDL Comparison

For PIDL, the robust claim is not "match one FEM curve exactly." The safer gate
is:

```text
PIDL should move toward both FEM references in:
  local history concentration,
  minimum f_fatigue,
  incremental E_d,
  crack-tip position,
  and near-tip field shape.
```

The new fine FEM reference makes the PIDL gap less extreme in some local
amplitudes than the old FEM reference, but it also fractures earlier. Therefore
we should report PIDL against both FEM references until the FEM mesh/reference
effect is understood at field level.

## Next Check

The scalar comparison is necessary but not sufficient. The next FEM-to-FEM
check should be a field-level comparison on a common interpolation grid at c10,
c40, and near fracture. Direct elementwise subtraction is not fair because the
two FEM meshes have different element counts and centroids.
