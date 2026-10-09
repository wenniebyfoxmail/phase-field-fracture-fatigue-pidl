# HQ-PUBLIC-REF-001-R001 launch receipt

- Recorded: `2026-10-09T16:32:21Z` (`2026-10-09T17:32:21+0100`)
- Producer: `gpu-server`; hostname: `D-26-09`; physical device: GPU 0
- Scheduled task: `HQ-PUBLIC-REF-001-R001-20261009`; state at receipt: Running; task result `267009` (`0x41301`, still running)
- Runner PID from formal receipt: `55280`; the environment's launcher process was also visible as PID `37984`
- Formal remote output: `C:\Users\xw436\jobs\HQ-PUBLIC-REF-001-R001`
- Stage: `C:\Users\xw436\jobs\hq_public_ref_001_r001_stage_20261009`
- Data: `C:\Users\xw436\jobs\hq_public_ref_001_data_20261009`
- Current status: `running`; no result claim is available

## Identity and preflight

- Reviewed runner snapshot: `e17179cba87cf2ae134b7e99d82614c6eacd49bd5c54ef17f000468e03a1347e`
- Data lock: `19f0e55ba20c8758a06f72f3b3300bd25b6821d241b01f690a75777ff3c794d8`
- Remote code tar SHA-256: `6d92f46480584fd63c3e0756a0fddcfa2e6257e1b8ccec0e5f24aa03da17f2e7`
- Remote data tar SHA-256: `7c8688e8554c866efc6a5ea85a650abc1fd1d335a4b9f4c503433c88d474ee90`
- Producer environment: Python 3.12.14; PyTorch 2.11.0+cu128; NumPy 2.5.2; Pillow 11.3.0; Matplotlib 3.11.2; CUDA 12.8
- Producer synthetic suite: 9/9 passed
- Producer file-level data-lock validation: 816/816 rows passed
- Approval gate: passed with `CUDA_VISIBLE_DEVICES=0`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, exact hostname, code snapshot, data lock and environment
- Immediate pre-launch GPU check: GPU 0 approximately 310 MiB, 0% utilisation, no model-training Python process; output path absent

## Initial health evidence

The formal runner created `receipt.json` with status `running`, exact snapshot, exact lock, hostname `D-26-09`, GPU `0`, and PID `55280`. GPU 0 subsequently held approximately 3725 MiB and was sampled at 57%, 46% utilisation on later checks. PID CPU time increased across checks. Scheduled stderr remained empty. At this receipt time the first epoch had not yet completed, so `selection.json` did not exist. This establishes launch and forward computation only; it does not establish a validated checkpoint, completed run or scientific result.

Hourly read-only monitoring is active through heartbeat `hq`. It must not create a duplicate run or change code, data, estimands, budgets or stopping rules. On success it retrieves and hashes the result, checks the fixed 438-image final inventory and the 355/3 BuildCrack reference cohorts, performs a claim audit, records the final go/no-go and pauses itself. On failure or budget-limited uncertainty it records the concrete state and pauses.
