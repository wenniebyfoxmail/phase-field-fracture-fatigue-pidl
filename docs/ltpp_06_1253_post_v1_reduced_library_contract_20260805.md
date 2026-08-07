# LTPP 06-1253 Post-v1 Reduced-Library Identifiability Contract

## Status and boundary

This is an explicitly post-v1 exploratory diagnostic. It cannot overwrite the
frozen v1 result, authorize causal climate claims, or upgrade single-annotator
observations to ground truth.

## Frozen inputs

- The 48 weak systems produced by `ltpp_06_1253_single_annotator_freeze_select_v1`.
- No field-adapter refit and no weak-system regeneration are allowed.

## Frozen reduced libraries

Every family contains the same nuisance baseline:

- `constant`
- `damage`
- `damage_sq`

One forcing family is added at a time:

- `low_temp`: `low_temp_exposure`, `damage_x_low_temp_exposure`
- `temperature_change`: `temp_variation_rate`, `damage_x_temp_variation_rate`
- `precipitation`: `precipitation_rate`, `damage_x_precipitation_rate`

## Frozen checks

For each family across all 48 weak systems:

1. At least 90% of systems must have full normalized column rank.
2. Median normalized condition number must be at most 1e3.
3. P90 normalized condition number must be at most 1e4.
4. Every variable candidate must have median VIF at most 20.
5. Every variable candidate must have P90 VIF at most 50.

VIF excludes the intercept and is calculated by a small high-precision decimal
correlation-matrix inverse to avoid the local BLAS overflow observed in the full
library audit.

## Interpretation

- `IDENTIFIABLE_POST_V1_DIAGNOSTIC` means only that the reduced numerical design
  can separate that family under these frozen weak systems.
- It does not mean the forcing is selected, predictive, physical, or causal.
- Failure identifies a family that should not enter sparse selection in this
  parameterization without additional environments or a redesigned library.
