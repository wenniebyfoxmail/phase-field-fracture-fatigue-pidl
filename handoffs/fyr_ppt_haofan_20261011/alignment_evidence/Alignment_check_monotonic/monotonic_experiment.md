# Monotonic Soft-Hist0 FEM/PIDL Experiment

Date: 2026-06-07

## Purpose

This document records the strict monotonic comparison between the latest FEM
soft-hist0 reference and the PIDL all-fine soft-hist0 monotonic runs. The aim is
to check whether the FEM and PIDL settings are aligned, then compare the damage
and energy evolution under monotonic loading to `U=0.2`.

## Experiments Used

### FEM reference

- Fatigue off:
  `Alignment check/FEM monotonic match/cases/umax020_fatigue_off`
- Fatigue on:
  `Alignment check/FEM monotonic match/cases/umax020_fatigue_on`
- Raw VTK handoff:
  `Alignment check/FEM monotonic match/raw_handoff/_pidl_handoff_soft_hist0_monotonic_24vtk_20260607`

### PIDL reference

- Fatigue off:
  `Alignment check/PIDL monotonic/cases/softHist0_allFinePretrain_fatigue_off`
- Fatigue on:
  `Alignment check/PIDL monotonic/cases/softHist0_allFinePretrain_fatigue_on`

The PIDL `standard_pretrain` cases are not used as the main reference because
their coarse pretrain used `meshed_geom1.msh`. They should be treated only as a
coarse-pretrain-history ablation.

## Setting Alignment

### Loading

Both methods use the same monotonic displacement sequence:

```text
0.025, 0.050, 0.075, 0.100, then 0.105:0.005:0.200
```

FEM uses one-based output labels, while PIDL uses zero-based cycle labels. The
aligned comparison rule is:

```text
FEM step = PIDL cycle + 1
```

Examples:

- FEM step 1 = PIDL cycle 0 = `U=0.025`
- FEM step 13 = PIDL cycle 12 = `U=0.145`
- FEM step 24 = PIDL cycle 23 = `U=0.200`

PIDL fatigue-on saved only 23 outputs, ending at PIDL cycle 22 / `U=0.195`.
This is a missing final saved output, not a different loading sequence.

### Mesh and Precrack

The strict PIDL cases use `meshed_geom_fem_soft_hist0.msh` throughout both
coarse and fine stages.

The FEM and PIDL strict references are both retained-material soft diffuse
precrack cases, not the old void/slit-notch format:

- FEM uses a phase-field notch with retained material and a soft AT1-like
  squared-hat profile.
- PIDL uses `hist_alpha_init` with the AT1 squared-hat precrack profile.
- No duplicated crack-face nodes are used in the strict soft-hist0 match.

This is important: in this monotonic match, the "notch" is represented as an
initial phase-field/precrack profile, not as a physical void. The material in
the initial crack corridor is retained. There is no removed slit, no duplicated
crack-face nodes, and no traction-free internal crack boundary.

The coordinate frames differ only by a translation:

- FEM plate coordinates: `[0,1] x [0,1]`
- PIDL plate coordinates: `[-0.5,0.5] x [-0.5,0.5]`

Therefore the same precrack maps as:

- FEM: `x = 0..0.5`, `y = 0.5`
- PIDL: `x = -0.5..0`, `y = 0`

The same soft-hist0 retained-material convention was also used in the strict
cyclic FEM soft-hist0 reverseBC runs. The cyclic setting changes the loading
history and fatigue accumulation; it does not turn the initial notch into a
void for those strict soft-hist0 cases.

### Boundary Conditions

The FEM reference uses reverseBC:

- `fix_X` on top and bottom
- `fix_Y` on bottom
- `disp_Y` on top

The PIDL monotonic runners use the original PIDL BC ansatz with the newer
`exact_bc` / `fem_anchor` branch disabled. For vertical loading this gives:

- `u=0` on top and bottom
- `v=0` on bottom
- `v=lambda` on top

This is compatible with the FEM essential top/bottom displacement constraints.
The older PIDL case folders did not write a clean `bc_mode` metadata line, so
future reruns should keep the new runner metadata fields added in
`run_fem_mesh_monotonic_fatigue_on.py` and
`run_fem_mesh_monotonic_fatigue_off.py`.

