param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$c=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$proc=$null
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
  $apps=@(& nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader,nounits|Where-Object {$_ -match $c.gpu_uuid})
  if($LASTEXITCODE -ne 0){throw 'GPU process query failed'}
  if($apps.Count){throw 'Competing GPU process'}
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
 @{pid=$proc.Id;started_utc=$started.ToString('o');host=$env:COMPUTERNAME;kind=$c.kind;executable=$c.executable;arguments=$c.arguments;root=$c.root;output=$c.output;code_commit=$c.commit;deadline_seconds=$null;unlimited_compute=$true;authority_sha256=$c.authority_sha256;output_limit_GiB=10;RSS_limit_GiB=16;threads=4}|ConvertTo-Json|Set-Content ($c.root+'/launch.json')
 $peakRSS=0;$reason='exited'
 while(-not $proc.WaitForExit(1000)){
  $proc.Refresh();$peakRSS=[Math]::Max($peakRSS,$proc.PeakWorkingSet64)
  if($peakRSS -gt 16GB){$reason='memory_stopped';$proc.Kill();$proc.WaitForExit();break}
  $bytes=(Get-ChildItem -LiteralPath $c.root -Recurse -File -ErrorAction Stop|Measure-Object Length -Sum).Sum
  if($bytes -gt 10GB){$reason='output_storage_stopped';$proc.Kill();$proc.WaitForExit();break}
 }
 $proc.Refresh();$peakRSS=[Math]::Max($peakRSS,$proc.PeakWorkingSet64)
 $cpu='UNKNOWN';try{$cpu=$proc.TotalProcessorTime.TotalSeconds}catch{}
 @{pid=$proc.Id;finished_utc=[DateTime]::UtcNow.ToString('o');exit_code=$proc.ExitCode;wall_seconds=([DateTime]::UtcNow-$started).TotalSeconds;cpu_seconds=$cpu;peak_RSS_bytes=$peakRSS;cpu_affinity=15;reason=$reason;unlimited_compute=$true;completed_marker=(Test-Path ($c.output+'/COMPLETED.txt'))}|ConvertTo-Json|Set-Content ($c.root+'/exit.json')
}catch{
 $failure=$_.Exception.ToString()
 if($null -ne $proc -and -not $proc.HasExited){$proc.Kill();$proc.WaitForExit()}
 @{exception=$failure;utc=[DateTime]::UtcNow.ToString('o');child_pid=$(if($null -ne $proc){$proc.Id}else{$null})}|ConvertTo-Json|Set-Content ($c.root+'/supervisor_exception.json')
 throw
}
