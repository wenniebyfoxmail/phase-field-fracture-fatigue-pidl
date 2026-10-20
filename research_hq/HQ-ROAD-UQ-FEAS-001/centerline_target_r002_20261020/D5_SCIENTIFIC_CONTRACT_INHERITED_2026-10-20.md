# D5 R002 inherited scientific contract — 2026-10-20

`HQ-ROAD-CENTERLINE-001-R002` inherits the complete scientific contract from R001. The only permitted change is the Windows mechanical GPU-process admission rule and the new Run/task/output/cache/stage identity required to preserve R001 as an immutable stopped attempt.

Unchanged scientific elements:

- CRACK500 train/validation only for fitting and checkpoint selection;
- already-consumed CFD and GAPS384 for development evaluation;
- Road420 and CRACK500 test remain sealed;
- D2 ResNet18-UNet with official ImageNet weights, seed `20261011`, 40 epochs, batch 8 and the frozen centreline/distance-field target;
- frozen D1 and D2 checkpoints plus all four D3 metric tables;
- per-source absolute 4-pixel centreline F1 floor, component omission ceiling, paired 2-pixel F1 improvement and bootstrap lower-bound rules;
- scientific advance requires both CFD and GAPS384 to pass every original condition;
- a one-source improvement may be retained only as component evidence and cannot establish general cross-source usability or authorise UQ;
- one scientific attempt; the original non-finite, identity/resource, incomplete-schedule and first-failure stops remain unchanged.

R002 has one zero-start admission check, at most 90 seconds. Known desktop executables are background only when the process still exists, its CIM name and executable path are readable, the CIM name matches the NVIDIA basename, the normalized CIM and NVIDIA paths match exactly, the path matches the narrow reviewed pattern, the GPU UUID matches physical GPU 0, and reported per-process memory is `[N/A]`. Every other row is an unresolved or competing process and stops admission. The raw aggregate GPU row, all raw process rows, query exit codes, exact free memory when parseable and classification evidence are saved on both pass and fail.

The original package clock remains `2026-10-20T21:59:35Z` through `2026-10-21T01:59:35Z`. All R001 preparation, three checks, R002 preparation, admission, execution and retrieval consume that same four-hour envelope. R002 may launch only with at least 1,900 seconds remaining; the runner and scheduled-task time limit are both bounded by the original deadline. Prior D2 completed the comparable full schedule in 0.426 hours.

Resource and producer boundaries remain D-26-09, physical GPU 0 with UUID `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`, at least 16 GiB aggregate free memory, 25 GiB free disk, 4 CPU threads, 32 GiB RSS, 16 GiB CUDA allocated memory and 20 GiB output. No process may be killed or adjusted. No host/GPU switch, second R002 check, scientific retry, new data, public push, publication or external message is authorised.
