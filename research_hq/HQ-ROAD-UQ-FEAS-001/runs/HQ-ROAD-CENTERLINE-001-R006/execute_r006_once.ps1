$ErrorActionPreference = 'Stop'
$clockPath = 'C:\Users\xw436\jobs\hq_road_centerline_001_r006_mechanical_clock.json'
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r006_stage_20261021\HQ-ROAD-UQ-FEAS-001'
$run = Join-Path $stage 'runs\HQ-ROAD-CENTERLINE-001-R006'
$admissionScript = Join-Path $stage 'centerline_target_r006_20261021\invoke_d5_admission_once.ps1'
$registerScript = Join-Path $run 'register_and_start.ps1'
$receiptPath = Join-Path $run 'mechanical_window_receipt.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not (Test-Path $clockPath)) { throw 'R006 mechanical clock missing' }
if (Test-Path $receiptPath) { throw 'R006 mechanical receipt exists; repeat prohibited' }
$clock = Get-Content -Raw $clockPath | ConvertFrom-Json
if ($clock.run_id -ne 'HQ-ROAD-CENTERLINE-001-R006' -or $clock.cap_seconds -ne 90) { throw 'R006 mechanical clock identity mismatch' }
$started = [DateTimeOffset]::Parse($clock.started_utc)
$deadline = $started.AddSeconds(90)
function Get-RemainingMilliseconds([string]$Phase) {
  $remaining = [math]::Floor(($deadline - [DateTimeOffset]::UtcNow).TotalMilliseconds)
  if ($remaining -le 0) { throw "R006 cumulative mechanical window exhausted before $Phase" }
  return [int][math]::Min($remaining, [int]::MaxValue)
}
function Stop-OwnedProcessTree([int]$ProcessId) {
  & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-String | Out-Null
}
function Invoke-BoundedOwnedChild([string]$Phase, [string]$Script, [string]$StdoutPath, [string]$StderrPath) {
  $remainingMilliseconds = Get-RemainingMilliseconds $Phase
  $arguments = @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$Script)
  $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -PassThru -NoNewWindow -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
  $completed = $process.WaitForExit($remainingMilliseconds)
  if (-not $completed) {
    Stop-OwnedProcessTree $process.Id
    try { $process.WaitForExit(5000) | Out-Null } catch { }
    throw "R006 cumulative mechanical window timed out during $Phase; owned PID tree $($process.Id) terminated"
  }
  $process.WaitForExit()
  return [pscustomobject]@{phase=$Phase;pid=$process.Id;exit_code=$process.ExitCode;stdout=$StdoutPath;stderr=$StderrPath;remaining_milliseconds_at_start=$remainingMilliseconds}
}
$record = [ordered]@{status='MECHANICAL_WINDOW_FAILED';run_id='HQ-ROAD-CENTERLINE-001-R006';clock=$clock;admission=$null;registration=$null;launch=$null;error=$null}
try {
  $admissionStdout = Join-Path $run 'mechanical_admission.stdout.log'
  $admissionStderr = Join-Path $run 'mechanical_admission.stderr.log'
  $record.admission = Invoke-BoundedOwnedChild 'admission' $admissionScript $admissionStdout $admissionStderr
  if ($record.admission.exit_code -ne 0) { throw "R006 admission failed: $($record.admission.exit_code)" }

  $registerStdout = Join-Path $run 'mechanical_registration.stdout.log'
  $registerStderr = Join-Path $run 'mechanical_registration.stderr.log'
  $record.registration = Invoke-BoundedOwnedChild 'registration' $registerScript $registerStdout $registerStderr
  if ($record.registration.exit_code -ne 0) { throw "R006 registration/start failed: $($record.registration.exit_code)" }
  $launchText = Get-Content -Raw -LiteralPath $registerStdout
  $record.launch = $launchText | ConvertFrom-Json

  [void](Get-RemainingMilliseconds 'launch ownership check')
  $claim = Join-Path $run 'scientific_worker.exit.json.claim'
  $context = Join-Path $run 'scientific_worker.context.json'
  $exit = Join-Path $run 'scientific_worker.exit.json'
  $outputReceipt = 'C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R006\receipt.json'
  $ownedEvidence = (Test-Path $claim) -or (Test-Path $context) -or (Test-Path $exit) -or (Test-Path $outputReceipt)
  if ($record.launch.status -eq 'LAUNCH_DISPATCHED_VERIFIED' -or $ownedEvidence) {
    $record.status = 'MECHANICAL_WINDOW_COMPLETE_LAUNCH_OWNED'
  } else {
    $record.status = 'MECHANICAL_WINDOW_COMPLETE_LAUNCH_UNKNOWN_NO_REPEAT'
  }
  [void](Get-RemainingMilliseconds 'receipt write')
} catch {
  $record.error = $_.Exception.Message
} finally {
  $record.ended_utc = [DateTimeOffset]::UtcNow.ToString('o')
  $record.elapsed_seconds = [math]::Round(([DateTimeOffset]::UtcNow - $started).TotalSeconds,3)
  if ($record.elapsed_seconds -gt 90 -and $record.status -like 'MECHANICAL_WINDOW_COMPLETE*') {
    $record.status='MECHANICAL_WINDOW_FAILED'
    $record.error='cumulative 90-second cap exceeded'
  }
  $temporary = "$receiptPath.tmp.$PID"
  [System.IO.File]::WriteAllText($temporary,($record|ConvertTo-Json -Depth 10),$utf8)
  Move-Item -LiteralPath $temporary -Destination $receiptPath
}
$record | ConvertTo-Json -Depth 10
if ($record.status -notin @('MECHANICAL_WINDOW_COMPLETE_LAUNCH_OWNED','MECHANICAL_WINDOW_COMPLETE_LAUNCH_UNKNOWN_NO_REPEAT')) { exit 2 }
exit 0
