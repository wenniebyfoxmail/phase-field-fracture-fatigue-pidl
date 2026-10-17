# D01 fixed-mask measurement exploration

Scope: same six D01 images and refined_v3 masks; no inference, training, forecasts or MD01 work.

Command:
```sh
/Users/wenxiaofang/miniconda3/bin/python3 scripts/d01_fixed_mask_measurement_pilot.py --project /Users/wenxiaofang/phase-field-fracture-with-pidl --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fixed_mask_measurement_pilot_20261017
```

Output directory is fresh-only. Preserve the existing result; a rerun must use a new path.

[Analysis and literature assessment](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fixed_mask_measurement_pilot_20261017/README_analysis.md)

[Exact screening contract](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fixed_mask_measurement_pilot_20261017/pilot_contract.json)

[Measurements](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fixed_mask_measurement_pilot_20261017/eligible_measurements.csv)

[Integrity receipt](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016-D01/fixed_mask_measurement_pilot_20261017/receipt.json)

31 existing frozen artifact hashes matched before and after. Eligible area ranges 31,636–48,433 image px²; supported length ranges 1,638.98–4,841.31 image px. These are partial predicted-mask geometry, not physical totals or accuracy estimates. Existing 17 human width references remain systematically narrower; no pooled correction.

Recommendation: common spatial support and known loading/time axis, followed by a small probabilistic state-space observation/evolution model. Published asphalt particle-filter and GP observation-model precedents are screened in the archive; no ready pretrained D01 predictor was established.
