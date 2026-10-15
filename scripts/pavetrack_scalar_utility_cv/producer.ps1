param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256,[string]$RunId='S01-E011-R001')
$ErrorActionPreference='Stop'
$mp=Join-Path $Source 'docs\research\S01\S01-E011\source_manifest.json'
if((Get-FileHash $mp -Algorithm SHA256).Hash.ToLower() -ne $ManifestSha256){throw 'reviewed manifest mismatch'}
$m=Get-Content $mp -Raw|ConvertFrom-Json
foreach($p in $m.files.PSObject.Properties){if((Get-FileHash (Join-Path $Source $p.Name) -Algorithm SHA256).Hash.ToLower() -ne $p.Value){throw "source mismatch:$($p.Name)"}}
$r="C:\Users\xw436\pavetrack_runs\$RunId"
$logs="C:\Users\xw436\pavetrack_runs\$RunId-wrapper-logs"
if((Test-Path $r) -or (Test-Path $logs)){throw 'fresh run and wrapper log directories required'}
New-Item -ItemType Directory $logs|Out-Null
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$env:CUDA_VISIBLE_DEVICES='-1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:PYTHONPATH=''
$env:MPLBACKEND='Agg'
$argsBase=@('--config',"$Source\docs\research\S01\S01-E011\run_config.json",'--lock',"$Source\docs\research\S01\S01-E011\data_lock.json",'--cache','C:\Users\xw436\pavetrack_runs\S01-E008-R001','--metadata','C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\development\manifest_train_validation.json','--run',$r,'--e010-run','C:\Users\xw436\pavetrack_runs\S01-E010-R001')
@{run_id=$RunId;reviewed_commit=$ReviewedCommit;manifest_sha256=$ManifestSha256;wrapper_pid=$PID;started_at=(Get-Date -Format o);device='CPU';fresh_access=$false}|ConvertTo-Json|Set-Content "$logs\launch.json" -Encoding UTF8
function Step([string]$s){
 $saved=$ErrorActionPreference
 try{$ErrorActionPreference='Continue';if($s -eq 'analysis'){& $py "$Source\scripts\pavetrack_scalar_utility_cv\analyze.py" @argsBase 1>>"$logs\${s}_stdout.log" 2>>"$logs\${s}_stderr.log"}else{& $py "$Source\scripts\pavetrack_scalar_utility_cv\run.py" $s @argsBase 1>>"$logs\${s}_stdout.log" 2>>"$logs\${s}_stderr.log"};$stepExit=$LASTEXITCODE}
 finally{$ErrorActionPreference=$saved}
 if($stepExit -ne 0){throw "$s failed:$stepExit"}
}
try{
 Step 'execute';Step 'verify';Step 'analysis'
 Copy-Item "$logs\*" $r
 @{state='completed';updated_at=(Get-Date -Format o);fresh_access=$false;reviewed_commit=$ReviewedCommit}|ConvertTo-Json|Set-Content "$r\wrapper_receipt.json" -Encoding UTF8
}catch{@{state='failed';reason=$_.Exception.Message;updated_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8;throw}
