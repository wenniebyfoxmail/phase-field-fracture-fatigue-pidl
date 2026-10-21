$ErrorActionPreference = 'Stop'
$started = Get-Date
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r005_stage_20261021'
$owner = Join-Path $stage 'HQ-ROAD-UQ-FEAS-001'
$d5 = Join-Path $owner 'centerline_target_r005_20261021'
$run = Join-Path $owner 'runs\HQ-ROAD-CENTERLINE-001-R005'
$receiptPath = Join-Path $run 'admission_receipt_remote.json'
$controller = Join-Path $d5 'owned_subprocess.py'
$environmentInvocation = Join-Path $d5 'environment.invocation.json'
$preflightInvocation = Join-Path $d5 'preflight.invocation.json'
$python = 'C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$deps = 'C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020'
$output = 'C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R005'
$cache = 'C:\Users\xw436\jobs\hq_road_centerline_001_r005_cache_20261021'
$taskName = 'HQ-ROAD-CENTERLINE-001-R005-20261021'
$approvalPath = Join-Path $run 'approval_hq.json'
$launchReceiptPath = Join-Path $run 'launch_receipt_remote.json'
$lockPath = Join-Path $d5 'd5_data_lock.json'
$packageStart = [DateTimeOffset]::Parse('2026-10-20T21:59:35Z')
$packageDeadline = [DateTimeOffset]::Parse('2026-10-21T01:59:35Z')
$minimumLaunchRemainingSeconds = 1900
$expectedGpuUuid = 'GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7'
$knownDesktopPatterns = @(
  '^C:\\Program Files\\WindowsApps\\OpenAI\.Codex_[^\\]+\\app\\ChatGPT\.exe$',
  '^C:\\Windows\\System32\\dwm\.exe$',
  '^C:\\Windows\\explorer\.exe$',
  '^C:\\Windows\\System32\\LogonUI\.exe$',
  '^C:\\Windows\\SystemApps\\ShellExperienceHost_[^\\]+\\ShellExperienceHost\.exe$',
  '^C:\\Program Files \(x86\)\\Microsoft\\EdgeWebView\\Application\\[^\\]+\\msedgewebview2\.exe$',
  '^C:\\Program Files\\WindowsApps\\MSTeams_[^\\]+\\ms-teams\.exe$'
)
function Test-KnownDesktopBackground([string]$ProcessPath, [string]$UsedMemory, [string]$GpuUuid, [string]$ObservedName, [string]$ObservedPath) {
  $pathKnown = $false
  foreach ($pattern in $knownDesktopPatterns) { if ($ProcessPath -match $pattern) { $pathKnown = $true; break } }
  $nameConsistent = $ObservedName -and ([IO.Path]::GetFileName($ProcessPath) -ieq $ObservedName)
  $pathConsistent = $ObservedPath -and ([IO.Path]::GetFullPath($ProcessPath) -ieq [IO.Path]::GetFullPath($ObservedPath))
  return $UsedMemory -eq '[N/A]' -and $GpuUuid -eq $expectedGpuUuid -and $pathKnown -and $nameConsistent -and $pathConsistent
}
function Get-RequiredInteger($Object, [string]$Name, [string]$Context) {
  $property = $Object.PSObject.Properties[$Name]
  if (-not $property -or $null -eq $property.Value) { throw "$Context missing integer property: $Name" }
  $text = [string]$property.Value
  if ($text -notmatch '^-?\d+$') { throw "$Context malformed integer property: $Name" }
  return [int]$text
}
function Get-OwnedReceipt([string]$InvocationPath, [string]$ExpectedRole) {
  if (-not (Test-Path -LiteralPath $InvocationPath)) { throw "owned invocation missing: $InvocationPath" }
  $invocation = Get-Content -Raw -LiteralPath $InvocationPath | ConvertFrom-Json
  foreach ($path in @($invocation.receipt_path,$invocation.exitcode_path,$invocation.stdout_path,$invocation.stderr_path)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "owned child evidence missing: $path" }
  }
  $receipt = Get-Content -Raw -LiteralPath $invocation.receipt_path | ConvertFrom-Json
  $approval = Get-Content -Raw -LiteralPath $invocation.approval_path | ConvertFrom-Json
  $exitText = (Get-Content -Raw -LiteralPath $invocation.exitcode_path).Trim()
  if ($exitText -notmatch '^-?\d+$') { throw "owned child exit sidecar malformed: $($invocation.exitcode_path)" }
  $childExitCode = Get-RequiredInteger $receipt 'child_exit_code' $ExpectedRole
  $controllerExitCode = Get-RequiredInteger $receipt 'controller_exit_code' $ExpectedRole
  $invocationSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $InvocationPath).Hash.ToLowerInvariant()
  if ($receipt.schema -ne 1 -or $receipt.run_id -ne 'HQ-ROAD-CENTERLINE-001-R005' -or $receipt.role -ne $ExpectedRole) { throw "owned child identity mismatch: $ExpectedRole" }
  if ($receipt.invocation_sha256 -ne $invocationSha -or $receipt.code_snapshot -ne $approval.code_snapshot -or $receipt.data_lock_sha256 -ne $approval.data_lock_sha256) { throw "owned child source/data binding mismatch: $ExpectedRole" }
  $claimPath = [string]$invocation.receipt_path + '.claim'
  if (-not (Test-Path -LiteralPath $claimPath) -or $receipt.claim_sha256 -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $claimPath).Hash.ToLowerInvariant()) { throw "owned child exclusive claim mismatch: $ExpectedRole" }
  if ($controllerExitCode -ne [int]$exitText) { throw "owned child JSON/numeric exit disagreement: $ExpectedRole" }
  foreach ($name in @('stdout','stderr')) {
    $path = [string]$invocation.PSObject.Properties[($name + '_path')].Value
    $evidence = $receipt.$name
    if ([long](Get-Item -LiteralPath $path).Length -ne [long]$evidence.bytes -or (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $evidence.sha256) { throw "owned child $name evidence mismatch: $ExpectedRole" }
  }
  if ($receipt.status -ne 'COMPLETE_ZERO' -or $receipt.timed_out -ne $false -or $childExitCode -ne 0 -or $controllerExitCode -ne 0) { throw "owned child did not complete with exit 0: $ExpectedRole status=$($receipt.status) child=$childExitCode controller=$controllerExitCode" }
  return [ordered]@{ invocation=$invocation; receipt=$receipt }
}
$utf8 = New-Object System.Text.UTF8Encoding($false)
if (Test-Path $receiptPath) { throw "R005 admission receipt already exists; second R005 check prohibited: $receiptPath" }
$record = [ordered]@{
  status = 'FAIL_ADMISSION'
  run_id = 'HQ-ROAD-CENTERLINE-001-R005'
  started_iso = $started.ToString('o')
  r005_check_number = 1
  r005_check_cap = 1
  r001_checks_preserved = 3
  r001_approx_seconds_preserved = 45.544
  r002_checks_preserved = 1
  r002_approx_seconds_preserved = 12.359
  r003_checks_preserved = 1
  r003_scientific_attempts_preserved = 1
  r003_worker_seconds_preserved = 4.313
  r004_admission_checks_preserved = 1
  r004_admission_seconds_preserved = 8.250
  r004_scientific_attempts_preserved = 0
  check_limit_seconds = 90
  package_clock_start_utc = $packageStart.ToString('o')
  package_deadline_utc = $packageDeadline.ToString('o')
  package_elapsed_seconds_at_check_start = [math]::Round(([DateTimeOffset]::UtcNow - $packageStart).TotalSeconds, 3)
  package_remaining_seconds_at_check_start = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
  scientific_execution_started = $false
  training_steps = 0
  optimizer_steps = 0
  road420_access = $false
  task_name = $taskName
  gpu_query_raw = $null
  gpu_compute_rows_raw = @()
  gpu_process_classification = @()
  aggregate_free_mib = $null
  actual_gpu_uuid = $null
  gpu_query_exit_code = $null
  gpu_compute_query_exit_code = $null
  c_free_gib = $null
  classification_fixture = $null
}

