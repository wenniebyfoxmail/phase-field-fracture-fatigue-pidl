$ErrorActionPreference = 'Stop'
$started = Get-Date
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r001_stage_20261020\HQ-ROAD-UQ-FEAS-001'
$child = Join-Path $stage 'centerline_target_20261020\d5_admission.ps1'
$run = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R001'
$childReceipt = Join-Path $run 'admission_receipt_remote.json'
$wrapperReceipt = Join-Path $run 'admission_wrapper_receipt_remote.json'
$stdout = Join-Path $run 'admission.wrapper.stdout.log'
$stderr = Join-Path $run 'admission.wrapper.stderr.log'
$utf8 = New-Object System.Text.UTF8Encoding($false)
if ((Test-Path $childReceipt) -or (Test-Path $wrapperReceipt)) { throw 'admission receipt already exists; fourth check prohibited' }
if (-not (Test-Path $child)) { throw "reviewed admission child missing: $child" }
$process = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$child) -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$timedOut = -not $process.WaitForExit(68000)
$killExitCode = $null
$killOutput = $null
$remainingAdmissionProcesses = @()
if ($timedOut) {
  $killOutput = (& taskkill.exe /PID $process.Id /T /F 2>&1) -join "`n"
  $killExitCode = $LASTEXITCODE
  Start-Sleep -Seconds 1
  $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r001_stage_20261020') -and
    ($_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
  } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
  if ($remainingAdmissionProcesses.Count -gt 0) {
    foreach ($remaining in $remainingAdmissionProcesses) { & taskkill.exe /PID $remaining.ProcessId /T /F 2>$null | Out-Null }
    Start-Sleep -Milliseconds 250
    $remainingAdmissionProcesses = @(Get-CimInstance Win32_Process | Where-Object {
      $_.CommandLine -and $_.CommandLine.Contains('hq_road_centerline_001_r001_stage_20261020') -and
      ($_.CommandLine.Contains('d5_admission.ps1') -or $_.CommandLine.Contains('d5_preflight.py'))
    } | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine)
  }
} else {
  $process.WaitForExit()
}

$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
$childRecord = $null
$childHash = $null
if (Test-Path $childReceipt) {
  $childHash = (Get-FileHash -Algorithm SHA256 $childReceipt).Hash.ToLowerInvariant()
  try { $childRecord = Get-Content -Raw $childReceipt | ConvertFrom-Json } catch { $childRecord = $null }
}
$wrapperPass = (-not $timedOut) -and $process.ExitCode -eq 0 -and $elapsed -le 75 -and $childRecord -and $childRecord.status -eq 'PASS_ADMISSION_READY_TO_LAUNCH' -and [double]$childRecord.elapsed_seconds -le 75
$wrapper = [ordered]@{
  status = if ($wrapperPass) { 'PASS_ADMISSION_WATCHDOG' } else { 'FAIL_ADMISSION_WATCHDOG' }
  run_id = 'HQ-ROAD-CENTERLINE-001-R001'
  task_name = 'HQ-ROAD-CENTERLINE-001-R001-20261020'
  overall_check_number = 3
  prior_checks_consumed = 2
  additional_check_number = 1
  additional_check_limit_seconds = 75
  timed_out = $timedOut
  child_exit_code = if ($timedOut) { $null } else { $process.ExitCode }
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
