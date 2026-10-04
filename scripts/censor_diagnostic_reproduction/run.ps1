$ErrorActionPreference = "Stop"
$env:PATHEXT = ".COM;.EXE;.BAT;.CMD"
$env:SystemRoot = "C:\Windows"
$env:PATH = "C:\Windows\System32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:PYTHONUNBUFFERED = "1"
New-Item -ItemType Directory -Force output | Out-Null
$env:MPLCONFIGDIR = Join-Path (Get-Location) "mplconfig"
New-Item -ItemType Directory -Force $env:MPLCONFIGDIR | Out-Null
& C:/Windows/System32/whoami.exe | Out-File output/execution_identity.txt
Write-Output "Extracting private runtime"
& C:/Windows/System32/tar.exe -xf runtime.zip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Starting numerical diagnostics"
& ./runtime/python.exe -u run_diagnostics.py
exit $LASTEXITCODE
