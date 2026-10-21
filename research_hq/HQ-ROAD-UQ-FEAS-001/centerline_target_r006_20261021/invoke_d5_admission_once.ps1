$ErrorActionPreference = 'Stop'
$started = Get-Date
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r006_stage_20261021\HQ-ROAD-UQ-FEAS-001'
$d5 = Join-Path $stage 'centerline_target_r006_20261021'
$run = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R006'
$python = 'C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$controller = Join-Path $d5 'owned_subprocess.py'
$invocationPath = Join-Path $d5 'admission_child.invocation.json'
$childReceipt = Join-Path $run 'admission_receipt_remote.json'
$wrapperReceipt = Join-Path $run 'admission_wrapper_receipt_remote.json'
$controllerStdout = Join-Path $run 'admission.controller.stdout.log'
$controllerStderr = Join-Path $run 'admission.controller.stderr.log'
$packageStart = [DateTimeOffset]::Parse('2026-10-20T21:59:35Z')
$packageDeadline = [DateTimeOffset]::Parse('2026-10-21T01:59:35Z')
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Get-RequiredInteger($Object, [string]$Name, [string]$Context) {
  $property = $Object.PSObject.Properties[$Name]
  if (-not $property -or $null -eq $property.Value) { throw "$Context missing integer property: $Name" }
  $text = [string]$property.Value
  if ($text -notmatch '^-?\d+$') { throw "$Context malformed integer property: $Name" }
  return [int]$text
}
if ((Test-Path $childReceipt) -or (Test-Path $wrapperReceipt)) { throw 'R006 admission receipt already exists; second R006 check prohibited' }
if (-not (Test-Path $controller) -or -not (Test-Path $invocationPath)) { throw 'reviewed owned-child controller or invocation missing' }

$process = Start-Process -FilePath $python -ArgumentList @($controller,$invocationPath) -NoNewWindow -PassThru -RedirectStandardOutput $controllerStdout -RedirectStandardError $controllerStderr
$timedOut = -not $process.WaitForExit(86000)
$killExitCode = $null
$killOutput = $null
$remainingAdmissionProcesses = @()
if ($timedOut) {
  $killOutput = (& taskkill.exe /PID $process.Id /T /F 2>&1) -join "`n"
  $killExitCode = $LASTEXITCODE
  Start-Sleep -Seconds 1
  $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r006_stage_20261021') -and
    ($_.CommandLine.Contains('owned_subprocess.py') -or $_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
  } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
  foreach ($remaining in $remainingAdmissionProcesses) { & taskkill.exe /PID $remaining.ProcessId /T /F 2>$null | Out-Null }
  Start-Sleep -Milliseconds 250
  $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r006_stage_20261021') -and
    ($_.CommandLine.Contains('owned_subprocess.py') -or $_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
  } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
} else {
  $process.WaitForExit()
}

$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
$controlRecord = $null
$controlError = $null
$controlChildExit = $null
$controlControllerExit = $null
$invocation = Get-Content -Raw -LiteralPath $invocationPath | ConvertFrom-Json
try {
  foreach ($path in @($invocation.receipt_path,$invocation.exitcode_path,$invocation.stdout_path,$invocation.stderr_path)) { if (-not (Test-Path -LiteralPath $path)) { throw "owned admission evidence missing: $path" } }
  $controlRecord = Get-Content -Raw -LiteralPath $invocation.receipt_path | ConvertFrom-Json
  $approval = Get-Content -Raw -LiteralPath $invocation.approval_path | ConvertFrom-Json
  $exitText = (Get-Content -Raw -LiteralPath $invocation.exitcode_path).Trim()
  if ($exitText -notmatch '^-?\d+$') { throw 'owned admission numeric exit malformed' }
  $controlChildExit = Get-RequiredInteger $controlRecord 'child_exit_code' 'owned admission'
  $controlControllerExit = Get-RequiredInteger $controlRecord 'controller_exit_code' 'owned admission'
  if ($controlRecord.schema -ne 1 -or $controlRecord.run_id -ne 'HQ-ROAD-CENTERLINE-001-R006' -or $controlRecord.role -ne 'admission_child') { throw 'owned admission identity mismatch' }
  if ($controlRecord.invocation_sha256 -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $invocationPath).Hash.ToLowerInvariant() -or $controlRecord.code_snapshot -ne $approval.code_snapshot -or $controlRecord.data_lock_sha256 -ne $approval.data_lock_sha256) { throw 'owned admission source/data binding mismatch' }
  $claimPath = [string]$invocation.receipt_path + '.claim'
  if (-not (Test-Path -LiteralPath $claimPath) -or $controlRecord.claim_sha256 -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $claimPath).Hash.ToLowerInvariant()) { throw 'owned admission exclusive claim mismatch' }
  if ($controlControllerExit -ne [int]$exitText) { throw 'owned admission JSON/numeric exit mismatch' }
  foreach ($name in @('stdout','stderr')) {
    $path = [string]$invocation.PSObject.Properties[($name + '_path')].Value
    $evidence = $controlRecord.$name
    if ([long](Get-Item -LiteralPath $path).Length -ne [long]$evidence.bytes -or (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $evidence.sha256) { throw "owned admission $name evidence mismatch" }
  }
} catch { $controlError = $_.Exception.Message; $controlRecord = $null }

