param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256)
$ErrorActionPreference='Stop'
$r='C:\Users\xw436\pavetrack_runs\S01-E028-R001';$logs=$r+'-wrapper-logs'
if((Test-Path $r) -or (Test-Path $logs)){throw 'fresh run/log dirs'}
if($env:COMPUTERNAME -ne 'D-26-09' -or (whoami) -ne 'ad\xw436'){throw 'producer identity'}
if(@(Get-Process python* -ErrorAction SilentlyContinue).Count -ne 0){throw 'shared compute conflict'}
$os=Get-CimInstance Win32_OperatingSystem;$load=(Get-CimInstance Win32_Processor|Measure-Object LoadPercentage -Average).Average
if($os.FreePhysicalMemory -lt 8388608 -or $load -ge 50 -or (Get-PSDrive C).Free -lt 17179869184){throw 'CPU/RAM/disk conflict'}
$env:CUDA_VISIBLE_DEVICES='1';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH='';$env:MPLBACKEND='Agg'
New-Item -ItemType Directory $logs|Out-Null
# Keep a native Process handle; do not Refresh() away the observed exit state.
$p=New-Object System.Diagnostics.Process
$p.StartInfo.FileName='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$p.StartInfo.Arguments='"'+$Source+'\scripts\pavetrack_target_spatial\run.py" --input "'+$Source+'\private_inputs" --run "'+$r+'" --reviewed-commit '+$ReviewedCommit+' --manifest-sha256 '+$ManifestSha256
$p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true
$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
try{
 if(!$p.Start()){throw 'Python start failed'}
 $retainedHandle=$p.Handle
 $stdoutTask=$p.StandardOutput.ReadToEndAsync();$stderrTask=$p.StandardError.ReadToEndAsync()
 @{python_pid=$p.Id;wrapper_pid=$PID;reviewed_commit=$ReviewedCommit;started_at=(Get-Date -Format o);arguments=$p.StartInfo.Arguments}|ConvertTo-Json|Set-Content "$logs\launch.json" -Encoding UTF8
 if(!$p.WaitForExit(3600000)){
  $v=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
  if($null -eq $v -or $v.CommandLine -notlike '*pavetrack_target_spatial*' -or $v.ParentProcessId -ne $PID){throw 'timeout process identity uncertain'}
  $all=@(Get-CimInstance Win32_Process);$own=@($p.Id);$previous=0
  while($previous -ne $own.Count){$previous=$own.Count;foreach($child in $all){if(($own -contains $child.ParentProcessId) -and ($own -notcontains $child.ProcessId)){$own+=@($child.ProcessId)}}}
  & taskkill.exe /PID $p.Id /T /F|Out-Null
  if($LASTEXITCODE -ne 0 -or @(Get-CimInstance Win32_Process|Where-Object {$own -contains $_.ProcessId}).Count -ne 0){throw 'own tree termination uncertain; inspect without retry'}
  throw 'own source probe exceeded3600s; stopped, no retry'
 }
 $p.WaitForExit();$exitCode=$p.ExitCode
 $stdoutTask.Result|Set-Content "$logs\stdout.log" -Encoding UTF8
 $stderrTask.Result|Set-Content "$logs\stderr.log" -Encoding UTF8
 if($null -eq $exitCode){throw 'exitcode unavailable; inspect saved artifacts without retry'}
 if($exitCode -ne 0){throw "source probe stopped:$exitCode"}
 @{state='completed';exit_code=$exitCode;python_pid=$p.Id;reviewed_commit=$ReviewedCommit;finished_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8
}catch{@{state='stopped';reason=$_.Exception.Message;exit_code=$exitCode;reviewed_commit=$ReviewedCommit;updated_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8;throw}