try {
  if ((hostname) -ne 'D-26-09') { throw 'hostname mismatch' }
  $fixturePath = 'C:\Program Files\WindowsApps\OpenAI.Codex_1_x64__x\app\ChatGPT.exe'
  $fixtureKnown = Test-KnownDesktopBackground $fixturePath '[N/A]' $expectedGpuUuid 'ChatGPT.exe' $fixturePath
  $fixtureNumeric = Test-KnownDesktopBackground $fixturePath '100' $expectedGpuUuid 'ChatGPT.exe' $fixturePath
  $fixtureMissingPath = Test-KnownDesktopBackground $fixturePath '[N/A]' $expectedGpuUuid 'ChatGPT.exe' $null
  $fixturePython = Test-KnownDesktopBackground 'C:\Python\python.exe' '[N/A]' $expectedGpuUuid 'python.exe' 'C:\Python\python.exe'
  $record.classification_fixture = [ordered]@{ known_desktop_na=$fixtureKnown; known_desktop_numeric=$fixtureNumeric; known_desktop_missing_observed_path=$fixtureMissingPath; unknown_python_na=$fixturePython }
  if (-not $fixtureKnown -or $fixtureNumeric -or $fixtureMissingPath -or $fixturePython) { throw 'GPU classification fixture failed' }
  if (-not (Test-Path $stage) -or -not (Test-Path $d5) -or -not (Test-Path $run)) { throw 'stage incomplete' }
  if (-not (Test-Path $deps)) { throw 'task dependency path missing' }
  if (Test-Path $output) { throw 'canonical output already exists' }
  if (Test-Path $cache) { throw 'canonical cache already exists before preflight' }
  if (Test-Path $launchReceiptPath) { throw 'launch receipt already exists' }
  if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'scheduled task already exists' }

  $required = @(
    'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\traincrop.zip',
    'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\valcrop.zip',
    'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\GAPs384_raw_img_gt.zip',
    'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\resnet18-f37072fd.pth',
    'C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\CFD',
    'C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001\best.pt',
    'C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001\best.pt',
    (Join-Path $owner 'runs\HQ-ROAD-UQ-MATRIX-001-R001\retrieved_2026-10-19\HQ-ROAD-UQ-MATRIX-001-R001\old_cfd_metrics.csv'),
    (Join-Path $owner 'runs\HQ-ROAD-UQ-MATRIX-001-R001\retrieved_2026-10-19\HQ-ROAD-UQ-MATRIX-001-R001\old_gaps384_metrics.csv'),
    (Join-Path $owner 'runs\HQ-ROAD-UQ-MATRIX-001-R001\retrieved_2026-10-19\HQ-ROAD-UQ-MATRIX-001-R001\repair_cfd_metrics.csv'),
    (Join-Path $owner 'runs\HQ-ROAD-UQ-MATRIX-001-R001\retrieved_2026-10-19\HQ-ROAD-UQ-MATRIX-001-R001\repair_gaps384_metrics.csv')
  )
  $missing = @($required | Where-Object { -not (Test-Path $_) })
  if ($missing.Count -gt 0) { throw "required paths missing: $($missing -join '; ')" }

  $gpuRaw = (& nvidia-smi -i 0 --query-gpu=index,uuid,name,memory.total,memory.free,utilization.gpu --format=csv,noheader,nounits) -join ''
  $gpuExitCode = $LASTEXITCODE
  $record.gpu_query_raw = $gpuRaw
  $record.gpu_query_exit_code = $gpuExitCode
  if ($gpuExitCode -ne 0 -or -not $gpuRaw) { throw 'GPU 0 query failed' }
  $gpuParts = @($gpuRaw.Split(',') | ForEach-Object { $_.Trim() })
  if ($gpuParts.Count -ne 6 -or $gpuParts[0] -ne '0') { throw "unexpected GPU query: $gpuRaw" }
  $record.aggregate_free_mib = [double]$gpuParts[4]
  $record.actual_gpu_uuid = $gpuParts[1]
  if ($gpuParts[1] -ne $expectedGpuUuid) { throw "GPU 0 UUID mismatch: $($gpuParts[1])" }
  if ([double]$gpuParts[4] -lt 16384) { throw "GPU 0 has less than 16 GiB free: $($gpuParts[4]) MiB" }
  $computeRaw = (& nvidia-smi -i 0 --query-compute-apps=pid,process_name,used_gpu_memory,gpu_uuid --format=csv,noheader,nounits 2>$null) -join "`n"
  $computeExitCode = $LASTEXITCODE
  $record.gpu_compute_rows_raw = @($computeRaw -split "`r?`n" | Where-Object { $_.Trim() })
  $record.gpu_compute_query_exit_code = $computeExitCode
  if ($computeExitCode -ne 0) { throw 'GPU 0 compute-process query failed' }
  $computeLines = @($computeRaw -split "`r?`n" | Where-Object { $_.Trim() })
  $classifications = @()
  $conflicts = @()
  foreach ($line in $computeLines) {
    $parts = @($line.Split(',') | ForEach-Object { $_.Trim() })
    if ($parts.Count -ne 4 -or $parts[0] -notmatch '^\d+$') {
      $entry = [ordered]@{ raw=$line; classification='UNKNOWN_COMPUTE_ROW'; reason='unparseable row' }
      $classifications += $entry; $conflicts += $entry; continue
    }
    $pidValue = [int]$parts[0]
    $processPath = $parts[1]
    $usedMemory = $parts[2]
    $gpuUuid = $parts[3]
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $actualName = if ($process) { [string]$process.Name } else { $null }
    $actualPath = if ($process) { [string]$process.ExecutablePath } else { $null }
    $commandLine = if ($process) { [string]$process.CommandLine } else { $null }
    $isBackground = $process -and (Test-KnownDesktopBackground $processPath $usedMemory $gpuUuid $actualName $actualPath)
    $entry = [ordered]@{
      raw = $line
      pid = $pidValue
      nvidia_process_path = $processPath
      used_gpu_memory = $usedMemory
      gpu_uuid = $gpuUuid
      observed_name = $actualName
      observed_executable_path = $actualPath
      observed_command_line = $commandLine
      classification = if ($isBackground) { 'KNOWN_DESKTOP_BACKGROUND_NA_MEMORY' } else { 'UNKNOWN_OR_COMPETING_COMPUTE_PROCESS' }
    }
    $classifications += $entry
    if (-not $isBackground) { $conflicts += $entry }
  }
  $record.gpu_process_classification = @($classifications)
  $ownedOrClaiming = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine.Contains('HQ-ROAD-CENTERLINE-001-R005') -or $_.CommandLine.Contains('d5_runner.py')) -and
    -not $_.CommandLine.Contains('d5_admission.ps1') -and -not $_.CommandLine.Contains('d5_preflight.py')
  } | Select-Object ProcessId, Name, ExecutablePath, CommandLine)
  if ($ownedOrClaiming.Count -gt 0) { throw "existing HQ/D5 runner claim detected: $($ownedOrClaiming | ConvertTo-Json -Compress)" }
  if ($conflicts.Count -gt 0) { throw "unclassified or competing GPU 0 process: $($conflicts | ConvertTo-Json -Compress)" }
  $disk = Get-PSDrive -Name C
  $freeGiB = [math]::Round($disk.Free / 1GB, 3)
  $record.c_free_gib = $freeGiB
  if ($freeGiB -lt 25) { throw "C drive has less than 25 GiB free: $freeGiB" }
  $remainingPackageSeconds = ($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds
  if ($remainingPackageSeconds -lt $minimumLaunchRemainingSeconds) { throw "original package clock cannot fit complete run: $remainingPackageSeconds seconds remain" }

  $env:CUDA_VISIBLE_DEVICES='0'
  $env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
  $env:PYTHONUTF8='1'
  $env:PYTHONPATH=$deps
  $env:HQ_RUN_LAUNCH_ID=$taskName
  $env:OMP_NUM_THREADS='4'; $env:MKL_NUM_THREADS='4'; $env:OPENBLAS_NUM_THREADS='4'
  $env:NUMEXPR_NUM_THREADS='4'; $env:VECLIB_MAXIMUM_THREADS='4'; $env:BLIS_NUM_THREADS='4'

  Push-Location $d5
  try {
    if ((90 - ((Get-Date) - $started).TotalSeconds) -le 2) { throw 'no admission time remains for environment probe' }
    & $python $controller $environmentInvocation | Out-Null
    $environmentControl = Get-OwnedReceipt $environmentInvocation 'environment'
    $environmentRaw = Get-Content -Raw -LiteralPath $environmentControl.invocation.stdout_path
    $environment = $environmentRaw | ConvertFrom-Json
    $environmentContext = Get-Content -Raw -LiteralPath (Join-Path $run 'environment.context.json') | ConvertFrom-Json
    if ($environmentContext.status -ne 'PASS_SCHEDULED_CONTEXT' -or $environmentContext.run_id -ne 'HQ-ROAD-CENTERLINE-001-R005' -or $environmentContext.dependency_root -ne $deps -or $environmentControl.receipt.context_ownership -notin @('SAME_PROCESS','DIRECT_CHILD_OF_OWNED_LAUNCHER')) { throw 'environment bootstrap context mismatch' }
    $approval = Get-Content -Raw $approvalPath | ConvertFrom-Json
    $approval.environment = $environment
    [System.IO.File]::WriteAllText($approvalPath, ($approval | ConvertTo-Json -Depth 10), $utf8)

    if ((90 - ((Get-Date) - $started).TotalSeconds) -le 1) { throw 'no admission time remains for preflight' }
    & $python $controller $preflightInvocation | Out-Null
    $preflightControl = Get-OwnedReceipt $preflightInvocation 'preflight'
    $preflightRaw = Get-Content -Raw -LiteralPath $preflightControl.invocation.stdout_path
    $preflight = $preflightRaw | ConvertFrom-Json
    $preflightContext = Get-Content -Raw -LiteralPath (Join-Path $run 'preflight.context.json') | ConvertFrom-Json
    if ($preflightContext.status -ne 'PASS_SCHEDULED_CONTEXT' -or $preflightContext.run_id -ne 'HQ-ROAD-CENTERLINE-001-R005' -or $preflightContext.dependency_root -ne $deps -or $preflightControl.receipt.context_ownership -notin @('SAME_PROCESS','DIRECT_CHILD_OF_OWNED_LAUNCHER')) { throw 'preflight bootstrap context mismatch' }
  } finally {
    Pop-Location
  }

  $elapsed = ((Get-Date) - $started).TotalSeconds
  if ($elapsed -gt 90) { throw "R005 admission check exceeded 90 seconds: $elapsed" }
  if (Test-Path $output) { throw 'preflight created scientific output' }
  if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'scheduled task appeared during preflight' }
  foreach ($name in @('train','val')) {
    $marker = Join-Path (Join-Path $cache $name) '.complete'
    if (-not (Test-Path $marker)) { throw "cache marker missing: $marker" }
  }

  $record.status = 'PASS_ADMISSION_READY_TO_LAUNCH'
  $record.hostname = 'D-26-09'
  $record.gpu = [ordered]@{query=$gpuRaw; compute_processes=@($computeLines); classifications=@($classifications); free_mib=[double]$gpuParts[4]; uuid=$gpuParts[1]}
  $record.environment = $environment
  $record.environment_context = $environmentContext
  $record.environment_control = $environmentControl.receipt
  $record.preflight = $preflight
  $record.preflight_context = $preflightContext
  $record.preflight_control = $preflightControl.receipt
  $record.code_snapshot = $preflight.code_snapshot
  $record.data_lock_sha256 = $preflight.data_lock_sha256
  $record.canonical_output_exists = $false
  $record.canonical_cache_markers_verified = $true
  $record.scheduled_task_exists = $false
  $record.launch_receipt_exists = $false
  $record.package_elapsed_seconds_at_admission_end = [math]::Round(([DateTimeOffset]::UtcNow - $packageStart).TotalSeconds, 3)
  $record.package_remaining_seconds_at_admission_end = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
} catch {
  $record.error = $_.Exception.Message
} finally {
  $record.ended_iso = (Get-Date).ToString('o')
  $record.elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
  $record.package_elapsed_seconds_at_receipt = [math]::Round(([DateTimeOffset]::UtcNow - $packageStart).TotalSeconds, 3)
  $record.package_remaining_seconds_at_receipt = [math]::Round(($packageDeadline - [DateTimeOffset]::UtcNow).TotalSeconds, 3)
  if ($record.elapsed_seconds -gt 90 -and $record.status -eq 'PASS_ADMISSION_READY_TO_LAUNCH') {
    $record.status = 'FAIL_ADMISSION'
    $record.error = "R005 admission exceeded 90 seconds: $($record.elapsed_seconds)"
  }
  [System.IO.File]::WriteAllText($receiptPath, ($record | ConvertTo-Json -Depth 12), $utf8)
}

if ($record.status -ne 'PASS_ADMISSION_READY_TO_LAUNCH') { exit 2 }
exit 0
