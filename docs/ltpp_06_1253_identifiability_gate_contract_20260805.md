# LTPP 06-1253 exploratory identifiability gate

## Status

This gate was introduced after the frozen single-annotator v1 selection result.
It is therefore a post-v1 diagnostic and cannot retroactively replace or
reclassify that result.

## Inputs

- The seven climate-complete survey transitions.
- All 48 frozen weak-system matrices from the v1 perturbation matrix.
- The unchanged nine-term v1 library.

## Frozen thresholds

The full library is structurally eligible for further same-asset exploratory
interpretation only if all conditions pass:

1. The centered and scaled three-column forcing matrix has rank 3.
2. Its maximum absolute pairwise correlation is below 0.95.
3. At least 90% of weak systems have full normalized design rank.
4. The median normalized condition number is at most 1e3.
5. The 90th-percentile normalized condition number is at most 1e4.
6. Every variable candidate has median VIF at most 20.
7. Every variable candidate has 90th-percentile VIF at most 50.
8. Each temporal perturbation window contains at least four distinct forcing
   environments, and the full route contains at least seven.

Constant columns are excluded from VIF because they have zero centered
variance. Failure authorizes only a diagnostic reduced-library design. It does
not authorize threshold tuning, a positive FTS claim, or causal interpretation.
