# LTPP 06-1253 Climate-Free A/B Contract

## Evidence status

Post-v1, single-annotator exploratory model comparison. This experiment does
not modify the frozen v1 selection result and cannot establish a PDE or physical
mechanism.

## Frozen models

- Null: `constant`
- A: `constant + damage`
- B: `constant + damage_sq`

No climate forcing, interaction, threshold search, or sparse support selection
is allowed.

## Paired validation axes

Each model is fit by ordinary least squares on exactly the same rows.

1. Spatial holdout: leave one `spatial_section` out.
2. Trajectory holdout: leave one `trajectory_id` out within each frozen weak
   system and time-window configuration.

Every valid fold must contain at least two training rows and one test row. All
48 frozen weak systems are used.

## Frozen decision rule

For challenger X against reference Y on each validation axis:

- X must have lower RMSE in at least 75% of paired folds; and
- median relative RMSE improvement must be at least 5%.

B wins only if it clears this rule against A on both validation axes and clears
the null on both axes. Otherwise A is selected only if A clears the null on both
axes. If neither condition holds, the decision is `NO_DAMAGE_MODEL_CLEARS_NULL`.

Coefficient sign consistency and coefficient variation are descriptive only and
cannot override the frozen RMSE rule.

## Interpretation boundary

Choosing A or B means only that one pre-specified empirical weak model predicts
held-out frozen observations better. It does not imply that climate is
irrelevant, that `damage` is a physical state variable, or that the selected
term is causal.
