@echo off
set CUDA_VISIBLE_DEVICES=0
set CUBLAS_WORKSPACE_CONFIG=:4096:8
set PYTHONUTF8=1
cd /d C:\Users\xw436\jobs\hq_road_uq_feas_002_r001_stage_20261019\HQ-ROAD-UQ-FEAS-001\d2_public_b_repair_20261019
"C:\Users\xw436\pavetrack_env\Scripts\python.exe" d2_runner.py --approval ..\runs\HQ-ROAD-UQ-FEAS-002-R001\approval_gpu_server.json --lock d2_data_lock.json --trainzip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\traincrop.zip --valzip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\valcrop.zip --testzip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\testdata.zip --gapszip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\GAPs384_raw_img_gt.zip --weights C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\resnet18-f37072fd.pth --cache C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\cache --output C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001 > ..\runs\HQ-ROAD-UQ-FEAS-002-R001\scheduled.stdout.log 2> ..\runs\HQ-ROAD-UQ-FEAS-002-R001\scheduled.stderr.log
echo %ERRORLEVEL% > ..\runs\HQ-ROAD-UQ-FEAS-002-R001\scheduled.exitcode.txt
