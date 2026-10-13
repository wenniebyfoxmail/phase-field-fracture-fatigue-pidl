param([Parameter(Mandatory=$true)][string]$Stage,[Parameter(Mandatory=$true)][string]$Source,[string]$RunId='S01-E006-R001',[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256,[string]$IndependentReview,[string]$ReviewSha256,[string]$SourceRun)
$ErrorActionPreference='Stop'
$manifestPath=Join-Path $Source 'docs\research\S01\S01-E006\source_manifest.json'
if ((Get-FileHash $manifestPath -Algorithm SHA256).Hash.ToLower() -ne $ManifestSha256) {throw 'reviewed source manifest mismatch'}
$manifest=Get-Content $manifestPath -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files.PSObject.Properties) {
 if ((Get-FileHash (Join-Path $Source $entry.Name) -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) {throw "reviewed file mismatch: $($entry.Name)"}
}

$run="C:\Users\xw436\pavetrack_runs\$RunId"
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$prior='C:\Users\xw436\pavetrack_runs\S01-E003-R001'
$e5='C:\Users\xw436\pavetrack_runs\S01-E005-R001'
$e2='C:\Users\xw436\pavetrack_runs\S01-E002-R002'
$workbook='C:\Users\xw436\pavetrack_stage\S01-E001-v11-review-20261009\data\Dataset_PDdescription.xlsx'
$downloader=Join-Path $Source 'scripts\pavetrack_protected_cv\download_frozen.py'
$base=@('--config',"$Source\docs\research\S01\S01-E006\run_config.json",'--lock',"$Source\docs\research\S01\S01-E006\data_lock.json",'--tiled',"$e2\training\tiled_proposer\weights\best.pt",'--old-ranker',"$prior\best_ranker.pt",'--development',"$e2\prepared\development\manifest_train_validation.json",'--source-validation',"$prior\evaluation_validation.json",'--source-train',"$prior\train_proposals.json",'--corrector',"$e5\box_model.json",'--old-audit',"$e5\context_audit.json",'--old-train-features',"$e5\train_features.npz",'--old-validation',"$e5\evaluation_validation.json",'--run',$run)
if ($Stage -eq 'adopt') {if (-not $SourceRun) {throw 'source Run required'};$base+=@('--source-run',$SourceRun)}
if ($Stage -notin @('development','adopt')) {if (-not $IndependentReview -or -not $ReviewSha256) {throw 'bound independent development review required'};$base+=@('--independent-review',$IndependentReview,'--review-sha256',$ReviewSha256)}
function Invoke-Step([string]$step,[string[]]$extra=@()) {
 $savedPreference=$ErrorActionPreference
 try {$ErrorActionPreference='Continue'; & $py "$Source\scripts\pavetrack_protected_cv\run.py" $step @base @extra 1>> "$run\${step}_stdout.log" 2>> "$run\${step}_stderr.log";$stepExit=$LASTEXITCODE}
 finally {$ErrorActionPreference=$savedPreference}
 if ($stepExit -ne 0) {throw "$step failed: $stepExit"}
}
if ($Stage -in @('development','adopt')) {
 if (Test-Path $run) {throw 'fresh run directory required'}
 New-Item -ItemType Directory $run | Out-Null
 @{run_id=$RunId;wrapper_pid=$PID;source=$Source;reviewed_commit=$ReviewedCommit;source_manifest_sha256=$ManifestSha256;dirty_status='immutable Git archive with reviewed manifest verified';started_at=(Get-Date -Format o);execution_status='running';confirmatory_access=$false} | ConvertTo-Json | Set-Content "$run\launch_receipt.json" -Encoding UTF8
 try {if ($Stage -eq 'adopt') {Invoke-Step 'adopt'} else {Invoke-Step 'extract'};Invoke-Step 'fit';Invoke-Step 'freeze';@{state='development_completed';updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8}
 catch {@{state='failed';detail=$_.Exception.Message;updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8;throw}
} elseif ($Stage -eq 'authorize') {
 Invoke-Step 'authorize'
} elseif ($Stage -eq 'confirmatory') {
 Invoke-Step 'check-authorization'
 if ((Test-Path "$run\confirmatory_download") -or (Test-Path "$run\confirmatory_launch.json")) {throw 'refuse duplicate confirmatory access'}
 $auth=Get-Content "$run\test_authorization.json" -Raw | ConvertFrom-Json
 @{run_id=$RunId;authorization_sha256=(Get-FileHash "$run\test_authorization.json" -Algorithm SHA256).Hash.ToLower();started_at=(Get-Date -Format o);confirmatory_access=$true;locations=$auth.confirmatory_test_locations} | ConvertTo-Json | Set-Content "$run\confirmatory_launch.json" -Encoding UTF8
 New-Item -ItemType Directory "$run\confirmatory_download" | Out-Null
 $locations=@($auth.confirmatory_test_locations)
 & $py $downloader '--url' 'https://china.scidb.cn/download?fileId=6a6125c7db77487782cafee9506e58f3' '--size' '5694108370' '--locations' @locations '--output' "$run\confirmatory_download\images" '--manifest' "$run\confirmatory_download\download_manifest.json" '--max-range-mib' '32' '--max-gap-mib' '2' '--delay-s' '1' 1>> "$run\download_stdout.log" 2>> "$run\download_stderr.log"
 if ($LASTEXITCODE -ne 0) {throw 'download failed'}
 Invoke-Step 'prepare' @('--workbook',$workbook,'--image-root',"$run\confirmatory_download\images",'--download-manifest',"$run\confirmatory_download\download_manifest.json")
 Invoke-Step 'evaluate' @('--download-manifest',"$run\confirmatory_download\download_manifest.json")
 @{state='confirmatory_completed';updated_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content "$run\status.json" -Encoding UTF8
} else {throw 'stage must be development, authorize or confirmatory'}
