# D01 common support and state-space inputs

Exploratory preparation only: same six D01 masks; no segmentation, training, fit, filtering, forecasts or MD01 edits.

[Completed r002 preparation](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/common_support_state_space_inputs_20261017_r002/README_analysis.md)

[Model inputs](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/common_support_state_space_inputs_20261017_r002/state_space_inputs.json)

[Model specification](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/common_support_state_space_inputs_20261017_r002/state_space_model_spec.json)

Command (fresh output only):
```sh
/Users/wenxiaofang/miniconda3/bin/python3 scripts/prepare_d01_state_space_inputs.py --project /Users/wenxiaofang/phase-field-fracture-with-pidl --output <fresh-absolute-output-path>
```

Three per-beam support pairs, 8 paired clear width cuts / 16 measurements. Camera time and force/displacement joins remain nominal, with unknown synchronization error. The 6 images provide 3 specimen-level endpoint transitions; enough for model definition, not independent estimation of bias/process/measurement variance. Existing 14-stage metadata are available, no additional image pixels processed. The previous formal D01 identity result remains unchanged.

Translation/edge sanity checks, common area partitions, source immutability and exact serialization comparisons completed. Code produces the core geometry/metadata/NPZ exports and figures; README, review-page links and Obsidian are local presentation records. The initial incomplete attempt is preserved with a failure receipt; use r002.
