$ErrorActionPreference = 'Stop'
$started = Get-Date
$stage = 'C:\Users\xw436\jobs\hq_road_centerline_001_r001_stage_20261020'
$owner = Join-Path $stage 'HQ-ROAD-UQ-FEAS-001'
$d5 = Join-Path $owner 'centerline_target_20261020'
$run = Join-Path $owner 'runs\HQ-ROAD-CENTERLINE-001-R001'
$receiptPath = Join-Path $run 'admission_receipt_remote.json'
$environmentStdout = Join-Path $run 'environment.stdout.json'
$environmentStderr = Join-Path $run 'environment.stderr.log'
$preflightStdout = Join-Path $run 'preflight.stdout.json'
$preflightStderr = Join-Path $run 'preflight.stderr.log'
$python = 'C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$deps = 'C:\Users\xw436\jobs\hq_road_centerline_001_deps_20261020'
$output = 'C:\Users\xw436\jobs\HQ-ROAD-CENTERLINE-001-R001'
$cache = 'C:\Users\xw436\jobs\hq_road_centerline_001_r001_cache_20261020'
$taskName = 'HQ-ROAD-CENTERLINE-001-R001-20261020'
$approvalPath = Join-Path $run 'approval_hq.json'
$lockPath = Join-Path $d5 'd5_data_lock.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
if (Test-Path $receiptPath) { throw "admission receipt already exists; fourth check prohibited: $receiptPath" }
$record = [ordered]@{
  status = 'FAIL_ADMISSION'
  run_id = 'HQ-ROAD-CENTERLINE-001-R001'
  started_iso = $started.ToString('o')
  additional_check_number = 1
  overall_check_number = 3
  prior_checks_consumed = 2
  additional_check_limit_seconds = 75
  scientific_execution_started = $false
  training_steps = 0
  optimizer_steps = 0
  road420_access = $false
  task_name = $taskName
}

