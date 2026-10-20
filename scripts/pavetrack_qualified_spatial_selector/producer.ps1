param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256,[Parameter(Mandatory=$true)][string]$ApprovalFile)
$ErrorActionPreference='Stop'
$r='C:\Users\xw436\pavetrack_runs\S01-E029-R001';$logs=$r+'-wrapper-logs';$python='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$clock=[Diagnostics.Stopwatch]::StartNew();$exitCode=$null;$state='stopped';$reason='not started'
if((Test-Path $r) -or (Test-Path $logs) -or (Test-Path ($r+'-fixed-v1.tar.gz')) -or (Test-Path ($r+'-fixed-v1.tar.gz.part'))){throw 'fresh E029 run/log/package paths required'}
if($env:COMPUTERNAME -ne 'D-26-09' -or (whoami) -ne 'ad\xw436'){throw 'producer identity'}
if(@(Get-Process python* -ErrorAction SilentlyContinue).Count -ne 0){throw 'shared compute conflict'}
$os=Get-CimInstance Win32_OperatingSystem;$load=(Get-CimInstance Win32_Processor|Measure-Object LoadPercentage -Average).Average
if($os.FreePhysicalMemory -lt 8388608 -or $load -ge 50 -or (Get-PSDrive C).Free -lt 17179869184){throw 'CPU/RAM/disk admission stopped'}
$m=Join-Path $Source 'docs/research/S01/S01-E029/source_manifest.json'
if((Get-FileHash $m -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ManifestSha256){throw 'source manifest identity'}
$a=Get-Content -Raw $ApprovalFile|ConvertFrom-Json
if(!$a.execute_once -or $a.run_id -ne 'S01-E029-R001' -or $a.reviewed_commit -ne $ReviewedCommit -or $a.source_manifest_sha256 -ne $ManifestSha256 -or $a.wall_seconds -ne 3600 -or $a.GPU_uuid -ne 'GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7'){throw 'new exact E029 approval required; package is disabled'}
$env:CUDA_VISIBLE_DEVICES='0';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH='C:\Users\xw436\pavetrack_runtime\S01-E028-Pillow-12.3.0-v1';$env:PYTHONDONTWRITEBYTECODE='1';$env:MPLBACKEND='Agg'
New-Item -ItemType Directory $logs|Out-Null
$env:MPLCONFIGDIR=Join-Path $logs 'mplconfig'
# Same retained-Process-handle and owned-tree termination method as E028.
function Invoke-Owned([string]$arguments,[string]$tag,[double]$deadline){
 $p=New-Object Diagnostics.Process;$p.StartInfo.FileName=$python;$p.StartInfo.Arguments=$arguments;$p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true;$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
 $owned=@{};$failure=$null
 try{
  if(!$p.Start()){throw 'Python start failed'};$handle=$p.Handle
  $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
  @{python_launcher_pid=$p.Id;wrapper_pid=$PID;arguments=$arguments;tag=$tag;started_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\$tag-launch.json" -Encoding UTF8
  do{
   $all=@(Get-CimInstance Win32_Process);$ids=@($p.Id);$oldCount=0
   while($oldCount -ne $ids.Count){$oldCount=$ids.Count;foreach($v in $all){if(($ids -contains $v.ParentProcessId) -and ($ids -notcontains $v.ProcessId)){$ids+=@($v.ProcessId)}}}
   foreach($v in $all){if($ids -contains $v.ProcessId){$owned[[int]$v.ProcessId]=$v}}
   $rss=($all|Where-Object {$ids -contains $_.ProcessId}|Measure-Object WorkingSetSize -Sum).Sum
   if($clock.Elapsed.TotalSeconds -ge $deadline -or $rss -gt 4294967296){throw 'external wall/RSS first stop'}
  }while(!$p.WaitForExit(100))
  $p.WaitForExit();$code=$p.ExitCode
  if($null -eq $code -or $code -ne 0){throw "owned stage $tag stopped, exit=$code"}
 }catch{$failure=$_.Exception.Message}
 finally{
  # Verify every captured birth identity; never kill by process name/account.
  $cleanupFailure=$null
  foreach($key in @($owned.Keys)){
   $saved=$owned[$key];$live=Get-CimInstance Win32_Process -Filter "ProcessId=$key"
   if($null -eq $live){continue}
   if($live.CreationDate -ne $saved.CreationDate -or $live.CommandLine -ne $saved.CommandLine){$cleanupFailure='owned PID identity changed; manual inspect';continue}
   if($live.CommandLine -notlike "*$Source*"){$cleanupFailure='owned descendant command identity uncertain';continue}
   & taskkill.exe /PID $key /T /F|Out-Null
   if($LASTEXITCODE -ne 0 -or $null -ne (Get-CimInstance Win32_Process -Filter "ProcessId=$key")){$cleanupFailure='owned tree termination not confirmed; no retry'}
  }
  if($null -ne $stdout -and $p.HasExited){$stdout.Result|Set-Content "$logs\$tag-stdout.log" -Encoding UTF8;$stderr.Result|Set-Content "$logs\$tag-stderr.log" -Encoding UTF8}
  if($cleanupFailure){$failure=([string]$failure)+'; cleanup='+$cleanupFailure}
 }
 if($failure){throw $failure}
 return $code
}
try{
 Invoke-Owned ('"'+$Source+'\scripts\pavetrack_target_spatial\runtime_preflight.py"') 'preflight' ([Math]::Min(120,3480))|Out-Null
 $producerArgs='"'+$Source+'\scripts\pavetrack_qualified_spatial_selector\run.py" --run "'+$r+'" --paths "'+$Source+'\docs\research\S01\S01-E029\private_paths.template.json" --reviewed-commit '+$ReviewedCommit+' --manifest-sha256 '+$ManifestSha256+' --approval-file "'+$ApprovalFile+'"'
 $exitCode=Invoke-Owned $producerArgs 'producer' 3480;$state='completed';$reason='producer completed, no scientific verdict inferred by wrapper'
}catch{$reason=$_.Exception.Message}
@{state=$state;reason=$reason;exit_code=$exitCode;reviewed_commit=$ReviewedCommit;elapsed_seconds=$clock.Elapsed.TotalSeconds;no_retry=$true;finished_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8
# Reserve the final120s inside the same3600s outer wall for a success/stop package.
$left=3600-$clock.Elapsed.TotalSeconds
if($left -le 0){throw 'outer deadline: inspect saved stop files; no automatic packaging retry'}
$pack='"'+$Source+'\scripts\pavetrack_qualified_spatial_selector\pack.py" --run "'+$r+'" --logs "'+$logs+'" --manifest "'+$m+'" --output "'+$r+'-fixed-v1.tar.gz" --seconds '+([Math]::Max(1,$left-1))
Invoke-Owned $pack 'package' 3600|Out-Null
if($state -ne 'completed'){throw $reason}
