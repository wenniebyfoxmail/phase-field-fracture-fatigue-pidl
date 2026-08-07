# LTPP 06-1253 Climate-Free Baseline Gate

## Purpose

Test whether the frozen single-annotator weak systems can numerically separate a
minimal climate-free temporal library before any new sparse-selection run.

## Frozen candidate library

- `constant`
- `damage`
- `damage_sq`

Climate forcing and all damage-climate interactions are excluded. This does not
assert that climate is physically irrelevant.

## Frozen checks across 48 weak systems

1. Full normalized rank fraction at least 0.90.
2. Median normalized condition number at most 1e3.
3. P90 normalized condition number at most 1e4.
4. Median VIF for every variable term at most 20.
5. P90 VIF for every variable term at most 50.

## Evidence boundary

This remains a post-v1, single-annotator exploratory gate. Passing authorizes
only a climate-free exploratory stability-selection run. It does not establish
a PDE, physical mechanism, ground truth, or causal irrelevance of climate.
