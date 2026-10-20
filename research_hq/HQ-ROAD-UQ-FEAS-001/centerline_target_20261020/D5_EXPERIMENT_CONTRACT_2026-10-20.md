# D5 experiment contract — HQ-ROAD-CENTERLINE-001-R001

## Authority and question

The restored research HQ authorised one complete D5 comparison on 2026-10-20. The question is whether changing only the training target from source-specific raw mask width to a fixed scale-normalised centreline-distance field creates usable cross-source crack localisation on both already-consumed development sources, CFD and GAPS384.

This is a C2 state-measurement experiment against named public published labels. It cannot establish physical crack truth or width, independent-site generalisation, field safety, human-review utility or uncertainty calibration.

## Frozen intervention

- Same CRACK500 train/validation groups and exclusions, D2 ResNet18-UNet/ImageNet initialization, seed 20261011, Adam 1e-3, batch 8, crop 320 and maximum 40 epochs.
- Only the target changes. Skeletonise the published mask on its native grid. Express Euclidean distance at a 512-pixel short side and use `exp(-ln(2)*(d/2)^2)`, zero beyond 8 normalised pixels. Threshold 0.5 is frozen.
- Select the checkpoint only by CRACK500 validation binary centreline-field Dice. No CFD/GAPS result may select a checkpoint, threshold, tolerance or epoch.
- No ensemble, domain adaptation, UQ head, renderer, threshold menu or post-result target change.

## Complete comparison

After the checkpoint is selected, freeze it and deterministically replay the saved D1 scratch and D2 raw-mask checkpoints, then evaluate all three checkpoints under the same probability resize, threshold, skeletonisation and 1/2/4-pixel normalised tolerance transform. Before using either baseline, its native-grid Dice, uncertainty-free mask statistics and 2/4-pixel band-overlap metrics must reproduce the frozen D3 per-image CSVs within `1e-5`. Report each source separately: centreline precision/recall/F1, reference-component omission, predicted-component excess, connectivity counts and empty-reference false positives. D1 is the primary comparator because the already-completed D3 matrix found it had higher 2-pixel tolerant F1 on both sources; D2 remains a fully reported secondary comparator.

## Prospective decision

Let the selected checkpoint's CRACK500 validation mean centreline F1 at 4 pixels be `V4`. For **each** CFD and GAPS384, all conditions are necessary:

1. mean centreline F1 at 4 pixels is at least `max(0.50, 0.60×V4)`;
2. aggregate reference-component omission rate at 4 pixels is at most 0.25;
3. mean centreline F1 at 2 pixels improves over D1 by at least 0.10;
4. the paired 5,000-bootstrap 95% interval for that 2-pixel improvement has lower bound greater than zero.

Only both-source success advances to later selective acceptance. Any miss stops further public-mask architecture/UQ expansion. Raw-mask Dice is secondary and cannot rescue or rank the route. The old 0.75 raw-Dice floor and 0.05 selective-risk rule are not used.

## Resources and stops

Producer is the D2 producer `gpu-server`, hostname `D-26-09`, physical GPU 0 and its isolated `pavetrack_env`. Budget is one run, one GPU, at most 4 wall-clock/GPU hours, 4 CPU threads, 32 GiB RSS, 16 GiB maximum allocated CUDA memory and 20 GiB output. The unique launch identity is `HQ-ROAD-CENTERLINE-001-R001-20261020`; the launcher must set the frozen four-thread OpenMP/MKL/OpenBLAS/NumExpr/VecLib/BLIS environment before Python imports numerical libraries. The missing `scikit-image` dependency may be installed only under the frozen Run-specific path `C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020`, which must be the launcher's `PYTHONPATH`; the shared environment is unchanged. Prior D2 completed the same 40-epoch schedule in 0.426 hours, so no truncated schedule is needed. If admission shows the full schedule cannot fit, do not start.

Two zero-start mechanical rechecks totalling at most 120 seconds are allowed. Once scientific execution begins, the first failure is preserved and stops the run with no retry. A pre-start occupied-resource wait is not a scientific failure, but the agent must not loop on SSH/GPU checks. CRACK500 test, Road420 and every new holdout remain sealed. The approval binds the sole canonical output and cache directories, and every reused cache marker must equal its source archive SHA-256. No paid compute, public push, external publication or new data acquisition is authorised.

