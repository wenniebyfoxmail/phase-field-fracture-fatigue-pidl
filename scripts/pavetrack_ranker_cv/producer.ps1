param([Parameter(Mandatory=$true)][string]$Stage,[Parameter(Mandatory=$true)][string]$Source,[string]$RunId='S01-E003-R001')
$ErrorActionPreference='Stop'
$run="C:\Users\xw436\pavetrack_runs\$RunId"
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$prior='C:\Users\xw436\pavetrack_runs\S01-E002-R002'
$workbook='C:\Users\xw436\pavetrack_stage\S01-E001-v11-review-20261009\data\Dataset_PDdescription.xlsx'
$downloader='C:\Users\xw436\pavetrack_stage\S01-E001-v7-preflight-20261009\data\remote_zip_extract_batched.py'
$base=@('--config',"$Source\docs\research\S01\S01-E003\run_config.json",'--lock',"$Source\docs\research\S01\S01-E003\data_lock.json",'--tiled',"$prior\training\tiled_proposer\weights\best.pt",'--old-ranker','C:\Users\xw436\pavetrack_runs\S01-E001-R008\reranker\best_reranker.pt','--development',"$prior\prepared\development\manifest_train_validation.json",'--source-validation',"$prior\evaluation\evaluation_validation.json",'--run',$run)
function Invoke-Step([string]$step,[string[]]$extra=@()) {
 & $py "$Source\scripts\pavetrack_ranker_cv\run.py" $step @base @extra 1>> "$run\${step}_stdout.log" 2>> "$run\${step}_stderr.log"
 if ($LASTEXITCODE -ne 0) {throw "$step failed: $LASTEXITCODE"}
}
if ($Stage -eq 'development') {
 if (Test-Path $run) {throw 'fresh run directory required'}
 New-Item -ItemType Directory $run | Out-Null
 @{run_id=$RunId;wrapper_pid=$PID;source=$Source;started_at=(Get-Date -Format o);execution_status='running';confirmatory_access=$false} | ConvertTo-Json | Set-Content "$run\launch_receipt.json" -Encoding UTF8
 try {Invoke-Step 'mine';Invoke-Step 'train';Invoke-Step 'freeze';@{state='development_completed';updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8}
 catch {@{state='failed';detail=$_.Exception.Message;updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8;throw}
} elseif ($Stage -eq 'confirmatory') {
 Invoke-Step 'check-authorization'
 if ((Test-Path "$run\confirmatory_download") -or (Test-Path "$run\confirmatory_launch.json")) {throw 'refuse duplicate confirmatory access'}
 $auth=Get-Content "$run\test_authorization.json" -Raw | ConvertFrom-Json
 @{run_id=$RunId;authorization_sha256=(Get-FileHash "$run\test_authorization.json" -Algorithm SHA256).Hash.ToLower();started_at=(Get-Date -Format o);confirmatory_access=$true;locations=$auth.confirmatory_test_locations} | ConvertTo-Json | Set-Content "$run\confirmatory_launch.json" -Encoding UTF8
 New-Item -ItemType Directory "$run\confirmatory_download" | Out-Null
 $locations=@($auth.confirmatory_test_locations)
 & $py $downloader '--url' 'https://china.scidb.cn/download?fileId=6a6125c7db77487782cafee9506e58f3' '--size' '5694108370' '--locations' @locations '--output' "$run\confirmatory_download\images" '--manifest' "$run\confirmatory_download\download_manifest.json" '--max-range-mib' '32' '--max-gap-mib' '2' '--delay-s' '1' 1>> "$run\download_stdout.log" 2>> "$run\download_stderr.log"
 if ($LASTEXITCODE -ne 0) {throw 'download failed'}
 Invoke-Step 'prepare' @('--workbook',$workbook,'--image-root',"$run\confirmatory_download\images")
 Invoke-Step 'evaluate'
 @{state='confirmatory_completed';updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8
} else {throw 'stage must be development or confirmatory'}
