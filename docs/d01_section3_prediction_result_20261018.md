# D01 section3 exploratory prediction result

| Beam / aggregate | Scored forecasts | Persistence MAE | Load secant MAE | State-space MAE |
|---|---:|---:|---:|---:|
| Beam4 | 2 | 0.7002 | 0.3490 | 0.5507 |
| Beam5 | 4 | 0.8518 | 0.8835 | 0.6631 |
| Beam6 | 2 | 2.8730 | 2.4726 | 2.8278 |
| Equal-weight mean across beams | 8 total | 1.4750 | 1.2350 | 1.3472 |

[Detailed result and curves](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/section3_prediction_20261018/README_analysis.md)

Frozen nominal sigma1px,a0.05; all9 sensitivity cases preserved. Main8 prefix forecasts; warm-up3 separate. State-space improves persistence but not load secant overall; best only on Beam5. Physical observation bias and noise calibration remain unresolved. No mask changes or neural training; no MD01 work. Next candidate is a separately frozen prefix-only slope initialization, not executed.
