@echo off
set CUDA_VISIBLE_DEVICES=0
set CUBLAS_WORKSPACE_CONFIG=:4096:8
set PYTHONUTF8=1
cd /d C:\Users\xw436\jobs\hq_public_ref_001_r001_stage_20261009\HQ-PUBLIC-REF-001\public_source_runner_r1_20261009
"C:\Users\xw436\pavetrack_env\Scripts\python.exe" runner.py --approval ..\runs\HQ-PUBLIC-REF-001-R001\approval_gpu_server.json --lock data_lock_verified_r1.json --roots ..\runs\HQ-PUBLIC-REF-001-R001\roots_gpu_server.json --output C:\Users\xw436\jobs\HQ-PUBLIC-REF-001-R001 > "C:\Users\xw436\jobs\hq_public_ref_001_r001_stage_20261009\HQ-PUBLIC-REF-001\runs\HQ-PUBLIC-REF-001-R001\scheduled.stdout.log" 2> "C:\Users\xw436\jobs\hq_public_ref_001_r001_stage_20261009\HQ-PUBLIC-REF-001\runs\HQ-PUBLIC-REF-001-R001\scheduled.stderr.log"
echo %ERRORLEVEL% > "C:\Users\xw436\jobs\hq_public_ref_001_r001_stage_20261009\HQ-PUBLIC-REF-001\runs\HQ-PUBLIC-REF-001-R001\scheduled.exitcode.txt"
