@echo off
set CUDA_VISIBLE_DEVICES=0
set CUBLAS_WORKSPACE_CONFIG=:4096:8
set PYTHONUTF8=1
cd /d C:\Users\xw436\jobs\hq_road_uq_feas_001_r001_stage_20261011\HQ-ROAD-UQ-FEAS-001
"C:\Users\xw436\pavetrack_env\Scripts\python.exe" runner.py --approval runs\HQ-ROAD-UQ-FEAS-001-R001\approval_gpu_server.json --lock data_lock.json --trainzip C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\traincrop.zip --valzip C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\valcrop.zip --testzip C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\testdata.zip --cfd C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\CFD --cache C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\cache --output C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001 > runs\HQ-ROAD-UQ-FEAS-001-R001\scheduled.stdout.log 2> runs\HQ-ROAD-UQ-FEAS-001-R001\scheduled.stderr.log
echo %ERRORLEVEL% > runs\HQ-ROAD-UQ-FEAS-001-R001\scheduled.exitcode.txt
