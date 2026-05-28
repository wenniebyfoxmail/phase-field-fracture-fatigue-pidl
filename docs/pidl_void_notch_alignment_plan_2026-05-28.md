# PIDL Void-Notch Alignment Plan

Date: 2026-05-28

## Why

The FEM/PIDL baseline comparison has a notch-definition confounder:

- FEM initial notch is void.
- PIDL initial notch/pre-crack is a damaged `d=1` region inside the domain.

This changes absolute `E_d` and may affect local fatigue-history accumulation.

## Implemented PIDL Diagnostic

`source/model_train.py` now supports:

```python
fatigue_dict["void_notch_mask"] = {
    "enable": True,
    "x_max": 0.0,
    "half_width": 0.02,
    "mask_energy": True,
    "mask_fatigue": True,
}
```

When enabled, elements satisfying:

```text
x <= x_max and |y| <= half_width
```

are excluded from the variational energy and from fatigue-history accumulation.
This is a void-like diagnostic approximation, not a true internal-free-boundary
geometry.

## Runners

Standard PIDL mesh, void-like notch:

```bash
python SENS_tensile/run_void_notch_mask_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom2.msh \
  --precrack-half-width 0.02 \
  --precrack-x-max 0.0 \
  --fracture-confirm-cycles 3
```

FEM-mesh alignment, void-like notch:

```bash
python SENS_tensile/run_void_notch_mask_umax.py 0.12 \
  --n-cycles 100 \
  --seed 1 \
  --mesh-file meshed_geom_fem_baseline.msh \
  --tag femmesh \
  --precrack-half-width 0.02 \
  --precrack-x-max 0.0 \
  --fracture-confirm-cycles 3
```

`meshed_geom_fem_baseline.msh` was checked against the latest FEM
`mesh_geometry.mat` from the cyclewise handoff and is identical to the freshly
regenerated conversion.

## Evaluation Gate

For each run, compare against FEM c1-c74 using:

- outside-precrack history max/mean,
- outside-precrack `f_min`,
- outside-precrack `psi_plus` max,
- outside-precrack incremental `E_d`,
- crack-tip x,
- field residuals at c10, c40, c70, and near fracture.

Improvement means the outside-precrack history peak and `f_min` move toward FEM,
not merely that the fracture cycle changes.
