$ErrorActionPreference = "Stop"
$env:OMP_NUM_THREADS = "8"
$env:MKL_NUM_THREADS = "8"
$env:OPENBLAS_NUM_THREADS = "8"
$env:PYTHONUNBUFFERED = "1"
New-Item -ItemType Directory -Force output | Out-Null
whoami | Out-File output/execution_identity.txt
Write-Output "Extracting private runtime"
& C:/Windows/System32/tar.exe -xf runtime.zip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Starting numerical diagnostics"
& ./runtime/python.exe -u run_diagnostics.py
exit $LASTEXITCODE
