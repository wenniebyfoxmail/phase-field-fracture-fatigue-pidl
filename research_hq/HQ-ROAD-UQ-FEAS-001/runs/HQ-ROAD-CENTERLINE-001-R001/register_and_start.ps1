$ErrorActionPreference = 'Stop'
$taskName = 'HQ-ROAD-CENTERLINE-001-R001-20261020'
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r001_stage_20261020\HQ-ROAD-UQ-FEAS-001'
$launch = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001\launch_gpu_server.cmd'
$receipt = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001\launch_receipt_remote.json'
$admission = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001\admission_receipt_remote.json'
$wrapperAdmission = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001\admission_wrapper_receipt_remote.json'
$output = 'C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R001'
$utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not (Test-Path $launch)) { throw 'launch command missing' }
if (-not (Test-Path $admission)) { throw 'admission receipt missing' }
if (-not (Test-Path $wrapperAdmission)) { throw 'admission watchdog receipt missing' }
$wrapperRecord = Get-Content -Raw $wrapperAdmission | ConvertFrom-Json
if ($wrapperRecord.status -ne 'PASS_ADMISSION_WATCHDOG' -or $wrapperRecord.timed_out -ne $false -or [double]$wrapperRecord.elapsed_seconds -gt 75) { throw 'admission watchdog receipt is not PASS' }
$admissionRecord = Get-Content -Raw $admission | ConvertFrom-Json
if ($admissionRecord.status -ne 'PASS_ADMISSION_READY_TO_LAUNCH') { throw 'admission receipt is not PASS' }
if ($wrapperRecord.run_id -ne $admissionRecord.run_id -or $wrapperRecord.task_name -ne $taskName -or $wrapperRecord.child_receipt_sha256 -ne (Get-FileHash -Algorithm SHA256 $admission).Hash.ToLowerInvariant()) { throw 'watchdog/child receipt identity mismatch' }
if ($admissionRecord.run_id -ne 'HQ-ROAD-CENTERLINE-001-R001' -or $admissionRecord.task_name -ne $taskName) { throw 'admission run/task identity mismatch' }
if ($admissionRecord.overall_check_number -ne 3 -or $admissionRecord.prior_checks_consumed -ne 2 -or $admissionRecord.additional_check_number -ne 1) { throw 'admission check-count identity mismatch' }
if ([double]$admissionRecord.elapsed_seconds -gt 75) { throw 'admission exceeded 75 seconds' }
if ($admissionRecord.scientific_execution_started -ne $false -or $admissionRecord.training_steps -ne 0 -or $admissionRecord.optimizer_steps -ne 0 -or $admissionRecord.road420_access -ne $false) { throw 'admission zero-step/Road420 contract mismatch' }
if ($admissionRecord.preflight.status -ne 'PASS_ZERO_STEP_PREFLIGHT' -or $admissionRecord.preflight.run_id -ne 'HQ-ROAD-CENTERLINE-001-R001') { throw 'zero-step preflight receipt mismatch' }
$approvalPath = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001\approval_hq.json'
$lockPath = Join-Path $stage 'centerline_target_20261020\d5_data_lock.json'
$approval = Get-Content -Raw $approvalPath | ConvertFrom-Json
$lockSha = (Get-FileHash -Algorithm SHA256 $lockPath).Hash.ToLowerInvariant()
if ($admissionRecord.preflight.code_snapshot -ne $approval.code_snapshot -or $admissionRecord.preflight.data_lock_sha256 -ne $approval.data_lock_sha256 -or $lockSha -ne $approval.data_lock_sha256) { throw 'admission code/data identity mismatch' }
if ($admissionRecord.canonical_output_exists -ne $false -or $admissionRecord.scheduled_task_exists -ne $false -or $admissionRecord.canonical_cache_markers_verified -ne $true) { throw 'admission path/task/cache contract mismatch' }
$cache = 'C:\Users\xw436\jobs\hq_road_centerline_001_r001_cache_20261020'
$lock = Get-Content -Raw $lockPath | ConvertFrom-Json
if ((Get-Content -Raw (Join-Path $cache 'train\.complete')).Trim() -ne $lock.trainzip.sha256) { throw 'train cache marker mismatch before launch' }
if ((Get-Content -Raw (Join-Path $cache 'val\.complete')).Trim() -ne $lock.valzip.sha256) { throw 'val cache marker mismatch before launch' }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'scheduled task already exists' }
if (Test-Path $output) { throw 'canonical output already exists' }
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/d /c $launch"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 4 -Minutes 5) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
$info = Get-ScheduledTaskInfo -TaskName $taskName
$task = Get-ScheduledTask -TaskName $taskName
$canonicalOutputArgument = '--output C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R001'
$processes = @(Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and $_.CommandLine.Contains('d5_runner.py') -and $_.CommandLine.Contains($approvalPath) -and $_.CommandLine.Contains($canonicalOutputArgument)
} | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
$runnerReceipt = Join-Path $output 'receipt.json'
$launchStatus = if ($task.State -eq 'Running' -or $processes.Count -gt 0 -or (Test-Path $runnerReceipt)) { 'LAUNCH_DISPATCHED_VERIFIED' } else { 'LAUNCH_STATE_UNKNOWN_NO_REPEAT' }
$record = [ordered]@{
  status = $launchStatus
  run_id = 'HQ-ROAD-CENTERLINE-001-R001'
  task_name = $taskName
  last_task_result = $info.LastTaskResult
  task_state = [string]$task.State
  automatic_trigger_count = @($task.Triggers).Count
  action_execute = $task.Actions[0].Execute
  action_arguments = $task.Actions[0].Arguments
  launch_sha256 = (Get-FileHash -Algorithm SHA256 $launch).Hash.ToLowerInvariant()
  admission_receipt_sha256 = (Get-FileHash -Algorithm SHA256 $admission).Hash.ToLowerInvariant()
  admission_watchdog_receipt_sha256 = (Get-FileHash -Algorithm SHA256 $wrapperAdmission).Hash.ToLowerInvariant()
  processes = $processes
  output_exists = Test-Path $output
  runner_receipt_exists = Test-Path $runnerReceipt
  launched_iso = (Get-Date).ToString('o')
  scientific_attempt = 1
  road420_access = $false
}
[System.IO.File]::WriteAllText($receipt, ($record | ConvertTo-Json -Depth 8), $utf8)
$record | ConvertTo-Json -Depth 8
