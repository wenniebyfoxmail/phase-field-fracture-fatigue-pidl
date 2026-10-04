@echo off
set OMP_NUM_THREADS=8
set MKL_NUM_THREADS=8
set OPENBLAS_NUM_THREADS=8
set PYTHONUNBUFFERED=1
C:\Users\xw436\jobs\censor_diag_20261004_r001\venv\Scripts\python.exe -u run_diagnostics.py
exit /b %ERRORLEVEL%
