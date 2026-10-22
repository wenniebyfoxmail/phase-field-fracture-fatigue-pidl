param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$proc=$null
try {
$limitSeconds=21600
if ($null -ne $c.timeout_seconds) { $limitSeconds=[double]$c.timeout_seconds }
if ($limitSeconds -le 0 -or $limitSeconds -gt 21600) { throw 'Invalid bounded timeout' }
$totalEnd=[DateTime]::Parse($c.total_deadline_utc).ToUniversalTime()
$limitSeconds=[Math]::Min($limitSeconds,($totalEnd.AddSeconds(-1800)-[DateTime]::UtcNow).TotalSeconds)
if ($limitSeconds -le 0) { throw 'No science budget after original cleanup reserve' }
$receipt=Join-Path $c.root 'launch.json'
if (Test-Path -LiteralPath $receipt) { throw 'Launch already recorded; inspect before any retry' }
if (Test-Path -LiteralPath $c.output) { throw 'Output already exists; fresh run required' }
if ((Get-PSDrive C).Free -lt 15GB) { throw 'Insufficient storage headroom' }
if ($c.kind -eq 'fem') {
    if (@(Get-CimInstance Win32_Process -Filter "Name='MATLAB.exe'").Count -gt 0) {
        throw 'Another MATLAB process exists; FEM admission blocked'
    }
    $env:MATLAB_PREFDIR=Join-Path $c.root 'prefs'
    New-Item -ItemType Directory -Force $env:MATLAB_PREFDIR | Out-Null
} else {
    # A reservation release must be supplied separately; idle utilization alone
    # never authorizes this launch. This file is created only after coordination.
    if (-not (Test-Path -LiteralPath (Join-Path $c.root 'GPU_RELEASED.json'))) {
        throw 'Reserved GPU has not been released for this task'
    }
    if ($c.kind -ne 'pidl') { throw 'Wrong producer kind' }
    $qualified=Get-Content -LiteralPath (Join-Path $c.root 'GPU_RELEASED.json') -Raw | ConvertFrom-Json
    if (-not $qualified.reference.complete_valid_reference -or $qualified.reference.accepted_prefix -ne 24) { throw 'Unqualified FEM reference' }
    if ((Get-FileHash (Join-Path $c.root 'GPU_RELEASED.json')).Hash.ToLower() -ne $c.reference_sha256) { throw 'Reference receipt changed' }
    $g=[string](& nvidia-smi --id=0 --query-gpu=uuid,memory.free,utilization.gpu --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0) { throw 'GPU query failed' }
    $parts=$g.Split(',')
    if ($parts[0].Trim() -ne $c.gpu_uuid -or [double]$parts[1] -lt 24576 -or [double]$parts[2] -gt 5) { throw 'GPU admission changed' }
    if (@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'python*'}).Count) { throw 'Competing Python process' }
    $temp=Join-Path $c.root 'tmp';New-Item -ItemType Directory -Force $temp | Out-Null
    $env:TEMP=$temp;$env:TMP=$temp;$env:MPLCONFIGDIR=$temp;$env:TORCH_HOME=$temp
    $env:TORCHINDUCTOR_CACHE_DIR=$temp;$env:TRITON_CACHE_DIR=$temp;$env:CUDA_CACHE_PATH=$temp
    $env:OMP_NUM_THREADS='4';$env:OPENBLAS_NUM_THREADS='4';$env:MKL_NUM_THREADS='4'
    $env:PYTHONDONTWRITEBYTECODE='1'
    $env:CUDA_VISIBLE_DEVICES=[string]$c.gpu_uuid
    $env:PYTHONPATH=Join-Path $c.root 'deps'
    $env:PYTHONUNBUFFERED='1'
}
$claim=[System.IO.File]::Open($receipt,[System.IO.FileMode]::CreateNew)
$claim.Dispose()
$started=[DateTime]::UtcNow
$scienceEnd=$started.AddSeconds($limitSeconds)
if ($scienceEnd -gt $totalEnd.AddSeconds(-1800)) { $scienceEnd=$totalEnd.AddSeconds(-1800) }
if(($scienceEnd-[DateTime]::UtcNow).TotalSeconds -le 0){throw 'No exact-start science time before original cleanup cutoff'}
$runnerHours=($scienceEnd-[DateTime]::UtcNow).TotalHours
if ($runnerHours -le 0) { throw 'No PIDL time left' }
$hoursString=$runnerHours.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)
$c.arguments=[string]$c.arguments+' --hours '+$hoursString
$proc=Start-Process -FilePath $c.executable -ArgumentList $c.arguments -WorkingDirectory $c.root `
    -RedirectStandardOutput (Join-Path $c.root 'stdout.log') `
    -RedirectStandardError (Join-Path $c.root 'stderr.log') -PassThru
