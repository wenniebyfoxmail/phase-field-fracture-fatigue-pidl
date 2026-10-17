# Stage A5 predeclared oracle active-measure protocol

Date frozen: 2026-08-04

## Hypothesis

Stage A4 made raw environmental forcing nearly orthogonal, but every correction
candidate retained the common envelope `q = d psi_plus`. Weak integration of this
envelope recreated correlations above 0.97. Stage A5 tests whether equal scaling
of both sides of each weak equation by its positive active measure removes this
row-amplitude confound without changing the represented equation.

For weak row `b_i = A_i beta`, compute

`M_i = integral(w_i d psi_plus) / integral(w_i)`

and use

`b_i / max(M_i, f) = (A_i / max(M_i, f)) beta`,

where `f = 0.10` times the median positive active measure in that environment.
No row may be deleted. Candidate columns may not be transformed separately.

## Fixed development case

- Oracle dynamic truth only; no field reconstruction or forecast.
- Existing seed 11 balanced eight-environment design.
- Six selection environments, one internal validation environment, and one
  unused LOSO environment per fold.
- 256 identical weak windows per environment and 24 selection trials.
- Raw and normalized systems use identical rows, selectors, thresholds, splits,
  test functions, and random seeds.

## Gate

All conditions are required:

- row count preserved in every fold;
- normalized maximum candidate correlation at most 0.90;
- effective rank at least 6, condition number at most 1e6, and environment
  leverage at most 0.40;
- normalized median support Jaccard at least 0.90;
- exact true support in at least 6 of 8 folds;
- normalized median pairwise support Jaccard at least 0.70;
- every true-term frequency at least 0.75 and every false-term frequency at
  most 0.45;
- normalized support Jaccard improves over raw by at least 0.15.

## Stop rule and evidence boundary

A failure ends A5. Do not alter the floor, threshold, candidate library, forcing,
or folds and rerun. A pass permits only an independently reviewed reconstructed-
field protocol; it does not permit confirmation seeds, producer training, road
claims, or causal claims. Independent methods review was unavailable when this
oracle diagnostic was frozen and remains mandatory before any next stage.
