@echo off
set CUDA_VISIBLE_DEVICES=0
set CUBLAS_WORKSPACE_CONFIG=:4096:8
set PYTHONUTF8=1
cd /d C:\Users\xw436\jobs\hq_road_uq_matrix_001_r001_stage_20261019\HQ-ROAD-UQ-FEAS-001\paired_source_model_matrix_20261019
"C:\Users\xw436\pavetrack_env\Scripts\python.exe" paired_matrix_evaluator.py --approval ..\runs\HQ-ROAD-UQ-MATRIX-001-R001\approval_gpu_server.json --lock matrix_data_lock.json --old-checkpoint C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001\best.pt --new-checkpoint C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001\best.pt --valzip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\valcrop.zip --cfd C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\CFD --gapszip C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\GAPs384_raw_img_gt.zip --old-cfd-csv C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001\cfd_metrics.csv --new-gaps-csv C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001\gaps384_nonempty_metrics.csv --cache C:\Users\xw436\jobs\hq_road_uq_matrix_001_r001_cache_20261019 --output C:\Users\xw436\jobs\HQ-ROAD-UQ-MATRIX-001-R001 > ..\runs\HQ-ROAD-UQ-MATRIX-001-R001\scheduled.stdout.log 2> ..\runs\HQ-ROAD-UQ-MATRIX-001-R001\scheduled.stderr.log
echo %ERRORLEVEL% > ..\runs\HQ-ROAD-UQ-MATRIX-001-R001\scheduled.exitcode.txt
