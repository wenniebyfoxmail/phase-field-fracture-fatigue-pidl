param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256,[string]$RunId='S01-E007-R001')
$ErrorActionPreference='Stop'
$mp=Join-Path $Source 'docs\research\S01\S01-E007\source_manifest.json'
if((Get-FileHash $mp -Algorithm SHA256).Hash.ToLower() -ne $ManifestSha256){throw 'reviewed manifest mismatch'}
$m=Get-Content $mp -Raw|ConvertFrom-Json
foreach($p in $m.files.PSObject.Properties){if((Get-FileHash (Join-Path $Source $p.Name) -Algorithm SHA256).Hash.ToLower() -ne $p.Value){throw "reviewed source mismatch:$($p.Name)"}}
$r="C:\Users\xw436\pavetrack_runs\$RunId"
if(Test-Path $r){throw 'fresh Run required'}
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$e2='C:\Users\xw436\pavetrack_runs\S01-E002-R002';$e3='C:\Users\xw436\pavetrack_runs\S01-E003-R001';$e5='C:\Users\xw436\pavetrack_runs\S01-E005-R001';$e6='C:\Users\xw436\pavetrack_runs\S01-E006-R002'
$argsBase=@('--config',"$Source\docs\research\S01\S01-E007\run_config.json",'--lock',"$Source\docs\research\S01\S01-E007\data_lock.json",'--tiled',"$e2\training\tiled_proposer\weights\best.pt",'--old-ranker',"$e3\best_ranker.pt",'--development',"$e2\prepared\development\manifest_train_validation.json",'--source-validation',"$e3\evaluation_validation.json",'--source-train',"$e3\train_proposals.json",'--corrector',"$e5\box_model.json",'--old-audit',"$e5\context_audit.json",'--old-train-features',"$e5\train_features.npz",'--old-validation',"$e5\evaluation_validation.json",'--parent-run',$e6,'--run',$r)
New-Item -ItemType Directory $r|Out-Null
@{run_id=$RunId;source=$Source;reviewed_commit=$ReviewedCommit;manifest_sha256=$ManifestSha256;wrapper_pid=$PID;started_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$r\launch_receipt.json" -Encoding UTF8
function Step([string]$s){
 $savedPreference=$ErrorActionPreference
 try{$ErrorActionPreference='Continue'; & $py "$Source\scripts\pavetrack_paired_cv\run.py" $s @argsBase 1>>"$r\${s}_stdout.log" 2>>"$r\${s}_stderr.log";$stepExit=$LASTEXITCODE}
 finally{$ErrorActionPreference=$savedPreference}
 if($stepExit -ne 0){throw "$s failed:$stepExit"}
}
try{
 Step 'extract';Step 'qualify';Step 'verify'
 $d=Get-Content "$r\qualification_decision.json" -Raw|ConvertFrom-Json
 if($d.status -eq 'qualified'){Step 'development';Step 'verify';$state='development_completed'}else{$state='qualification_stopped'}
 @{state=$state;updated_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$r\status.json" -Encoding UTF8
}catch{@{state='failed';detail=$_.Exception.Message;updated_at=(Get-Date -Format o);fresh_access=$false}|ConvertTo-Json|Set-Content "$r\status.json" -Encoding UTF8;throw}
