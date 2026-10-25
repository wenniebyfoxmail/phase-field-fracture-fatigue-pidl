# Code package boundaries

This file records code ownership and compatibility only.  It does not change
an experiment contract, run a model, or make a scientific claim.

## Stable packages

| Package | Owns | Direct package dependency | Not included |
|---|---|---|---|
| `pidl_core` | deterministic equilibrium kernel, FEM mechanism operator, material properties | none | runners, datasets, training loops |
| `fracture_state` | load/displacement inversion and optional neural spatial degradation reconstruction | `pidl_core` for the neural reconstruction submodule | observation acquisition, runners |
| `fracture_observation` | array/geometry-only crack-observation reconstruction | none | image I/O, datasets, experiment runners |
| `fracture_assimilation` | deterministic declared-channel state updates | none | source acquisition, forecasting, training |

`source/*.py` files with the same former module names are compatibility
bridges.  They re-export one packaged implementation so existing SENS runners
continue to work while their own migration is deliberately staged.

## Import direction

```text
SENS runners -> source compatibility bridges -> stable packages
fracture_state.spatial_degradation_reconstruction -> pidl_core
```

Package modules must not import an extracted module back through the legacy
`source` root.  `tests/test_package_boundaries.py` enforces this direction and
verifies that every legacy bridge exports the same representative object as its
package target.

## Split acceptance rule

For each future code split:

1. Preserve the former `source` path as a compatibility bridge.
2. Add the new package module and declare any package-level dependency.
3. Extend the affected module's existing fixed test with an identity check.
4. Run that affected fixed test plus `tests/test_package_boundaries.py`.
5. Do not migrate a runner covered by a frozen code lock without a separately
   authorised lock migration.
