# D01 other-section robustness result

| Beam / score | Original SS | Load extrapolation | Prefix-slope SS |
|---|---:|---:|---:|
| 4 | 1.248 | 2.027 | 1.292 |
| 5 | 1.183 | 0.832 | 1.235 |
| 6 | 0.361 | 0.379 | 0.535 |
| Equal-beam MAE | 0.931 | 1.079 | 1.021 |

Primary: all five additional eligible saved sections; 12 correlated section-targets, three physical beams. Noise and equations fixed; 33 old forecasts reused, 51 newly evaluated on existing widths. Prefix initialization is worse than original in four of five sections. The section-3 advantage is not stable across other sections. Do not replace original SS or tune on these errors.

All-section secondary MAE original/secant/prefix: 1.041/1.134/1.033 px; this tiny difference does not overturn the primary result. No training, new widths/images, mask changes or MD01 work.

Code commit 02356143. Full result: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/other_sections_prefix_20261018/README_analysis.md
