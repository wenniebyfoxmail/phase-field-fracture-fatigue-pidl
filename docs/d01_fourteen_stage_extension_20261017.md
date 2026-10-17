# D01 selected fourteen-stage extension

| Beam | Nominal loading stages (kN) | Images | Adjacent transitions | Fixed sections |
|---|---|---:|---:|---|
| 4 | 10, 30, 40, 50 | 4 | 3 | 3, 6, 9 |
| 5 | 10, 20, 30, 40, 50, 60 | 6 | 5 | 3, 6 |
| 6 | 10, 20, 30, 40 | 4 | 3 | 3, 9, 12 |

[Analysis, figures and inputs](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fourteen_stage_extension_20261017/analysis/README_analysis.md)

Eight new inferences, six old masks/eligibility maps reused exactly. Both checkpoint hashes and 44 retrieved artifacts verified; actual producer PID52616 on D-26-09 GPU0,58.23s,grad count0. No training, fitting, filtering, forecasting or MD01 changes.

Core export: scripts/extend_d01_frozen_stages.py --project <project> --root <prepared14-stage-root>. Plot saved inputs using scripts/plot_d01_stage_observations.py --analysis <analysis-folder>. Fresh-only export folder; preserve completed output.

11 adjacent transitions / 36 widths / 16 existing paired human endpoint values. Clock error, boundary bias, micro-crack omissions and absent metric scale remain flagged. Prepared smallest next test is a one-section load-conditioned development model against persistence; not executed.
