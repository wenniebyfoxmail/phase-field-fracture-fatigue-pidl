$ErrorActionPreference = "Stop"
$base = "C:\Users\xw436\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
$root = "C:\Users\xw436\jobs\censor_diag_20261004_r001"
$runtime = "$root\package\runtime"
New-Item -ItemType Directory -Force $runtime | Out-Null
Copy-Item "$base\*.exe", "$base\*.dll" $runtime
Copy-Item "$base\DLLs" $runtime -Recurse -Force
New-Item -ItemType Directory -Force "$runtime\Lib" | Out-Null
Get-ChildItem "$base\Lib" | Where-Object { $_.Name -ne "site-packages" } | Copy-Item -Destination "$runtime\Lib" -Recurse -Force
Copy-Item "$root\venv\Lib\site-packages" "$runtime\Lib" -Recurse -Force
& "$runtime\python.exe" -c "import torch, scipy, h5py; print(torch.__version__)"
