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
| `fracture_visuals` | optional canonical plotting-style utilities | none | figure generation, experiment output |

`source/*.py` files with the same former module names are compatibility
bridges.  They re-export one packaged implementation so existing SENS runners
continue to work while their own migration is deliberately staged.

The one exception is `source/fem_mechanism_operator.py`.  The D1 matrix lock
hashes that exact source file, so it remains a byte-frozen legacy implementation
rather than a bridge.  `pidl_core.fem_mechanism_operator` is its separately
installable packaged counterpart.  Do not edit or re-bridge the frozen file
unless an owner-authorised D1 lock migration has first been made.

## Import direction

```text
SENS runners -> source compatibility bridges -> stable packages
D1 frozen runner -> byte-frozen source/fem_mechanism_operator.py
fracture_state.spatial_degradation_reconstruction -> pidl_core
```

Package modules must not import an extracted module back through the legacy
`source` root.  `tests/test_package_boundaries.py` enforces this direction,
verifies that mutable legacy bridges export the same representative object as
their package target, and checks the D1-frozen exception against its declared
hash.

## Split acceptance rule

For each future code split:

1. Preserve the former `source` path as a compatibility bridge, except when a
   frozen contract hashes that path; retain the frozen file byte-for-byte in
   that case.
2. Add the new package module and declare any package-level dependency.
3. Extend the affected module's existing fixed test with an identity check for
   a bridge, or a fixed-contract plus package-contract check for a frozen path.
4. Run that affected fixed test plus `tests/test_package_boundaries.py`.
5. Do not migrate a runner covered by a frozen code lock without a separately
   authorised lock migration.
