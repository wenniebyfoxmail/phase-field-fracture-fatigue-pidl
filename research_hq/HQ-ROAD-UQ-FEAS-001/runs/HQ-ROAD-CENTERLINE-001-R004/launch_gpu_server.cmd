@echo off
set "CUDA_VISIBLE_DEVICES=0"
set "CUBLAS_WORKSPACE_CONFIG=:4096:8"
set "PYTHONUTF8=1"
set "PYTHONPATH=C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020"
set "HQ_RUN_LAUNCH_ID=HQ-ROAD-CENTERLINE-001-R004-20261021"
set "OMP_NUM_THREADS=4"
set "MKL_NUM_THREADS=4"
set "OPENBLAS_NUM_THREADS=4"
set "NUMEXPR_NUM_THREADS=4"
set "VECLIB_MAXIMUM_THREADS=4"
set "BLIS_NUM_THREADS=4"
set "STAGE=C:\Users\xw436\jobs\hq_road_centerline_001_r004_stage_20261021\HQ-ROAD-UQ-FEAS-001"
cd /d "%STAGE%\centerline_target_r004_20261021"
"C:\Users\xw436\pavetrack_env\Scripts\python.exe" owned_subprocess.py scientific_worker.invocation.json
exit /b %ERRORLEVEL%
