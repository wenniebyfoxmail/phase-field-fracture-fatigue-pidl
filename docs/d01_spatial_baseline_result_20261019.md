# D01 spatial baseline comparison result

| 梁 | 主目标数 | 保持空间误差pp | 荷载外推空间误差pp |
|---|---:|---:|---:|
| 4 | 2 | 0.05815 | 0.08643 |
| 5 | 4 | 0.05144 | 0.08250 |
| 6 | 2 | 0.04044 | 0.03686 |
| 三梁等权 | 8 | 0.05001 | 0.06860 |

All8main targets retained,3warmups separate. Raw secant worsens equal-beam weighted spatialL1 by37.17%; improves only the two Beam6targets.8negative cell outputs retained without clipping. All352cell predictions/flags exported. Frozen preparation unchanged; no training/image/mask/new-holdout reads or MD03work.

Code60fa88c8; report: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/spatial_baselines_20261019/README_analysis.md
Next draft (not run, not added to this result): /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/spatial_baselines_20261019/NEXT_DESIGN_DRAFT.md
