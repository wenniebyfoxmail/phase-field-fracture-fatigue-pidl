param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Wheel)
$ErrorActionPreference='Stop'
$lock=Get-Content (Join-Path $Source 'docs/research/S01/S01-E028/runtime_lock.json') -Raw|ConvertFrom-Json
if((Get-Item $Wheel).Name -ne $lock.wheel.name -or (Get-Item $Wheel).Length -ne $lock.wheel.bytes -or (Get-FileHash $Wheel -Algorithm SHA256).Hash.ToLower() -ne $lock.wheel.sha256){throw 'Pillow wheel identity'}
if(Test-Path $lock.overlay){throw 'fresh isolated runtime required; inspect existing state, never overwrite'}
New-Item -ItemType Directory $lock.overlay|Out-Null
& 'C:\Users\xw436\pavetrack_env\Scripts\python.exe' -m zipfile -e $Wheel $lock.overlay
if($LASTEXITCODE -ne 0){throw 'wheel extraction stopped; no producer'}
$env:CUDA_VISIBLE_DEVICES='0';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH=$lock.overlay;$env:PYTHONDONTWRITEBYTECODE='1';$env:MPLBACKEND='Agg'
& 'C:\Users\xw436\pavetrack_env\Scripts\python.exe' (Join-Path $Source 'scripts/pavetrack_target_spatial/runtime_preflight.py')
if($LASTEXITCODE -ne 0){throw 'isolated runtime qualification stopped; no producer'}
& 'C:\Users\xw436\pavetrack_env\Scripts\python.exe' (Join-Path $Source 'tests/pavetrack_target_spatial/raster_fixture.py')
if($LASTEXITCODE -ne 0){throw 'synthetic raster fixture stopped; no producer'}
# This preparation creates only a private Pillow overlay; no Run, model or real data is opened.
