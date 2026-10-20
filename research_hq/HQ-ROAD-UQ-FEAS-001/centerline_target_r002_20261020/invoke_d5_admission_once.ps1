$ErrorActionPreference = 'Stop'
$started = Get-Date
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r002_stage_20261020\HQ-ROAD-UQ-FEAS-001'
$child = Join-Path $stage 'centerline_target_r002_20261020\d5_admission.ps1'
$run = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R002'
$childReceipt = Join-Path $run 'admission_receipt_remote.json'
$wrapperReceipt = Join-Path $run 'admission_wrapper_receipt_remote.json'
$stdout = Join-Path $run 'admission.wrapper.stdout.log'
$stderr = Join-Path $run 'admission.wrapper.stderr.log'
$packageStart = [DateTimeOffset]::Parse('2026-10-20T21:59:35Z')
$packageDeadline = [DateTimeOffset]::Parse('2026-10-21T01:59:35Z')
$utf8 = New-Object System.Text.UTF8Encoding($false)
if ((Test-Path $childReceipt) -or (Test-Path $wrapperReceipt)) { throw 'R002 admission receipt already exists; second R002 check prohibited' }
if (-not (Test-Path $child)) { throw "reviewed admission child missing: $child" }
$process = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$child) -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$timedOut = -not $process.WaitForExit(83000)
$killExitCode = $null
$killOutput = $null
$childExitCode = $null
$remainingAdmissionProcesses = @()
if ($timedOut) {
  $killOutput = (& taskkill.exe /PID $process.Id /T /F 2>&1) -join "`n"
  $killExitCode = $LASTEXITCODE
  Start-Sleep -Seconds 1
  $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r002_stage_20261020') -and
    ($_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
  } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
  if ($remainingAdmissionProcesses.Count -gt 0) {
    foreach ($remaining in $remainingAdmissionProcesses) { & taskkill.exe /PID $remaining.ProcessId /T /F 2>$null | Out-Null }
    Start-Sleep -Milliseconds 250
    $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
      $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r002_stage_20261020') -and
      ($_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
    } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
  }
} else {
  $process.WaitForExit()
  $process.Refresh()
  $childExitCode = $process.ExitCode
}

$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
$childRecord = $null
$childHash = $null
if (Test-Path $childReceipt) {
  $childHash = (Get-FileHash -Algorithm SHA256 $childReceipt).Hash.ToLowerInvariant()
  try { $childRecord = Get-Content -Raw $childReceipt | ConvertFrom-Json } catch { $childRecord = $null }
}
$wrapperPass = (-not $timedOut) -and $childExitCode -eq 0 -and $elapsed -le 90 -and $childRecord -and $childRecord.status -eq 'PASS_ADMISSION_READY_TO_LAUNCH' -and [double]$childRecord.elapsed_seconds -le 90 -and $childRecord.r002_check_number -eq 1 -and $childRecord.r002_check_cap -eq 1
$wrapper = [ordered]@{
  status = if ($wrapperPass) { 'PASS_ADMISSION_WATCHDOG' } else { 'FAIL_ADMISSION_WATCHDOG' }
  run_id = 'HQ-ROAD-CENTERLINE-001-R002'
  task_name = 'HQ-ROAD-CENTERLINE-001-R002-20261020'
  r002_check_number = 1
  r002_check_cap = 1
  r001_checks_preserved = 3
  r001_approx_seconds_preserved = 45.544
  check_limit_seconds = 90
  package_clock_start_utc = $packageStart.ToString('o')
  package_deadline_utc = $packageDeadline.ToString('o')
  package_elapsed_seconds_at_wrapper_end = [math]::Round(([DateTimeOffset]::UtcNow - $packageStart).TotalSeconds, 3)
  package_remaining_seconds_at_wrapper_end = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
  timed_out = $timedOut
  child_exit_code = $childExitCode
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
[System.IO.File]::WriteAllText($wrapperReceipt, ($wrapper | ConvertTo-Json -Depth 10), $utf8)
$wrapper | ConvertTo-Json -Depth 10
if (-not $wrapperPass) { exit 2 }
exit 0