## Fatigue-On versus Fatigue-Off under Monotonic Loading

Under monotonic loading, fatigue-on and fatigue-off should be the same because
there is no cyclic fatigue history accumulation.

This is confirmed:

- PIDL fatigue-on/off energy traces are exactly identical over common saved
  steps.
- FEM fatigue-on/off are effectively identical. The very small differences in
  postprocessed energy are numerical/postprocessing differences from the VTK
  field integration, not a separate fatigue trajectory.

Summary from `fatigue_on_off_energy_difference_summary.csv`:

```text
PIDL E_el max |on-off| = 0
PIDL E_d  max |on-off| = 0
FEM  E_el max |on-off| = 4.056e-6
FEM  E_d  max |on-off| = 3.435e-6
```

## Energy Comparison

Generated comparison package:

```text
Alignment check/monotonic_energy_comparison_20260607
```

Key files:

- `fem_pidl_monotonic_Eel_Ed_comparison.csv`
- `fem_pidl_monotonic_Eel_Ed_comparison.png`
- `fem_pidl_monotonic_Eel_Ed_aligned_step_comparison.png`
- `fatigue_on_off_energy_delta.png`
- `compare_fem_pidl_ed_eel.py`

PIDL energies are native `compute_energy` exports.

FEM energies are postprocessed from the 24 VTK fields because the FEM handoff
did not include native scalar energy CSVs:

- FEM `E_el` is integrated from `0.5 * epsilon:sigma`.
- FEM `E_d` uses the PIDL AT1 damage energy form on the FEM `d` field:
  `(w1/c_w) * (d + l0^2 |grad d|^2)`, with `w1=1`, `l0=0.01`, `c_w=8/3`.

This makes the FEM energy trace suitable for diagnostic comparison, but native
FEM scalar energy exports would be preferable for final quantitative reporting.

## Fracture / Collapse Interpretation

There are two useful definitions, and they should not be mixed.

### Full collapse / detected fracture

By the post-collapse state and PIDL boundary-detection criterion, both methods
reach the fracture/collapse state at:

```text
U = 0.145
```

Mapping:

- FEM: step 13, `U=0.145`
- PIDL: cycle 12, `U=0.145`

### First visible softening

The energy traces show that PIDL begins to soften one load step earlier:

- FEM remains high through `U=0.140` and collapses at `U=0.145`.
- PIDL peaks at `U=0.135`, then shows a significant `E_el` drop at `U=0.140`,
  before full collapse at `U=0.145`.

Therefore the most precise statement is:

```text
FEM and PIDL both reach the fully collapsed/detected fracture state at U=0.145,
but PIDL shows earlier pre-collapse softening at U=0.140.
```

## Key Numeric Checkpoints

At the aligned pre-collapse and collapse steps:

| Method | Case | Step/Cycle | U | E_el | E_d |
|---|---|---:|---:|---:|---:|
| FEM | fatigue off | step 12 | 0.140 | 0.006860 | 0.005773 |
| FEM | fatigue off | step 13 | 0.145 | 0.000012 | 0.011059 |
| FEM | fatigue on | step 12 | 0.140 | 0.006864 | 0.005770 |
| FEM | fatigue on | step 13 | 0.145 | 0.000011 | 0.011059 |
| PIDL | fatigue off | cycle 11 | 0.140 | 0.003391 | 0.008199 |
| PIDL | fatigue off | cycle 12 | 0.145 | 0.000016 | 0.010680 |
| PIDL | fatigue on | cycle 11 | 0.140 | 0.003391 | 0.008199 |
| PIDL | fatigue on | cycle 12 | 0.145 | 0.000016 | 0.010680 |

## Main Conclusion

The strict soft-hist0 monotonic FEM/PIDL setup is aligned in loading, mesh
history, precrack format, and essential top/bottom displacement constraints for
the all-fine PIDL cases. Under monotonic loading, fatigue-on/off does not create
a distinct trajectory.

The main physics difference is timing/detail of softening:

- FEM: abrupt collapse between `U=0.140` and `U=0.145`.
- PIDL: pre-collapse softening appears at `U=0.140`, then full collapse at
  `U=0.145`.
