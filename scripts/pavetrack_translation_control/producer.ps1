param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256)
$ErrorActionPreference='Stop'
$r='C:\Users\xw436\pavetrack_runs\S01-E026-R001';$logs=$r+'-wrapper-logs'
if((Test-Path $r) -or (Test-Path $logs)){throw 'fresh run/log directories required'}
if($env:COMPUTERNAME -ne 'D-26-09' -or (whoami) -ne 'ad\xw436'){throw 'producer identity'}
if(@(Get-Process python* -ErrorAction SilentlyContinue).Count -ne 0){throw 'shared Python compute conflict'}
$os=Get-CimInstance Win32_OperatingSystem;$load=(Get-CimInstance Win32_Processor|Measure-Object LoadPercentage -Average).Average
if($os.FreePhysicalMemory -lt 8388608 -or $load -ge 50 -or (Get-PSDrive C).Free -lt 1073741824){throw 'CPU/RAM/disk conflict'}
New-Item -ItemType Directory $logs|Out-Null
$env:CUDA_VISIBLE_DEVICES='1';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH='';$env:MPLBACKEND='Agg'
$py='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$arguments=@(('"'+$Source+'\scripts\pavetrack_translation_control\run.py"'),'--source',('"'+$Source+'"'),'--input',('"'+$Source+'\private_controls"'),'--run',('"'+$r+'"'),'--reviewed-commit',$ReviewedCommit,'--manifest-sha256',$ManifestSha256)
try{
 $p=Start-Process -FilePath $py -ArgumentList $arguments -PassThru -RedirectStandardOutput "$logs\stdout.log" -RedirectStandardError "$logs\stderr.log"
 @{python_pid=$p.Id;wrapper_pid=$PID;command=($py+' '+($arguments -join ' '));reviewed_commit=$ReviewedCommit;started_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\launch.json" -Encoding UTF8
 if(!$p.WaitForExit(600000)){
  $v=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
  if($null -eq $v -or $v.CommandLine -notlike '*pavetrack_translation_control*' -or $v.ParentProcessId -ne $PID){throw 'watchdog process identity uncertain'}
  $p.Kill();throw 'own E026 Python exceeded600s; no retry'
 }
 $p.Refresh();if($p.ExitCode -ne 0){throw "E026 stopped:$($p.ExitCode)"}
 @{state='completed';wrapper_pid=$PID;python_pid=$p.Id;reviewed_commit=$ReviewedCommit;finished_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8
}catch{@{state='stopped';reason=$_.Exception.Message;reviewed_commit=$ReviewedCommit;updated_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8;throw}
