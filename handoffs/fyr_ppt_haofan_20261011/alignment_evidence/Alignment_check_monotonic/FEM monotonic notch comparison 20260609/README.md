# FEM Monotonic Notch Representation Comparison

Date: 2026-06-09

## Purpose

Compare the older FEM monotonic **void/slit notch** package against the newer
FEM monotonic **retained-material soft diffuse precrack / soft-hist0** package.
The comparison asks whether the notch representation changes the monotonic
response, especially peak force and collapse displacement.

## Packages Compared

### Older void/slit-notch monotonic FEM

Folder:

```text
Alignment check/FEM monotonic void notch /
```

Main `Umax=0.2` cases:

```text
Alignment check/FEM monotonic void notch /cases/umax020_fatigue_off
Alignment check/FEM monotonic void notch /cases/umax020_fatigue_on
```

Source script:

```text
Alignment check/FEM monotonic void notch /scripts/INPUT_SENT_PIDL_12_fine_reverseBC_monotonic.m
```

This package imports:

```text
Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp
```

This is the older external Abaqus/PIDL-fine mesh convention with a physical
slit/notch representation. It is the package previously organised under
`FEM monotonic void notch`.

### Newer retained-material soft-hist0 monotonic FEM

Folder:

```text
Alignment check/FEM monotonic match
```

Main `Umax=0.2` cases:

```text
Alignment check/FEM monotonic match/cases/umax020_fatigue_off
Alignment check/FEM monotonic match/cases/umax020_fatigue_on
```

Raw VTK handoff:

```text
Alignment check/FEM monotonic match/raw_handoff/_pidl_handoff_soft_hist0_monotonic_24vtk_20260607
```

This package uses retained material with a soft diffuse precrack / hist0
initialisation. It explicitly states:

- no void slit
- no duplicated crack-face nodes
- no traction-free internal crack boundary
- initial precrack is a soft AT1-like squared-hat damage profile

## Complete Setting Comparison

| Setting | Void/slit-notch monotonic FEM | Retained soft-hist0 monotonic FEM |
|---|---|---|
| Organised folder | `Alignment check/FEM monotonic void notch /` | `Alignment check/FEM monotonic match/` |
| Handoff date | 2026-06-03 package | 2026-06-07 package |
| Geometry convention | Physical slit/void notch in imported Abaqus mesh | Continuous retained-material plate |
| Notch/precrack representation | Void/slit notch; material absent along initial notch | Soft diffuse phase-field precrack / hist0 initial damage |
| Initial crack corridor material | Removed / void-like | Retained |
| Duplicated crack-face/internal free boundary | Slit/void convention from imported mesh | No duplicated crack-face nodes; no internal traction-free boundary |
| FEM mesh source | `SENT_pidl_fine_lh5.inp` via `specimen.external.abaqus_import` | `specimen.internal.plate(... notch_type='phase_field' ...)` |
| Mesh size from VTK | 10,401 nodes, 10,261 quads | 45,591 nodes, 45,000 quads |
| Coordinate frame | Centered SENT mesh, top/bottom at `y=±0.5` | Plate coordinates `[0,1] x [0,1]` |
| Loading | Monotonic, 24 explicit steps to `U=0.2` | Monotonic, same 24 explicit steps to `U=0.2` |
| Step sequence | `0.025, 0.050, 0.075, 0.100, 0.105:0.005:0.200` | Same |
| Boundary condition | reverseBC | reverseBC |
| Essential BC | `fix_X` top+bottom, `fix_Y` bottom, `disp_Y` top | Same |
| Model | `AT1 + AMOR + PENALTY` | Same |
| Material | `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `res_stiff=1e-6` | Same |
| Fatigue-on alpha_T | `0.5` | `0.5` |
| Fatigue-off alpha_T | `1e10` | `1e10` |
| Available VTK output | Peak and final VTKs plus logs/checkpoints | Full 24 VTKs for fatigue-on and fatigue-off |

The main intentional difference is therefore the notch/precrack representation
and the resulting mesh/topology. The loading, BC, phase-field model, material
parameters, and fatigue-on/off labels are otherwise aligned for this monotonic
comparison.

## Result Summary

The load-displacement comparison is generated here:

```text
fem_void_vs_soft_hist0_load_displacement.png
fem_void_vs_soft_hist0_load_displacement.csv
fem_void_vs_soft_hist0_summary.csv
```

### Peak and drop locations

Drop is defined here as the first post-peak step where `F_y < 0.1 * F_peak`.

| Family | Fatigue | Peak step | Peak U | Peak Fy | Drop step | Drop U | Drop Fy |
|---|---|---:|---:|---:|---:|---:|---:|
| Void/slit notch | off | 17 | 0.165 | 0.110845 | 18 | 0.170 | 0.000201698 |
| Void/slit notch | on | 16 | 0.160 | 0.107442 | 17 | 0.165 | 0.000214598 |
| Soft-hist0 retained | off | 12 | 0.140 | 0.0928339 | 13 | 0.145 | 0.000458300 |
| Soft-hist0 retained | on | 12 | 0.140 | 0.0928888 | 13 | 0.145 | 0.000456674 |

## Interpretation

The notch representation makes a large difference under monotonic loading.

The older void/slit-notch model carries load longer and reaches a higher peak:

- fatigue-off peak: `Fy=0.110845` at `U=0.165`
- fatigue-on peak: `Fy=0.107442` at `U=0.160`
- collapse/drop: `U=0.170` for fatigue-off and `U=0.165` for fatigue-on

The retained-material soft-hist0 model collapses earlier:

- fatigue-off peak: `Fy=0.0928339` at `U=0.140`
- fatigue-on peak: `Fy=0.0928888` at `U=0.140`
- collapse/drop: `U=0.145` for both fatigue-off and fatigue-on

So the two notch conventions are not interchangeable. The retained soft-hist0
precrack is already a damaged material band and produces an earlier collapse
than the physical void/slit mesh under the same nominal monotonic loading,
material law, and reverseBC.

## Fatigue-On / Fatigue-Off Observation

In monotonic loading, fatigue-on/off should be nearly the same because there is
no cyclic fatigue-history accumulation. That expectation holds much more
cleanly for the retained soft-hist0 package:

- Soft-hist0 retained: fatigue-on/off peak and drop are essentially identical.
- Void/slit notch: fatigue-on drops one step earlier than fatigue-off. The force
  curves are still close before collapse, but the discrete collapse step differs
  (`U=0.165` versus `U=0.170`).

## Recommendation

Use the retained-material soft-hist0 package for strict comparison with the
current PIDL soft-hist0 monotonic cases.

Use the older void/slit-notch monotonic package only as a notch-representation
ablation. It answers a different question: how much the physical void/slit
topology changes the FEM monotonic response.

