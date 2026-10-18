param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256)
$ErrorActionPreference='Stop'
$mp=Join-Path $Source 'docs\research\S01\S01-E025\source_manifest.json'
if((Get-FileHash $mp -Algorithm SHA256).Hash.ToLower() -ne $ManifestSha256){throw 'manifest mismatch'}
$m=Get-Content $mp -Raw|ConvertFrom-Json
foreach($p in $m.files.PSObject.Properties){if((Get-FileHash (Join-Path $Source $p.Name) -Algorithm SHA256).Hash.ToLower() -ne $p.Value){throw "source mismatch:$($p.Name)"}}
$r='C:\Users\xw436\pavetrack_runs\S01-E025-R001';$logs=$r+'-wrapper-logs'
if((Test-Path $r) -or (Test-Path $logs)){throw 'fresh run/log dirs required'}
if($env:COMPUTERNAME -ne 'D-26-09' -or (whoami) -ne 'ad\xw436'){throw 'producer identity'}
if(@(Get-Process python* -ErrorAction SilentlyContinue).Count -ne 0){throw 'compute conflict'}
$os=Get-CimInstance Win32_OperatingSystem;$load=(Get-CimInstance Win32_Processor|Measure-Object LoadPercentage -Average).Average
if($os.FreePhysicalMemory -lt 8388608 -or $load -ge 50){throw 'CPU/RAM conflict'}
if((Get-PSDrive C).Free -lt 12884901888){throw '12GiB free temporary disk required'}
New-Item -ItemType Directory $logs|Out-Null
$env:CUDA_VISIBLE_DEVICES='1';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH='';$env:MPLBACKEND='Agg'
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$argsBase=@('--config',"$Source\docs\research\S01\S01-E025\run_config.json",'--lock',"$Source\docs\research\S01\S01-E025\data_lock.json",'--source','C:\Users\xw436\pavetrack_runs\S01-E017-R001\delivery\S01-E017-R001-evidence-v1.zip','--metadata','C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\development\manifest_train_validation.json','--run',$r,'--reviewed-commit',$ReviewedCommit)
try{
 $saved=$ErrorActionPreference
 try{$ErrorActionPreference='Continue';& $py "$Source\scripts\pavetrack_controlled_localizer\run.py" @argsBase 1>"$logs\execute_stdout.log" 2>"$logs\execute_stderr.log";$code=$LASTEXITCODE}finally{$ErrorActionPreference=$saved}
 if($code -ne 0){throw "E025 stopped:$code"}
 Copy-Item "$logs\*" $r
 @{state='completed';reviewed_commit=$ReviewedCommit;wrapper_pid=$PID;completed_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$r\wrapper_receipt.json" -Encoding UTF8
}catch{@{state='stopped';reason=$_.Exception.Message;updated_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8;throw}
