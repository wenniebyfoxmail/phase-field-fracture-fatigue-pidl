# HQ-ROAD-UQ-FEAS-001-R001 launch receipt

- Launched: 2026-10-11 23:32:42 Europe/London.
- Producer: `gpu-server`; hostname `D-26-09`; physical GPU 0.
- Scheduled task: `HQ-ROAD-UQ-FEAS-001-R001-20261011`; initial task result `267009` (`0x41301`, running).
- Formal runner PID: 49712. PID 2392 is its `pavetrack_env` parent launcher, not a second run.
- Formal output: `C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001`.
- Stage: `C:\Users\xw436\jobs\hq_road_uq_feas_001_r001_stage_20261011`.
- Task-owned data: `C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011`.
- Runner snapshot: `46c488c9b33f2130a499491d704c8b6276280af18fc328815314446f32b5dc87`.
- Data-lock SHA-256: `7223dfabfbff5087a196c9e0105f4cd4c4cb8a0bb082bdbffb21e7ae5d954435`.
- Producer environment: Python 3.12.14; PyTorch 2.11.0+cu128; CUDA 12.8; NumPy 2.5.2; Pillow 11.3.0; Matplotlib 3.11.2; SciPy 1.18.1.

The CRACK500 outer package was downloaded on the producer from the official author-repository Google Drive target. Its 1,980,983,618-byte package passed the frozen outer SHA-256 before the three required inner archives were extracted. CFD was obtained from the official GitHub codeload endpoint at commit `ed57c2d96754e6c7d105805cd29aeeb3a799f267`. Producer preflight passed all archive hashes, the CFD 118-pair/236-file aggregate hash, exact inventories, 3/3 synthetic tests and all static contract checks. Road420 was neither transferred nor read.

Initial health: receipt status `running`; epoch 2 completed at roughly 60 seconds with validation mean Dice 0.700460; GPU 0 approximately 3.5 GB and active; stderr empty. This proves only correct launch and early progress, not completion or scientific feasibility.
