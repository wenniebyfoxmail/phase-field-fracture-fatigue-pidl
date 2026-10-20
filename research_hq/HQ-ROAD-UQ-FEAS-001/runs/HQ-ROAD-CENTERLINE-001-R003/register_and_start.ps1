$ErrorActionPreference = 'Stop'
$taskName = 'HQ-ROAD-CENTERLINE-001-R003-20261021'
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r003_stage_20261021\HQ-ROAD-UQ-FEAS-001'
$launch = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R003\launch_gpu_server.cmd'
$receipt = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R003\launch_receipt_remote.json'
$admission = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R003\admission_receipt_remote.json'
$wrapperAdmission = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R003\admission_wrapper_receipt_remote.json'
$output = 'C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R003'
$packageStart = [DateTimeOffset]::Parse('2026-10-20T21:59:35Z')
$packageDeadline = [DateTimeOffset]::Parse('2026-10-21T01:59:35Z')
$minimumLaunchRemainingSeconds = 1900
$expectedGpuUuid = 'GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7'
$scientificInvocation = Join-Path $stage 'centerline_target_r003_20261021\scientific_worker.invocation.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Get-RequiredInteger($Object, [string]$Name, [string]$Context) {
  $property = $Object.PSObject.Properties[$Name]
  if (-not $property -or $null -eq $property.Value) { throw "$Context missing integer property: $Name" }
  $text = [string]$property.Value
  if ($text -notmatch '^-?\d+$') { throw "$Context malformed integer property: $Name" }
  return [int]$text
}
if (-not (Test-Path $launch)) { throw 'launch command missing' }
if (-not (Test-Path $admission)) { throw 'admission receipt missing' }
if (-not (Test-Path $wrapperAdmission)) { throw 'admission watchdog receipt missing' }
if (Test-Path $receipt) { throw 'launch receipt already exists; repeat dispatch prohibited' }
$wrapperRecord = Get-Content -Raw $wrapperAdmission | ConvertFrom-Json
if ($wrapperRecord.status -ne 'PASS_ADMISSION_WATCHDOG' -or $wrapperRecord.parent_watchdog_timed_out -ne $false -or [double]$wrapperRecord.elapsed_seconds -gt 90) { throw 'admission watchdog receipt is not PASS' }
$ownedChildExit = Get-RequiredInteger $wrapperRecord.owned_control_receipt 'child_exit_code' 'owned admission receipt'
$ownedControllerExit = Get-RequiredInteger $wrapperRecord.owned_control_receipt 'controller_exit_code' 'owned admission receipt'
if ($wrapperRecord.owned_control_receipt.status -ne 'COMPLETE_ZERO' -or $wrapperRecord.owned_control_receipt.timed_out -ne $false -or $ownedChildExit -ne 0 -or $ownedControllerExit -ne 0) { throw 'owned admission child receipt is not PASS' }
$admissionRecord = Get-Content -Raw $admission | ConvertFrom-Json
if ($admissionRecord.status -ne 'PASS_ADMISSION_READY_TO_LAUNCH') { throw 'admission receipt is not PASS' }
if ($wrapperRecord.run_id -ne $admissionRecord.run_id -or $wrapperRecord.task_name -ne $taskName -or $wrapperRecord.child_receipt_sha256 -ne (Get-FileHash -Algorithm SHA256 $admission).Hash.ToLowerInvariant()) { throw 'watchdog/child receipt identity mismatch' }
if ($admissionRecord.run_id -ne 'HQ-ROAD-CENTERLINE-001-R003' -or $admissionRecord.task_name -ne $taskName) { throw 'admission run/task identity mismatch' }
if ($admissionRecord.r003_check_number -ne 1 -or $admissionRecord.r003_check_cap -ne 1 -or $admissionRecord.r001_checks_preserved -ne 3 -or $admissionRecord.r002_checks_preserved -ne 1) { throw 'admission check-count identity mismatch' }
if ($wrapperRecord.r003_check_number -ne 1 -or $wrapperRecord.r003_check_cap -ne 1 -or $wrapperRecord.r001_checks_preserved -ne 3 -or $wrapperRecord.r002_checks_preserved -ne 1) { throw 'watchdog check-count identity mismatch' }
if ([double]$admissionRecord.elapsed_seconds -gt 90) { throw 'admission exceeded 90 seconds' }
if ($admissionRecord.scientific_execution_started -ne $false -or $admissionRecord.training_steps -ne 0 -or $admissionRecord.optimizer_steps -ne 0 -or $admissionRecord.road420_access -ne $false) { throw 'admission zero-step/Road420 contract mismatch' }
if ($admissionRecord.actual_gpu_uuid -ne $expectedGpuUuid -or [double]$admissionRecord.aggregate_free_mib -lt 16384) { throw 'admission GPU identity/free-memory mismatch' }
if (-not $admissionRecord.gpu_query_raw) { throw 'admission raw GPU query missing' }
$badClassifications = @($admissionRecord.gpu_process_classification | Where-Object { $_.classification -ne 'KNOWN_DESKTOP_BACKGROUND_NA_MEMORY' })
if ($badClassifications.Count -gt 0) { throw 'admission contains unknown or competing GPU processes' }
if ($admissionRecord.preflight.status -ne 'PASS_ZERO_STEP_PREFLIGHT' -or $admissionRecord.preflight.run_id -ne 'HQ-ROAD-CENTERLINE-001-R003') { throw 'zero-step preflight receipt mismatch' }
$approvalPath = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R003\approval_hq.json'
$lockPath = Join-Path $stage 'centerline_target_r003_20261021\d5_data_lock.json'
$approval = Get-Content -Raw $approvalPath | ConvertFrom-Json
$remainingSeconds = ($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds
if ($remainingSeconds -lt $minimumLaunchRemainingSeconds) { throw "original package clock cannot fit complete run: $remainingSeconds seconds remain" }
if ($approval.package_clock_start_utc -ne '2026-10-20T21:59:35Z' -or $approval.package_deadline_utc -ne '2026-10-21T01:59:35Z' -or $approval.minimum_launch_remaining_seconds -ne $minimumLaunchRemainingSeconds -or $approval.expected_gpu_uuid -ne $expectedGpuUuid) { throw 'approval package-clock/GPU binding mismatch' }
$lockSha = (Get-FileHash -Algorithm SHA256 $lockPath).Hash.ToLowerInvariant()
if ($admissionRecord.preflight.code_snapshot -ne $approval.code_snapshot -or $admissionRecord.preflight.data_lock_sha256 -ne $approval.data_lock_sha256 -or $lockSha -ne $approval.data_lock_sha256) { throw 'admission code/data identity mismatch' }
if ($admissionRecord.canonical_output_exists -ne $false -or $admissionRecord.scheduled_task_exists -ne $false -or $admissionRecord.launch_receipt_exists -ne $false -or $admissionRecord.canonical_cache_markers_verified -ne $true) { throw 'admission path/task/cache/launch-receipt contract mismatch' }
$cache = 'C:\Users\xw436\jobs\hq_road_centerline_001_r003_cache_20261021'
$lock = Get-Content -Raw $lockPath | ConvertFrom-Json
if ((Get-Content -Raw (Join-Path $cache 'train\.complete')).Trim() -ne $lock.trainzip.sha256) { throw 'train cache marker mismatch before launch' }
if ((Get-Content -Raw (Join-Path $cache 'val\.complete')).Trim() -ne $lock.valzip.sha256) { throw 'val cache marker mismatch before launch' }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'scheduled task already exists' }
if (Test-Path $output) { throw 'canonical output already exists' }
if (Test-Path $receipt) { throw 'launch receipt appeared before registration; repeat dispatch prohibited' }
$scientificControl = Get-Content -Raw -LiteralPath $scientificInvocation | ConvertFrom-Json
foreach ($path in @($scientificControl.receipt_path,$scientificControl.exitcode_path,$scientificControl.stdout_path,$scientificControl.stderr_path)) { if (Test-Path -LiteralPath $path) { throw "scientific-worker evidence already exists; repeat dispatch prohibited: $path" } }
$scientificClaim = [string]$scientificControl.receipt_path + '.claim'
if (Test-Path -LiteralPath $scientificClaim) { throw "scientific-worker exclusive claim already exists; repeat dispatch prohibited: $scientificClaim" }
$remainingAtTaskCreationSeconds = ($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds
if ($remainingAtTaskCreationSeconds -lt $minimumLaunchRemainingSeconds) { throw "original package clock cannot fit complete run at task creation: $remainingAtTaskCreationSeconds seconds remain" }
$taskLimitSafetySeconds = 120
$taskExecutionLimitSeconds = [math]::Floor($remainingAtTaskCreationSeconds - $taskLimitSafetySeconds)
if ($taskExecutionLimitSeconds -le 0) { throw 'no package clock remains for scheduled task' }
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/d /c $launch"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds $taskExecutionLimitSeconds) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
$info = Get-ScheduledTaskInfo -TaskName $taskName
$task = Get-ScheduledTask -TaskName $taskName
$canonicalOutputArgument = '--output C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R003'
$processes = @(Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and $_.CommandLine.Contains('d5_runner.py') -and $_.CommandLine.Contains($approvalPath) -and $_.CommandLine.Contains($canonicalOutputArgument)
} | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
$runnerReceipt = Join-Path $output 'receipt.json'
$launchStatus = if ($task.State -eq 'Running' -or $processes.Count -gt 0 -or (Test-Path $runnerReceipt)) { 'LAUNCH_DISPATCHED_VERIFIED' } else { 'LAUNCH_STATE_UNKNOWN_NO_REPEAT' }
$record = [ordered]@{
  status = $launchStatus
  run_id = 'HQ-ROAD-CENTERLINE-001-R003'
  task_name = $taskName
  last_task_result = $info.LastTaskResult
  task_state = [string]$task.State
  automatic_trigger_count = @($task.Triggers).Count
  action_execute = $task.Actions[0].Execute
  action_arguments = $task.Actions[0].Arguments
  launch_sha256 = (Get-FileHash -Algorithm SHA256 $launch).Hash.ToLowerInvariant()
  admission_receipt_sha256 = (Get-FileHash -Algorithm SHA256 $admission).Hash.ToLowerInvariant()
  admission_watchdog_receipt_sha256 = (Get-FileHash -Algorithm SHA256 $wrapperAdmission).Hash.ToLowerInvariant()
  scientific_worker_invocation_sha256 = (Get-FileHash -Algorithm SHA256 $scientificInvocation).Hash.ToLowerInvariant()
  processes = $processes
  output_exists = Test-Path $output
  runner_receipt_exists = Test-Path $runnerReceipt
  launched_iso = (Get-Date).ToString('o')
  package_clock_start_utc = $packageStart.ToString('o')
  package_deadline_utc = $packageDeadline.ToString('o')
  package_elapsed_seconds_at_launch = [math]::Round(([DateTimeOffset]::UtcNow - $packageStart).TotalSeconds, 3)
  package_remaining_seconds_at_launch = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
  task_limit_safety_seconds = $taskLimitSafetySeconds
  task_execution_limit_seconds = $taskExecutionLimitSeconds
  task_limit_configured_utc = ([DateTimeOffset]::UtcNow).ToString('o')
  scientific_attempt = 1
  road420_access = $false
}
$temporary = "$receipt.tmp.$PID"
[System.IO.File]::WriteAllText($temporary, ($record | ConvertTo-Json -Depth 8), $utf8)
Move-Item -LiteralPath $temporary -Destination $receipt
$record | ConvertTo-Json -Depth 8
