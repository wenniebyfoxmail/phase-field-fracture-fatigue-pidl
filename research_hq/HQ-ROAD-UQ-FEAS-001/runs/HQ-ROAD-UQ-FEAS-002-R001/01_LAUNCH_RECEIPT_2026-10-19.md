# HQ-ROAD-UQ-FEAS-002-R001 launch receipt

- Launched: 2026-10-19 12:25:35 Europe/London.
- Producer: `gpu-server`; hostname `D-26-09`; physical GPU 0.
- Scheduled task: `HQ-ROAD-UQ-FEAS-002-R001-20261019`; initial result `267009` (`0x41301`, running).
- Formal runner PID: `9532`. PID `44400` is the `pavetrack_env` launcher, not a second run.
- Formal output: `C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001`.
- Stage: `C:\Users\xw436\jobs\hq_road_uq_feas_002_r001_stage_20261019`.
- Task-owned data: `C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019`.
- Runner snapshot: `79132eecb1d8d80a486a92475eab7226cf7324cce2d0258fc76254a036cc4b65`.
- Data-lock SHA-256: `ff95bd1e005f8ef3cccde8024eee7da7b4b2fdce338ca2acd6e199b25319a2a0`.
- Producer environment: Python 3.12.14; PyTorch 2.11.0+cu128; torchvision 0.26.0+cu128; CUDA 12.8; NumPy 2.5.2; Pillow 11.3.0; Matplotlib 3.11.2.

Remote preflight passed exact hashes for the three frozen CRACK500 archives, GAPS384 archive and official ResNet18 weights; exact code/data-lock/environment identity; the full 384-pair/382-nonempty GAPS inventory; and the forward/gate checks. It performed zero training or optimizer steps and did not access Road420.

Initial health: the receipt records `run_id=HQ-ROAD-UQ-FEAS-002-R001`, GPU `0`, and `road420_access=false`. Epochs 1–2 completed; epoch 1 validation Dice was 0.711432 and epoch 2 was 0.692296. GPU 0 was active at about 4.2 GiB and 70% utilization, with empty stderr. This confirms a correctly identified live run, not completion or feasibility.
