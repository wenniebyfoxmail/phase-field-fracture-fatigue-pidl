param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$ReviewedCommit,[Parameter(Mandatory=$true)][string]$ManifestSha256,[Parameter(Mandatory=$true)][string]$ApprovalFile)
$ErrorActionPreference='Stop'
$r='C:\Users\xw436\pavetrack_runs\S01-E029-R001';$logs=$r+'-wrapper-logs';$python='C:\Users\xw436\pavetrack_env\Scripts\python.exe'
$clock=[Diagnostics.Stopwatch]::StartNew();$exitCode=$null;$state='stopped';$reason='not started'
if((Test-Path $r) -or (Test-Path $logs) -or (Test-Path ($r+'-fixed-v1.tar.gz')) -or (Test-Path ($r+'-fixed-v1.tar.gz.part'))){throw 'fresh E029 run/log/package paths required'}
if($env:COMPUTERNAME -ne 'D-26-09' -or (whoami) -ne 'ad\xw436'){throw 'producer identity'}
if(@(Get-Process python* -ErrorAction SilentlyContinue).Count -ne 0){throw 'shared compute conflict'}
$os=Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 2;$load=(Get-CimInstance Win32_Processor -OperationTimeoutSec 2|Measure-Object LoadPercentage -Average).Average
if($os.FreePhysicalMemory -lt 8388608 -or $load -ge 50 -or (Get-PSDrive C).Free -lt 17179869184){throw 'CPU/RAM/disk admission stopped'}
$m=Join-Path $Source 'docs/research/S01/S01-E029/source_manifest.json'
if((Get-FileHash $m -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ManifestSha256){throw 'source manifest identity'}
# Validate every bound source and the exact overlay before the first Python start.
function Assert-Bindings([string]$root,$bindings,[int]$count,[bool]$exact){
 $base=[IO.Path]::GetFullPath($root).TrimEnd('\')+'\';$expected=@()
 $items=@($bindings.PSObject.Properties)
 if($items.Count -ne $count){throw 'binding inventory count'}
 foreach($item in $items){
  if($clock.Elapsed.TotalSeconds -ge 120){throw 'pre-Python validation deadline'}
  $rel=$item.Name
  if($rel -match '(^/|\\|(^|/)\.\.(/|$)|:)'){throw 'unsafe binding path'}
  $path=[IO.Path]::GetFullPath((Join-Path $root $rel))
  if(!$path.StartsWith($base,[StringComparison]::OrdinalIgnoreCase)){throw 'binding escapes root'}
  $leaf=Get-Item -LiteralPath $path;$cursor=$leaf
  while($null -ne $cursor -and $cursor.FullName.Length -ge $base.Length-1){
   if(($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'binding reparse point'}
   if($cursor -is [IO.FileInfo]){$cursor=$cursor.Directory}else{$cursor=$cursor.Parent}
  }
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$item.Value){throw ('binding hash '+$rel)}
  $expected+=@($path)
 }
 if($exact){
  $actual=@(Get-ChildItem -LiteralPath $root -Recurse -Force -File|ForEach-Object {$_.FullName})
  if($actual.Count -ne $expected.Count -or @(Compare-Object $actual $expected).Count -ne 0){throw 'overlay contains unlisted files'}
 }
}
$manifest=Get-Content -Raw -LiteralPath $m|ConvertFrom-Json
Assert-Bindings $Source $manifest.files 252 $false
$runtime=Get-Content -Raw -LiteralPath (Join-Path $Source 'docs/research/S01/S01-E028/runtime_lock.json')|ConvertFrom-Json
Assert-Bindings $runtime.overlay $runtime.files 121 $true
$a=Get-Content -Raw -LiteralPath $ApprovalFile|ConvertFrom-Json
$keys=@('run_id','reviewed_commit','source_manifest_sha256','execute_once','wall_seconds','GPU_uuid')
if(@($a.PSObject.Properties).Count -ne 6 -or @(Compare-Object @($a.PSObject.Properties.Name) $keys -CaseSensitive).Count -ne 0){throw 'exact approval fields required'}
if($a.execute_once -isnot [bool] -or $a.execute_once -ne $true -or ($a.wall_seconds -isnot [int] -and $a.wall_seconds -isnot [long]) -or $a.wall_seconds -ne 3600){throw 'strict approval types'}
foreach($key in @('run_id','reviewed_commit','source_manifest_sha256','GPU_uuid')){if($a.$key -isnot [string]){throw 'strict approval identity type'}}
if($a.run_id -cne 'S01-E029-R001' -or $a.reviewed_commit -cne $ReviewedCommit -or $a.source_manifest_sha256 -cne $ManifestSha256 -or $a.GPU_uuid -cne 'GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7'){throw 'new exact E029 approval required; package is disabled'}
$env:CUDA_VISIBLE_DEVICES='0';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:OPENBLAS_NUM_THREADS='1';$env:PYTHONPATH='C:\Users\xw436\pavetrack_runtime\S01-E028-Pillow-12.3.0-v1';$env:PYTHONDONTWRITEBYTECODE='1';$env:MPLBACKEND='Agg'
New-Item -ItemType Directory $logs|Out-Null
$env:MPLCONFIGDIR=Join-Path $logs 'mplconfig'
# Same retained-Process-handle and owned-tree termination method as E028.
function Invoke-Owned([string]$arguments,[string]$tag,[double]$deadline){
 $p=New-Object Diagnostics.Process;$p.StartInfo.FileName=$python;$p.StartInfo.Arguments=$arguments;$p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true;$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
 $owned=@{};$failure=$null;$uncertain=@();$stdout=$null;$stderr=$null;$started=$false;$code=$null;$rootBirth=$null
 try{
  if($clock.Elapsed.TotalSeconds -ge $deadline){throw 'stage deadline before start'}
  if(!$p.Start()){throw 'Python start failed'};$started=$true;$handle=$p.Handle;$rootBirth=$p.StartTime.ToUniversalTime()
  $stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync()
  # Record root birth immediately so a later CIM/log error cannot orphan it.
  $owned[[int]$p.Id]=@{ProcessId=$p.Id;CreationDate=$p.StartTime.ToUniversalTime();CommandLine=$null;Root=$true}
  @{python_launcher_pid=$p.Id;wrapper_pid=$PID;arguments=$arguments;tag=$tag;started_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\$tag-launch.json" -Encoding UTF8
  do{
   if($clock.Elapsed.TotalSeconds -ge ($deadline-2)){throw 'stage deadline reserves CIM/cleanup'}
   $all=@(Get-CimInstance Win32_Process -OperationTimeoutSec 2);$ids=@($p.Id);$oldCount=0
   while($oldCount -ne $ids.Count){$oldCount=$ids.Count;foreach($v in $all){if(($ids -contains $v.ParentProcessId) -and ($ids -notcontains $v.ProcessId)){$ids+=@($v.ProcessId)}}}
   foreach($v in $all){if($ids -contains $v.ProcessId){$owned[[int]$v.ProcessId]=$v}}
   $rss=($all|Where-Object {$ids -contains $_.ProcessId}|Measure-Object WorkingSetSize -Sum).Sum
   if($clock.Elapsed.TotalSeconds -ge $deadline -or $rss -gt 4294967296){throw 'external wall/RSS first stop'}
  }while(!$p.WaitForExit(100))
  $code=$p.ExitCode
  if($null -eq $code -or $code -ne 0){throw "owned stage $tag stopped, exit=$code"}
 }catch{$failure=$_.Exception.Message}
 finally{
  # Every cleanup/log item is independent and bounded. Preserve the first cause.
  $cleanupEnd=[Math]::Min(3600,[Math]::Min($deadline+20,$clock.Elapsed.TotalSeconds+20))
  $ordered=@();if($started){$ordered=@($p.Id)+@($owned.Keys|Where-Object {$_ -ne $p.Id})}
  foreach($key in $ordered){
   try{
    if($clock.Elapsed.TotalSeconds -ge ($cleanupEnd-6)){throw 'cleanup time bound; inspect remaining owned IDs'}
    $saved=$owned[$key]
    if($key -eq $p.Id -and $started){
     if($p.HasExited){continue}
     if($p.StartTime.ToUniversalTime() -ne $rootBirth){throw 'root birth mismatch'}
    }else{
     $live=Get-CimInstance Win32_Process -Filter "ProcessId=$key" -OperationTimeoutSec 2
     if($null -eq $live){continue}
     if($live.CreationDate -ne $saved.CreationDate -or $live.CommandLine -ne $saved.CommandLine){throw 'owned PID identity changed'}
     if($live.CommandLine -notlike "*$Source*"){throw 'owned descendant command identity uncertain'}
    }
    $kill=New-Object Diagnostics.Process;$kill.StartInfo.FileName='taskkill.exe';$kill.StartInfo.Arguments="/PID $key /T /F";$kill.StartInfo.UseShellExecute=$false;$kill.StartInfo.CreateNoWindow=$true
    if(!$kill.Start()){throw 'taskkill start failed'}
    if(!$kill.WaitForExit(2000)){$kill.Kill();throw 'taskkill timeout'}
    if($kill.ExitCode -ne 0){throw 'taskkill stopped'}
    $live=Get-CimInstance Win32_Process -Filter "ProcessId=$key" -OperationTimeoutSec 2
    if($null -ne $live -and $live.CreationDate -eq $saved.CreationDate){throw 'owned termination not confirmed'}
   }catch{$uncertain+=@(('PID '+$key+': '+$_.Exception.Message))}
  }
  foreach($entry in @(@{task=$stdout;name='stdout'},@{task=$stderr;name='stderr'})){
   try{
    if($null -ne $entry.task){
     $waitMs=[Math]::Min(1000,[Math]::Floor(($cleanupEnd-$clock.Elapsed.TotalSeconds)*1000))
     if($waitMs -le 0 -or !$entry.task.Wait([int]$waitMs)){throw 'log pipe timeout'}
     $entry.task.GetAwaiter().GetResult()|Set-Content (Join-Path $logs ($tag+'-'+$entry.name+'.log')) -Encoding UTF8
    }
   }catch{$uncertain+=@(('log '+$entry.name+': '+$_.Exception.Message))}
  }
  if($uncertain.Count -gt 0){
   try{@{first_cause=$failure;cleanup_uncertain=$uncertain;owned_ids=@($owned.Keys);no_retry=$true}|ConvertTo-Json -Depth 5|Set-Content "$logs\$tag-cleanup-uncertain.json" -Encoding UTF8}catch{[Console]::Error.WriteLine('cleanup record failed: '+$_.Exception.Message)}
   if(!$failure){$failure='cleanup or log completion uncertain'}
  }
 }
 if($failure){throw $failure}
 return $code
}
try{
 Invoke-Owned ('"'+$Source+'\scripts\pavetrack_target_spatial\runtime_preflight.py"') 'preflight' 100|Out-Null
 $producerArgs='"'+$Source+'\scripts\pavetrack_qualified_spatial_selector\run.py" --run "'+$r+'" --paths "'+$Source+'\docs\research\S01\S01-E029\private_paths.template.json" --reviewed-commit '+$ReviewedCommit+' --manifest-sha256 '+$ManifestSha256+' --approval-file "'+$ApprovalFile+'"'
 $exitCode=Invoke-Owned $producerArgs 'producer' 3460;$state='completed';$reason='producer completed, no scientific verdict inferred by wrapper'
}catch{$reason=$_.Exception.Message}
try{@{state=$state;reason=$reason;exit_code=$exitCode;reviewed_commit=$ReviewedCommit;elapsed_seconds=$clock.Elapsed.TotalSeconds;no_retry=$true;finished_at=(Get-Date -Format o)}|ConvertTo-Json|Set-Content "$logs\wrapper_status.json" -Encoding UTF8}catch{[Console]::Error.WriteLine('wrapper status persistence failed: '+$_.Exception.Message)}
# Reserve the final120s inside the same3600s outer wall (last20s reserved for owned cleanup/log) for a success/stop package.
$left=3580-$clock.Elapsed.TotalSeconds
if($left -le 0){throw 'outer deadline: inspect saved stop files; no automatic packaging retry'}
$pack='"'+$Source+'\scripts\pavetrack_qualified_spatial_selector\pack.py" --run "'+$r+'" --logs "'+$logs+'" --manifest "'+$m+'" --output "'+$r+'-fixed-v1.tar.gz" --seconds '+([Math]::Max(1,$left-1))
Invoke-Owned $pack 'package' 3580|Out-Null
if($state -ne 'completed'){throw $reason}
