# D01 prefix-only slope initialization result

| Beam / score | Original SS | Load extrapolation | Prefix-slope SS |
|---|---:|---:|---:|
| 4 | 0.551 | 0.349 | 0.371 |
| 5 | 0.663 | 0.883 | 0.914 |
| 6 | 2.828 | 2.473 | 2.049 |
| Equal-beam MAE | 1.347 | 1.235 | 1.111 |

Same eight main next-observation targets; strip-coordinate px. Initial mean and covariance change coherently, with measurement SD=1 and process acceleration SD=0.05 fixed. First two observations used once. Overall gains are mixed by beam; working bands widen and are not calibrated. No neural training/inference or MD01 edits. Existing 14 masks and original results remain byte-identical.

Code commit: fa9662b9. Local report: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/section3_prefix_slope_init_20261018/README_analysis.md

Next proposed check: freeze the same rules before evaluating other eligible existing sections; no per-beam selection using these errors. No follow-on experiment run.
