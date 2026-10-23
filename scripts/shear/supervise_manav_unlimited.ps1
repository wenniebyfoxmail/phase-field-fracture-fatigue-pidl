param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$proc=$null
$owned=@{}
$ownedCPU=@{}
$ownedMeta=@{}
function Find-OwnedChildren {
 $found=$true
 $all=@(Get-CimInstance Win32_Process)
 while($found){
  $found=$false
  foreach($row in $all){
   $childId=[int]$row.ProcessId
   if($owned.ContainsKey([int]$row.ParentProcessId) -and -not $owned.ContainsKey($childId) -and $row.CreationDate.ToUniversalTime() -ge $started){
    # The Windows venv redirector's real interpreter retains this absolute command.
    if(([string]$row.CommandLine).Replace('/','\') -notlike ('*'+$c.root.Replace('/','\')+'*')){continue}
    try{$child=[Diagnostics.Process]::GetProcessById($childId);$held=$child.Handle}catch{continue}
    $child.ProcessorAffinity=[IntPtr]15
    $owned[$childId]=$child
    $ownedMeta[$childId]=@{pid=$childId;parent_pid=[int]$row.ParentProcessId;command=$row.CommandLine;created_utc=$row.CreationDate.ToUniversalTime().ToString('o')}
    $found=$true
   }
  }
 }
 @($ownedMeta.Values)|ConvertTo-Json -Depth 4|Set-Content ($c.root+'/worker_processes.json')
}
function Stop-OwnedProcesses {
 foreach($item in @($owned.Values)|Sort-Object Id -Descending){
  try{if(-not $item.HasExited){$item.Kill();$item.WaitForExit()}}catch{}
 }
}
try {
 if($c.unlimited_compute -ne $true){throw 'Explicit unlimited authorization required'}
 if($env:COMPUTERNAME -ne $c.host){throw 'Wrong producer'}
 if([Security.Principal.WindowsIdentity]::GetCurrent().Name.Split([char]92)[-1] -ne 'xw436'){throw 'Wrong account'}
 if((Get-FileHash ($c.root+'/authority.json')).Hash.ToLower() -ne $c.authority_sha256){throw 'Authority mismatch'}
 if(Test-Path $c.output){throw 'Output exists; inspect instead of retry'}
 if((Get-PSDrive C).Free -lt 15GB){throw 'Insufficient disk headroom'}
 if($c.kind -eq 'fem'){
  if(@(Get-CimInstance Win32_Process -Filter "Name='MATLAB.exe'").Count){throw 'Competing MATLAB'}
  $env:MATLAB_PREFDIR=Join-Path $c.root 'prefs'
  New-Item -ItemType Directory $env:MATLAB_PREFDIR|Out-Null
 }elseif($c.kind -eq 'pidl'){
  if((Get-FileHash ($c.root+'/GPU_RELEASED.json')).Hash.ToLower() -ne $c.reference_sha256){throw 'Reference receipt mismatch'}
  $ref=(Get-Content ($c.root+'/GPU_RELEASED.json') -Raw|ConvertFrom-Json).reference
  if(-not $ref.complete_valid_reference -or $ref.accepted_prefix -ne 24){throw 'Full reference required'}
  $gpu=@(& nvidia-smi --query-gpu=uuid,memory.free,utilization.gpu --format=csv,noheader,nounits)
  if($LASTEXITCODE -ne 0){throw 'GPU query failed'}
  $line=@($gpu|Where-Object {($_ -split ',')[0].Trim() -eq $c.gpu_uuid})
  if($line.Count -ne 1){throw 'GPU UUID missing'}
  $v=$line[0] -split ','
  if([double]$v[1] -lt 24576 -or [double]$v[2] -gt 5){throw 'GPU busy or insufficient headroom'}
  $apps=@(& nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name --format=csv,noheader,nounits)
  if($LASTEXITCODE -ne 0){throw 'GPU process query failed'}
  # WDDM reports ordinary desktop C+G contexts as compute-app entries.
  # Admit only recognized desktop executables at system/application paths;
  # unknown CUDA consumers and any Python process still block admission.
  $desktopNames=@('chatgpt.exe','dwm.exe','explorer.exe','logonui.exe','shellexperiencehost.exe','msedgewebview2.exe','ms-teams.exe','shellhost.exe','crossdeviceresume.exe','startmenuexperiencehost.exe','searchhost.exe','applicationframehost.exe','lockapp.exe','chrome.exe','windowsterminal.exe','systemsettings.exe','codex-computer-use-swift.exe')
  $desktopContexts=@()
  foreach($entry in $apps){
   $parts=$entry -split ',',3
   if($parts.Count -lt 3 -or $parts[0].Trim() -ne $c.gpu_uuid){continue}
   $appPid=[int]$parts[1].Trim();$reportedPath=$parts[2].Trim();$base=[IO.Path]::GetFileName($reportedPath).ToLowerInvariant()
   $live=Get-CimInstance Win32_Process -Filter "ProcessId=$appPid"
   if($null -eq $live){continue}
   $systemPath=$reportedPath -like 'C:\Windows\*' -or $reportedPath -like 'C:\Program Files\*' -or $reportedPath -like 'C:\Program Files (x86)\*' -or $reportedPath -like 'C:\Users\xw436\AppData\Local\OpenAI\Codex\runtimes\*'
   if($base -notin $desktopNames -or -not $systemPath -or $live.Name.ToLowerInvariant() -ne $base){throw ('Unclassified GPU consumer: '+$reportedPath)}
   $desktopContexts+=@{pid=$appPid;path=$reportedPath;classification='existing_desktop_graphics_context'}
  }
  @{utc=[DateTime]::UtcNow.ToString('o');gpu_uuid=$c.gpu_uuid;free_MiB=[double]$v[1];utilization_percent=[double]$v[2];desktop_contexts=$desktopContexts;unclassified_compute_consumers=0}|ConvertTo-Json -Depth 4|Set-Content ($c.root+'/GPU_admission.json')
  if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -like 'python*'}).Count){throw 'Competing Python process'}
  $env:CUDA_VISIBLE_DEVICES=$c.gpu_uuid
  $env:PYTHONPATH=Join-Path $c.root 'deps'
  $env:PYTHONUNBUFFERED='1'
 }else{throw 'Unknown kind'}
 foreach($name in @('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')){[Environment]::SetEnvironmentVariable($name,'4','Process')}
 $env:TEMP=Join-Path $c.root 'tmp';$env:TMP=$env:TEMP
 New-Item -ItemType Directory $env:TEMP|Out-Null
 foreach($name in @('MPLCONFIGDIR','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','TRITON_CACHE_DIR','CUDA_CACHE_PATH')){[Environment]::SetEnvironmentVariable($name,$env:TEMP,'Process')}
 $env:PYTHONDONTWRITEBYTECODE='1'
 $claim=[IO.File]::Open(($c.root+'/launch_claim'),[IO.FileMode]::CreateNew);$claim.Dispose()
 $started=[DateTime]::UtcNow
 $proc=Start-Process -FilePath $c.executable -ArgumentList $c.arguments -WorkingDirectory $c.root -RedirectStandardOutput ($c.root+'/stdout.log') -RedirectStandardError ($c.root+'/stderr.log') -PassThru
 $handle=$proc.Handle
 $proc.ProcessorAffinity=[IntPtr]15

 $owned[$proc.Id]=$proc
 $ownedMeta[$proc.Id]=@{pid=$proc.Id;parent_pid=$PID;command=$c.arguments;created_utc=$started.ToString('o');role='launcher_or_direct_worker'}
 $peakRSS=0;$reason='exited'
 @{pid=$proc.Id;started_utc=$started.ToString('o');host=$env:COMPUTERNAME;kind=$c.kind;executable=$c.executable;arguments=$c.arguments;root=$c.root;output=$c.output;code_commit=$c.commit;deadline_seconds=$null;unlimited_compute=$true;authority_sha256=$c.authority_sha256;output_limit_GiB=10;RSS_limit_GiB=16;threads=4;memory_scope='owned_launcher_and_interpreter_descendants'}|ConvertTo-Json|Set-Content ($c.root+'/launch.json')
 while($true){
  Find-OwnedChildren
  $rss=0L;$active=0
  foreach($item in @($owned.Values)){
   $item.Refresh()
   if(-not $item.HasExited){$rss+=$item.WorkingSet64;$active+=1;try{$ownedCPU[$item.Id]=[Math]::Max([double]$ownedCPU[$item.Id],$item.TotalProcessorTime.TotalSeconds)}catch{}}
  }
  $peakRSS=[Math]::Max($peakRSS,$rss)
  if($rss -gt 16GB){$reason='memory_stopped';Stop-OwnedProcesses;break}
  $bytes=(Get-ChildItem -LiteralPath $c.root -Recurse -File -ErrorAction Stop|Measure-Object Length -Sum).Sum
  if($bytes -gt 10GB){$reason='output_storage_stopped';Stop-OwnedProcesses;break}
  if($active -eq 0){break}
  Start-Sleep -Milliseconds 1000
 }
 $proc.Refresh()
 $cpuFloor=($ownedCPU.Values|Measure-Object -Sum).Sum
 @{pid=$proc.Id;finished_utc=[DateTime]::UtcNow.ToString('o');exit_code=$proc.ExitCode;wall_seconds=([DateTime]::UtcNow-$started).TotalSeconds;cpu_seconds='UNKNOWN';sampled_owned_cpu_lower_bound_seconds=$cpuFloor;peak_RSS_bytes=$peakRSS;cpu_affinity=15;reason=$reason;unlimited_compute=$true;resource_scope='owned_process_tree';completed_marker=(Test-Path ($c.output+'/COMPLETED.txt'))}|ConvertTo-Json|Set-Content ($c.root+'/exit.json')
}catch{
 $failure=$_.Exception.ToString()
 Stop-OwnedProcesses
 if($null -ne $proc -and -not $proc.HasExited){$proc.Kill();$proc.WaitForExit()}
 @{exception=$failure;utc=[DateTime]::UtcNow.ToString('o');child_pid=$(if($null -ne $proc){$proc.Id}else{$null})}|ConvertTo-Json|Set-Content ($c.root+'/supervisor_exception.json')
 throw
}
