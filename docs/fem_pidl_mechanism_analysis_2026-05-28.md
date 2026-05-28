# FEM/PIDL Mechanism Comparison: ReverseBC u=0.12

Date: 2026-05-28

## Sources

- FEM handoff:
  `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_mechanism_2026-05-28`
- PIDL branch-restart local analysis:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528`
- Key generated table:
  `_analysis_fem_mechanism_20260528/fem_pidl_definition_aware_mechanism_table.csv`
- Key figure:
  `_analysis_fem_mechanism_20260528/figures/fem_pidl_definition_aware_mechanism_bars.png`

## Definition Caveat

The FEM handoff contains two different `alpha_bar` maxima:

- `energy_vs_cycle.csv:max_alpha_bar` is the monitor maximum from `monitorcycle.dat`.
- `fem_mechanism_c40_c70_c80.mat:cycles.alpha_bar_elem` is the element-mean field from `psi_fields/cycle_XXXX.mat`.

These cannot be compared as the same quantity. Use labels such as
`FEM monitor max` and `FEM element-field max`.

For cycles 40 and 70:

| Cycle | FEM monitor max | FEM element-field max | FEM element mean |
|---:|---:|---:|---:|
| 40 | 342.523 | 103.071 | 0.416 |
| 70 | 766.440 | 215.476 | 0.615 |

PIDL `alpha_bar_vs_cycle.npy` stores only max, mean, and `f_min`; it does not
store the full element-history field in the lightweight archive.

## Matched Observations

| Comparison | FEM crack-tip x | PIDL crack-tip x | FEM width | PIDL width | FEM E_el | PIDL E_el | FEM E_d | PIDL E_d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| c40/c45 | 0.184 | 0.200 | 0.0103 | 0.0162 | 0.003174 | 0.003032 | 0.002160 | 0.006582 |
| c70/c75 | 0.425 | 0.432 | 0.0110 | 0.0149 | 0.001162 | 0.001046 | 0.004719 | 0.008285 |

The late crack-tip position is close: by the c70/c75 comparison the difference
is about 0.007 in x. The process-zone width proxy is broader in PIDL by about
30-60% depending on cycle and threshold definition.

The larger mismatch is not position alone. PIDL carries much larger fracture
dissipation energy than FEM at matched points, while elastic energy is similar
or slightly lower. At c70/c75, PIDL `E_d` is about 1.76x FEM.

## Fatigue-History Interpretation

The global history amount is not wildly wrong:

| Comparison | FEM mean history | PIDL mean history |
|---|---:|---:|
| c40/c45 | 0.416 | 0.383 |
| c70/c75 | 0.615 | 0.531 |

The local concentration is very different:

| Comparison | FEM monitor max | FEM element-field max | PIDL max |
|---|---:|---:|---:|
| c40/c45 | 342.523 | 103.071 | 6.627 |
| c70/c75 | 766.440 | 215.476 | 7.675 |

This means the current evidence points to a peak/localization problem, not a
global fatigue-budget problem. PIDL accumulates a comparable domain mean history,
but it does not create FEM-level local history concentration and therefore does
not weaken the most damaged region as much:

| Comparison | FEM min f | PIDL min f |
|---|---:|---:|
| c40/c45 | 2.96e-4 | 1.97e-2 |
| c70/c75 | 2.62e-4 | 1.50e-2 |

## Branch-Restart Result

The c40 and c70 branch-restart tests compared normal warm start, reinitialised
tip head, and reinitialised local alpha row. They returned to nearly the same
crack-front position, width, history max, and energy scale.

Interpretation: the thin/local-field behaviour is unlikely to be solved by a
simple local-head reinitialisation. This points away from pure path trapping and
toward representation/objective/discretisation issues, especially the local
history driver and fatigue degradation concentration.

## Next Best Move

Before another broad GPU sweep, add diagnostics that save full PIDL element
fields at selected cycles:

- `hist_fat_elem`
- `f_fatigue_elem`
- `psi_plus_elem`
- `alpha_elem`
- `E_el_elem`, `E_d_elem`, and optionally per-element residual proxy

Then compare FEM and PIDL using the same reductions: max, p99.9, p99, mean,
near-tip band width, and near-tip integrals. This is the cleanest way to decide
whether the remaining gap is caused by driver definition, mesh/collocation
resolution, or network representation.

## Implemented PIDL Diagnostic Hook

`source/model_train.py` now accepts:

```python
fatigue_dict["element_diagnostics"] = {
    "enable": True,
    "cycles": [40, 70, 75, 80],
    "every_n_cycles": None,
    "dense_sampling": True,
    "on_fracture": True,
}
```

When enabled, each selected cycle writes:

```text
element_diagnostics/element_fields_cycle_XXXX.npz
```

with element coordinates, area, `alpha_elem`, `hist_fat_elem`,
`f_fatigue_elem`, `psi_plus_elem`, `E_el_elem`, `E_d_elem`, `E_hist_elem`, and
`|E_el|+|E_d|` residual proxy. These files are designed to be compared directly
against the FEM element-field handoff using consistent reductions.