$childHandle=$proc.Handle
try { $proc.ProcessorAffinity=[IntPtr]15 } catch { $proc.Kill(); $proc.WaitForExit(); throw }
$peakRSS=0
@{pid=$proc.Id;started_utc=$started.ToString('o');host=$env:COMPUTERNAME;kind=$c.kind;
  executable=$c.executable;arguments=$c.arguments;root=$c.root;output=$c.output;code_commit=$c.commit;
  deadline_seconds=$limitSeconds;science_deadline_utc=$scienceEnd.ToString('o');output_limit_GiB=10} | ConvertTo-Json | Set-Content -LiteralPath $receipt
$reason='exited'
while ($true) {
    $remaining=[int][Math]::Ceiling(($scienceEnd-[DateTime]::UtcNow).TotalMilliseconds)
    if ($remaining -le 0) {
        $reason='budget_stopped'
        if (-not $proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
        break
    }
    if ($proc.WaitForExit([Math]::Min(1000,$remaining))) { break }
    if ($c.kind -eq 'fem') {
        $guard=Get-ChildItem -LiteralPath $c.output -Filter 'step_guard_*.json' -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
        if ($null -ne $guard) {
            try {
                $g=Get-Content -LiteralPath $guard.FullName -Raw | ConvertFrom-Json
                $done=Join-Path $c.output ('step_done_{0:D3}.txt' -f [int]$g.step)
                if (-not (Test-Path $done) -and [DateTime]::UtcNow -ge [DateTime]::Parse($g.deadline_utc).ToUniversalTime()) {
                    $reason='step_budget_stopped';$proc.Kill();$proc.WaitForExit();break
                }
            } catch {
                $reason='step_guard_monitor_failed';if(-not $proc.HasExited){$proc.Kill();$proc.WaitForExit()};break
            }
        }
    }
    $sample=$null
    try {
        $sample=[System.Diagnostics.Process]::GetProcessById($proc.Id)
        $peakRSS=[Math]::Max($peakRSS,$sample.PeakWorkingSet64)
    } catch {
        if ($proc.HasExited) { break }
        $reason='monitor_failed'; $proc.Kill(); $proc.WaitForExit(); break
    } finally { if ($null -ne $sample) { $sample.Dispose() } }
    if ($peakRSS -gt 16GB) { $reason='memory_stopped'; $proc.Kill(); $proc.WaitForExit(); break }
    $bytes=(Get-ChildItem -LiteralPath $c.root -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if ($bytes -gt 10GB) {
        $reason='budget_stopped'
        # This Process object is the exact child created above; no name/user kill.
        $proc.Kill(); $proc.WaitForExit(); break
    }
}
@{pid=$proc.Id;finished_utc=[DateTime]::UtcNow.ToString('o');exit_code=$proc.ExitCode;
  peak_RSS_bytes=$peakRSS;cpu_affinity=15;total_deadline_utc=$totalEnd.ToString('o');reason=$reason;completed_marker=(Test-Path -LiteralPath (Join-Path $c.output 'COMPLETED.txt'));
  prefix_completed=(Test-Path -LiteralPath (Join-Path $c.output 'PREFIX_COMPLETED.txt'))} |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $c.root 'exit.json')

} catch {
    $message=$_.Exception.ToString()
    if ($null -ne $proc) { if (-not $proc.HasExited) { $proc.Kill();$proc.WaitForExit() } }
    @{reason='supervisor_exception';message=$message;finished_utc=[DateTime]::UtcNow.ToString('o');worker_started=($null -ne $proc)} | ConvertTo-Json | Set-Content (Join-Path $c.root 'supervisor_exception.json')
    throw
}
