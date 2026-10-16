param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256)
$ErrorActionPreference='Stop'
$mp=Join-Path $Source 'docs\research\S01\S01-E012\stage_B\source_manifest.json'
if((Get-FileHash $mp -Algorithm SHA256).Hash.ToLower() -ne $ManifestSha256){throw 'manifest mismatch'}
$m=Get-Content $mp -Raw|ConvertFrom-Json
foreach($p in $m.files.PSObject.Properties){if((Get-FileHash (Join-Path $Source $p.Name) -Algorithm SHA256).Hash.ToLower() -ne $p.Value){throw "source mismatch:$($p.Name)"}}
$r='C:\Users\xw436\pavetrack_runs\S01-E012-R004';$logs=$r+'-wrapper-logs'
if((Test-Path $r) -or (Test-Path $logs)){throw 'fresh run/log dirs required'}
New-Item -ItemType Directory $logs|Out-Null
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$env:CUDA_VISIBLE_DEVICES='1';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:PYTHONPATH='';$env:MPLBACKEND='Agg'
$argsBase=@('--config',"$Source\docs\research\S01\S01-E012\stage_B\run_config.json",'--lock',"$Source\docs\research\S01\S01-E012\stage_B\data_lock.json",'--stage-a','C:\Users\xw436\pavetrack_runs\S01-E012-R002','--cache','C:\Users\xw436\pavetrack_runs\S01-E007-R001','--metadata','C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\development\manifest_train_validation.json','--checkpoint','C:\Users\xw436\pavetrack_runs\S01-E003-R001\best_ranker.pt','--run',$r,'--reviewed-commit',$ReviewedCommit)
try{
 $saved=$ErrorActionPreference
 try{$ErrorActionPreference='Continue';& $py "$Source\scripts\pavetrack_positive_evidence\stage_b.py" @argsBase 1>"$logs\execute_stdout.log" 2>"$logs\execute_stderr.log";$code=$LASTEXITCODE}finally{$ErrorActionPreference=$saved}
 if($code -ne 0){throw "Stage B stopped:$code"}
 Copy-Item "$logs\*" $r
 @{state='completed';reviewed_commit=$ReviewedCommit;wrapper_pid=$PID;completed_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$r\wrapper_receipt.json" -Encoding UTF8
}catch{@{state='stopped';reason=$_.Exception.Message;updated_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8;throw}
