$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\xw436\jobs\censor_projection_20261005_runtime'
if (Test-Path $taskRoot) { throw 'Fresh runtime root already exists' }
New-Item -ItemType Directory $taskRoot | Out-Null
& C:\Windows\System32\tar.exe -xf C:\Users\xw436\jobs\censor_diag_20261004_r001\package\runtime.zip -C $taskRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$taskRoot\runtime\python.exe" -m pip install --upgrade --no-warn-script-location torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128 *> "$taskRoot\install.log"
exit $LASTEXITCODE