$childRecord = $null
$childHash = $null
if (Test-Path $childReceipt) {
  $childHash = (Get-FileHash -Algorithm SHA256 $childReceipt).Hash.ToLowerInvariant()
  try { $childRecord = Get-Content -Raw $childReceipt | ConvertFrom-Json } catch { $childRecord = $null }
}
$controlPass = $controlRecord -and $null -ne $controlChildExit -and $null -ne $controlControllerExit -and $controlRecord.status -eq 'COMPLETE_ZERO' -and $controlRecord.timed_out -eq $false -and $controlChildExit -eq 0 -and $controlControllerExit -eq 0
$wrapperPass = (-not $timedOut) -and $controlPass -and $elapsed -le 90 -and $childRecord -and $childRecord.status -eq 'PASS_ADMISSION_READY_TO_LAUNCH' -and [double]$childRecord.elapsed_seconds -le 90 -and $childRecord.r006_check_number -eq 1 -and $childRecord.r006_check_cap -eq 1
$wrapper = [ordered]@{
  status = if ($wrapperPass) { 'PASS_ADMISSION_WATCHDOG' } else { 'FAIL_ADMISSION_WATCHDOG' }
  run_id = 'HQ-ROAD-CENTERLINE-001-R006'
  task_name = 'HQ-ROAD-CENTERLINE-001-R006-20261021'
  r006_check_number = 1
  r006_check_cap = 1
  r001_checks_preserved = 3
  r002_checks_preserved = 1
  r003_checks_preserved = 1
  r003_scientific_attempts_preserved = 1
  r004_admission_checks_preserved = 1
  r004_admission_seconds_preserved = 8.250
  r004_scientific_attempts_preserved = 0
  r005_admission_checks_preserved = 1
  r005_admission_seconds_preserved = 25.742
  r005_scientific_attempts_preserved = 1
  r005_worker_seconds_preserved = 0.219
  check_limit_seconds = 90
  package_clock_start_utc = $packageStart.ToString('o')
  package_deadline_utc = $packageDeadline.ToString('o')
  package_remaining_seconds_at_wrapper_end = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
  parent_watchdog_timed_out = $timedOut
  owned_control_receipt = $controlRecord
  owned_control_error = $controlError
  child_receipt_exists = Test-Path $childReceipt
  child_receipt_sha256 = $childHash
  child_status = if ($childRecord) { $childRecord.status } else { $null }
  process_tree_kill_exit_code = $killExitCode
  process_tree_kill_output = $killOutput
  remaining_admission_processes = $remainingAdmissionProcesses
  scientific_execution_started = $false
  training_steps = 0
  optimizer_steps = 0
  road420_access = $false
  started_iso = $started.ToString('o')
  ended_iso = (Get-Date).ToString('o')
  elapsed_seconds = $elapsed
}
$temporary = "$wrapperReceipt.tmp.$PID"
[System.IO.File]::WriteAllText($temporary, ($wrapper | ConvertTo-Json -Depth 12), $utf8)
Move-Item -LiteralPath $temporary -Destination $wrapperReceipt
$wrapper | ConvertTo-Json -Depth 12
if (-not $wrapperPass) { exit 2 }
exit 0
