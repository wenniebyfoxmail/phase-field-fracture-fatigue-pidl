@echo off
set OMP_NUM_THREADS=8
set MKL_NUM_THREADS=8
set OPENBLAS_NUM_THREADS=8
set PYTHONUNBUFFERED=1
if not exist output mkdir output
whoami > output\execution_identity.txt
runtime\python.exe -u run_diagnostics.py
exit /b %ERRORLEVEL%
