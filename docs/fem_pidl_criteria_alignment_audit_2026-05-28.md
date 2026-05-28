# FEM/PIDL Criteria Alignment Audit

Date: 2026-05-28

Purpose: make FEM/PIDL comparison definition-aware before using field residuals
or scalar gaps as mechanistic evidence.

## Baseline-First Diagnostic

The comparison pipeline should start from the finished baseline PIDL run, then
be reused for new reruns. This checks the exporter, mesh mapping, reductions,
and visual conventions before Taobo diagnostic reruns reach the selected cycles.

Baseline archive:

```text
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12
```

Post-hoc PIDL element diagnostics were exported for cycles 40, 70, 75, and 80.
The key baseline result is already informative:

| Quantity | FEM c40 | PIDL c40 | FEM c70 | PIDL c70 |
|---|---:|---:|---:|---:|
| `E_el` | 0.003174 | 0.003386 | 0.001162 | 0.001505 |
| `E_d` | 0.002160 | 0.006018 | 0.004719 | 0.007176 |
| element history max | 103.071 | 7.202 | 215.476 | 8.690 |
| element history mean | 0.416 | 0.229 | 0.615 | 0.345 |
| `f_min` | 2.96e-4 | 1.69e-2 | 2.62e-4 | 1.18e-2 |

Interpretation: the baseline mismatch is not mainly crack-tip position. PIDL
has comparable elastic energy, too much fracture dissipation, much weaker local
history concentration, and much weaker local fatigue degradation.

## Definitions

**Field type** means the physical quantity being compared:

- damage/phase field: FEM `d`, PIDL `alpha`
- fatigue history: FEM `alpha_bar`, PIDL `hist_fat`
- fatigue degradation: FEM/PIDL `f_fatigue`
- tensile energy driver: FEM/PIDL `psi_plus`
- integrated energies: `E_el`, `E_d`, and any history/irreversibility penalty

**Spatial level** means where the value lives before reduction:

- nodal value: value stored at mesh nodes
- Gauss-point value: quadrature-point value inside elements
- element mean: element-level average or representative value
- monitor scalar: solver diagnostic scalar, not necessarily a field reduction
- common-grid value: FEM/PIDL fields interpolated to the same probe grid

**Cycle timing** means when in the nonlinear/load-cycle loop the quantity is
captured:

- loaded peak snapshot
- unloaded/cycle-end snapshot
- post-optimisation but pre-history refresh
- post-history refresh
- monitor value accumulated during the cycle

**Reduction** means how a field becomes a scalar:

- max, p99.9, p99, mean, integral
- location of max or percentile peak
- crack-tip threshold crossing
- process-zone width at a selected threshold
- near-tip or near-crack integral
- boundary count above a threshold

**Event criterion** means the rule used to declare fracture or tip advance:

- damage threshold, e.g. `d > 0.95` or `alpha > 0.95`
- pre-crack exclusion or inclusion
- right-boundary count threshold
- loaded-state versus unloaded-state decision
- monitor max versus exported field max

## Current Alignment Audit

| Quantity | Current FEM source | Current PIDL source | Alignment status | Main caveat |
|---|---|---|---|---|
| damage field | `cycles.d_elem` element field | `alpha_elem` element field | mostly aligned | different meshes; interpolate before residuals |
| fatigue history | `cycles.alpha_bar_elem` element field | `hist_fat_elem` element field | partly aligned | scale/refresh timing still needs exact FEM metadata |
| history monitor max | `energy_vs_cycle.csv:max_alpha_bar` | PIDL history max | not aligned | FEM monitor max is not the same as element-field max |
| fatigue degradation | `cycles.f_fatigue_elem` | `f_fatigue_elem` | mostly aligned | only fair if Carrara law and `alpha_T` are identical |
| tensile driver | `cycles.psi_plus_elem` | `psi_plus_elem` | partly aligned | peak-over-cycle versus recomputed snapshot timing must be checked |
| elastic energy | FEM energy CSV/MAT summary | recomputed PIDL element sum | partly aligned | mesh quadrature and cycle timing differ |
| fracture energy | FEM energy CSV/MAT summary | recomputed PIDL element sum | partly aligned | width/discretisation sensitivity is high |
| crack-tip x | threshold on damage field | threshold on alpha field | usable with caveat | threshold and pre-crack mask must be identical |
| process-zone width | threshold band on damage | threshold band on alpha | usable with caveat | width depends strongly on threshold and interpolation |
| boundary fracture | boundary damage count/monitor | boundary alpha count/monitor | not fully aligned | criterion must be implemented with the same boundary mask |

## Residual-Field Policy

Residual fields are useful, but only after mapping FEM and PIDL onto a common
coordinate/probe grid. The ideal residual is zero everywhere only for a matched
field type with matched timing, spatial level, and reduction.

Recommended residuals:

- damage: `alpha_PIDL - d_FEM`
- history: `log10(1 + hist_PIDL) - log10(1 + alpha_bar_FEM)`
- fatigue degradation: `log10((f_PIDL + eps) / (f_FEM + eps))`
- tensile driver: `log10((psi_PIDL + eps) / (psi_FEM + eps))`
- energies: do not subtract as a field unless both are per-element energy
  densities mapped to the same grid; otherwise compare integrated scalars and
  near-tip integrals.

Do not subtract different field types from each other. For example, do not
subtract damage from history or `psi_plus` from `f_fatigue`. For cross-field
mechanism checks, use co-location plots instead: compare the locations of
max/p99 `alpha`, `psi_plus`, `hist_fat`, and min `f_fatigue`.

## Recommended Visual Package

1. Criteria-audit table:
   field type, spatial level, cycle timing, reduction, and event criterion,
   marked as aligned / partly aligned / not aligned.

2. FEM/PIDL/residual triplets:
   same cycle, same field, same coordinate frame. Use a shared colour scale for
   FEM and PIDL, and a zero-centred diverging scale for residuals.

3. Scalar reduction heatmap:
   rows are quantities, columns are FEM/PIDL/gap; include max, p99.9, p99,
   mean, integral, and location.

4. Event overlay:
   damage field with crack-tip threshold contour, measured tip x, process-zone
   width band, and boundary-count region.

5. Timing diagram:
   show whether each quantity is loaded peak, cycle end, pre-history-refresh,
   post-history-refresh, or monitor accumulated over the cycle.

6. Co-location map:
   overlay locations of max/p99 `psi_plus`, max/p99 history, max damage, and
   min `f_fatigue`. This tests whether the mechanism drivers move together.

## Current Residual Demo

The baseline residual-field demo uses FEM cycles 40 and 70 and baseline PIDL
cycles 40 and 70:

```text
_analysis_fem_mechanism_20260528/figures/baseline_pidl_fem_residual_field_demo.png
_analysis_fem_mechanism_20260528/baseline_pidl_fem_residual_field_demo_metrics.csv
```

The residual fields are useful for diagnosis, but the history and `psi_plus`
panels show interpolation and mesh-level sensitivity. Treat them as a pipeline
test and qualitative mechanism map, not yet as final quantitative evidence.

## Next Requirements From FEM

For a fair cyclewise comparison, FEM should export the same reductions for
every available cycle:

- `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`, `psi_plus_elem`
- `E_el`, `E_d`, total energy, and any fatigue/history energy contribution
- max, p99.9, p99, mean, integral for each field
- x/y location of max or p99.9 for each field
- crack-tip x using the same threshold and pre-crack exclusion
- process-zone width using the same threshold and width rule
- boundary count above fracture threshold
- explicit timing labels for every quantity

The most important audit item is to keep FEM monitor maxima separate from FEM
element-field maxima.
