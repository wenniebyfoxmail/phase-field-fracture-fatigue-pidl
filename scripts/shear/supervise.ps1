param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
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
    $env:CUDA_VISIBLE_DEVICES='0'
    $env:PYTHONPATH=Join-Path $c.root 'deps'
    $env:PYTHONUNBUFFERED='1'
}
$claim=[System.IO.File]::Open($receipt,[System.IO.FileMode]::CreateNew)
$claim.Dispose()
$proc=Start-Process -FilePath $c.executable -ArgumentList $c.arguments -WorkingDirectory $c.root `
    -RedirectStandardOutput (Join-Path $c.root 'stdout.log') `
    -RedirectStandardError (Join-Path $c.root 'stderr.log') -PassThru
$started=[DateTime]::UtcNow
@{pid=$proc.Id;started_utc=$started.ToString('o');host=$env:COMPUTERNAME;kind=$c.kind;
  executable=$c.executable;arguments=$c.arguments;root=$c.root;output=$c.output;code_commit=$c.commit;
  deadline_hours=4;output_limit_GiB=10} | ConvertTo-Json | Set-Content -LiteralPath $receipt
$reason='exited'
while (-not $proc.WaitForExit(30000)) {
    $bytes=(Get-ChildItem -LiteralPath $c.output -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if (([DateTime]::UtcNow-$started).TotalHours -ge 4 -or $bytes -gt 10GB) {
        $reason='budget_stopped'
        # This Process object is the exact child created above; no name/user kill.
        $proc.Kill(); $proc.WaitForExit(); break
    }
}
$proc.Refresh()
@{pid=$proc.Id;finished_utc=[DateTime]::UtcNow.ToString('o');exit_code=$proc.ExitCode;
  reason=$reason;completed_marker=(Test-Path -LiteralPath (Join-Path $c.output 'COMPLETED.txt'))} |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $c.root 'exit.json')