try {
  if ((hostname) -ne 'D-26-09') { throw 'hostname mismatch' }
  if (-not (Test-Path $stage) -or -not (Test-Path $d5) -or -not (Test-Path $run)) { throw 'stage incomplete' }
  if (-not (Test-Path $deps)) { throw 'task dependency path missing' }
  if (Test-Path $output) { throw 'canonical output already exists' }
  if (Test-Path $cache) { throw 'canonical cache already exists before preflight' }
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
  if ($LASTEXITCODE -ne 0 -or -not $gpuRaw) { throw 'GPU 0 query failed' }
  $gpuParts = @($gpuRaw.Split(',') | ForEach-Object { $_.Trim() })
  if ($gpuParts.Count -ne 6 -or $gpuParts[0] -ne '0') { throw "unexpected GPU query: $gpuRaw" }
  if ([double]$gpuParts[4] -lt 16384) { throw "GPU 0 has less than 16 GiB free: $($gpuParts[4]) MiB" }
  $computeRaw = (& nvidia-smi -i 0 --query-compute-apps=pid,process_name,used_gpu_memory,gpu_uuid --format=csv,noheader,nounits 2>$null) -join "`n"
  if ($LASTEXITCODE -ne 0) { throw 'GPU 0 compute-process query failed' }
  $computeLines = @($computeRaw -split "`r?`n" | Where-Object { $_.Trim() })
  if ($computeLines.Count -gt 0) { throw "GPU 0 has compute processes: $computeRaw" }
  $disk = Get-PSDrive -Name C
  $freeGiB = [math]::Round($disk.Free / 1GB, 3)
  if ($freeGiB -lt 25) { throw "C drive has less than 25 GiB free: $freeGiB" }

  $env:CUDA_VISIBLE_DEVICES='0'
  $env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
  $env:PYTHONUTF8='1'
  $env:PYTHONPATH=$deps
  $env:HQ_RUN_LAUNCH_ID=$taskName
  $env:OMP_NUM_THREADS='4'; $env:MKL_NUM_THREADS='4'; $env:OPENBLAS_NUM_THREADS='4'
  $env:NUMEXPR_NUM_THREADS='4'; $env:VECLIB_MAXIMUM_THREADS='4'; $env:BLIS_NUM_THREADS='4'

  Push-Location $d5
  try {
    $environmentSeconds = 75 - ((Get-Date) - $started).TotalSeconds
    if ($environmentSeconds -le 2) { throw 'no admission time remains for environment probe' }
    $environmentProcess = Start-Process -FilePath $python -ArgumentList @('-c',"j=__import__('json');d=__import__('d5_runner');print(j.dumps(d.environment()))") -NoNewWindow -PassThru -RedirectStandardOutput $environmentStdout -RedirectStandardError $environmentStderr
    if (-not $environmentProcess.WaitForExit([int](1000 * ($environmentSeconds - 1)))) {
      Stop-Process -Id $environmentProcess.Id -Force -ErrorAction SilentlyContinue
      throw 'environment probe exceeded remaining admission time and was terminated'
    }
    $environmentProcess.WaitForExit()
    if ($environmentProcess.ExitCode -ne 0) { throw "environment probe failed; see $environmentStderr" }
    $environmentRaw = Get-Content -Raw $environmentStdout
    $environment = $environmentRaw | ConvertFrom-Json
    $approval = Get-Content -Raw $approvalPath | ConvertFrom-Json
    $approval.environment = $environment
    [System.IO.File]::WriteAllText($approvalPath, ($approval | ConvertTo-Json -Depth 10), $utf8)

    $matrix = Join-Path $owner 'runs\HQ-ROAD-UQ-MATRIX-001-R001\retrieved_2026-10-19\HQ-ROAD-UQ-MATRIX-001-R001'
    $preflightArgs = @(
      'd5_preflight.py', '--approval', $approvalPath, '--lock', $lockPath,
      '--trainzip', 'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\traincrop.zip',
      '--valzip', 'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\valcrop.zip',
      '--cfd', 'C:\Users\xw436\jobs\hq_road_uq_feas_001_data_20261011\CFD',
      '--gapszip', 'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\GAPs384_raw_img_gt.zip',
      '--weights', 'C:\Users\xw436\jobs\hq_road_uq_feas_002_data_20261019\resnet18-f37072fd.pth',
      '--d1-checkpoint', 'C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-001-R001\best.pt',
      '--d2-checkpoint', 'C:\Users\xw436\jobs\HQ-ROAD-UQ-FEAS-002-R001\best.pt',
      '--d3-old-cfd-csv', (Join-Path $matrix 'old_cfd_metrics.csv'),
      '--d3-old-gaps-csv', (Join-Path $matrix 'old_gaps384_metrics.csv'),
      '--d3-repair-cfd-csv', (Join-Path $matrix 'repair_cfd_metrics.csv'),
      '--d3-repair-gaps-csv', (Join-Path $matrix 'repair_gaps384_metrics.csv'),
      '--cache', $cache, '--output', $output
    )
    $remainingSeconds = 75 - ((Get-Date) - $started).TotalSeconds
    if ($remainingSeconds -le 1) { throw 'no admission time remains for preflight' }
    $preflightProcess = Start-Process -FilePath $python -ArgumentList $preflightArgs -NoNewWindow -PassThru -RedirectStandardOutput $preflightStdout -RedirectStandardError $preflightStderr
    if (-not $preflightProcess.WaitForExit([int](1000 * ($remainingSeconds - 1)))) {
      Stop-Process -Id $preflightProcess.Id -Force -ErrorAction SilentlyContinue
      throw 'D5 preflight exceeded remaining admission time and was terminated'
    }
    $preflightProcess.WaitForExit()
    if ($preflightProcess.ExitCode -ne 0) { throw "D5 preflight failed; see $preflightStderr" }
    $preflightRaw = Get-Content -Raw $preflightStdout
    $preflight = $preflightRaw | ConvertFrom-Json
  } finally {
    Pop-Location
  }

  $elapsed = ((Get-Date) - $started).TotalSeconds
  if ($elapsed -gt 75) { throw "additional admission check exceeded 75 seconds: $elapsed" }
  if (Test-Path $output) { throw 'preflight created scientific output' }
  if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'scheduled task appeared during preflight' }
  foreach ($name in @('train','val')) {
    $marker = Join-Path (Join-Path $cache $name) '.complete'
    if (-not (Test-Path $marker)) { throw "cache marker missing: $marker" }
  }

  $record.status = 'PASS_ADMISSION_READY_TO_LAUNCH'
  $record.hostname = 'D-26-09'
  $record.gpu = [ordered]@{query=$gpuRaw; compute_processes=@($computeLines); free_mib=[double]$gpuParts[4]}
  $record.c_free_gib = $freeGiB
  $record.environment = $environment
  $record.preflight = $preflight
  $record.code_snapshot = $preflight.code_snapshot
  $record.data_lock_sha256 = $preflight.data_lock_sha256
  $record.canonical_output_exists = $false
  $record.canonical_cache_markers_verified = $true
  $record.scheduled_task_exists = $false
} catch {
  $record.error = $_.Exception.Message
} finally {
  $record.ended_iso = (Get-Date).ToString('o')
  $record.elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
  if ($record.elapsed_seconds -gt 75 -and $record.status -eq 'PASS_ADMISSION_READY_TO_LAUNCH') {
    $record.status = 'FAIL_ADMISSION'
    $record.error = "admission exceeded 75 seconds: $($record.elapsed_seconds)"
  }
  [System.IO.File]::WriteAllText($receiptPath, ($record | ConvertTo-Json -Depth 12), $utf8)
}

if ($record.status -ne 'PASS_ADMISSION_READY_TO_LAUNCH') { exit 2 }
exit 0
