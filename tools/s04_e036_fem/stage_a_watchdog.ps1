# Run through stage_a_launcher.ps1. Receipts, not this source, prove execution.
param([Parameter(Mandatory=$true)][string]$Root,
      [Parameter(Mandatory=$true)][string]$Label,
      [Parameter(Mandatory=$true)][string]$Entry,
      [Parameter(Mandatory=$true)][string]$AuthorityFile,
      [Parameter(Mandatory=$true)][string]$AuthoritySha256,
      [ValidateSet('Matlab','Python')][string]$Kind='Matlab',
      [string]$PythonExecutable='', [string]$ArgumentsFile='',
      [switch]$RequireArms)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$stopwatch=[Diagnostics.Stopwatch]::StartNew()
if ([IntPtr]::Size -ne 8) {throw 'The Stage A watchdog requires 64-bit PowerShell'}
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\');$Entry=[IO.Path]::GetFullPath($Entry)
if ($Label -notmatch '^[a-z0-9_]+$') {throw 'Invalid Stage A label'}
function In-Task([string]$path) {return [IO.Path]::GetFullPath($path).StartsWith($Root+'\',[StringComparison]::OrdinalIgnoreCase)}
if (-not (In-Task $Entry) -or -not (Test-Path -LiteralPath $Entry -PathType Leaf)) {throw 'Task-owned entry required'}
$logs=Join-Path $Root 'logs';$job=Join-Path $logs $Label;$armDirectory=$job+'_arms'
if (-not (Test-Path -LiteralPath $logs -PathType Container)) {throw 'Existing task logs required'}
foreach ($suffix in @('_attempt.json','_started.json','_finished.json')) {if (Test-Path -LiteralPath ($job+$suffix)) {throw 'Attempt exists; never relaunch'}}
if (Test-Path -LiteralPath $armDirectory) {throw 'Arm deadline directory already exists'}
function File-Hash([string]$path) {return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Write-NewJson([string]$path,$value) {
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 12))
 $temp=$path+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
 $file=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try {$file.Write($bytes,0,$bytes.Length);$file.Flush($true)} finally {$file.Dispose()}
 [IO.File]::Move($temp,$path) # New name, never replace an existing receipt.
}
function Read-Utc([string]$text) {
 if ($text -notmatch 'Z$') {throw 'Explicit UTC timestamp required'}
 return [DateTime]::Parse($text,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
function Positive-Number($value) {
 return (($value -is [int] -or $value -is [long] -or $value -is [double] -or $value -is [decimal]) -and [double]$value -gt 0 -and -not [double]::IsInfinity([double]$value) -and -not [double]::IsNaN([double]$value))
}
$AuthorityFile=[IO.Path]::GetFullPath($AuthorityFile)
if (-not (In-Task $AuthorityFile) -or $AuthoritySha256 -cnotmatch '^[a-f0-9]{64}$' -or (File-Hash $AuthorityFile) -cne $AuthoritySha256) {throw 'Authority path/hash differs'}
$authority=Get-Content -LiteralPath $AuthorityFile -Raw|ConvertFrom-Json
foreach ($field in @('schema','authority_id','stage','run_root','producer_hostname','allowed_labels','authorized_at_utc','human_authorization_ref','max_compute_threads','global_deadline_utc','per_job_wall_seconds','arm_wall_seconds')) {if ($authority.PSObject.Properties.Name -notcontains $field) {throw ('Missing authority field: '+$field)}}
if ($authority.schema -cne 'e036-stage-a-authority-v1' -or $authority.stage -cne 'A' -or [IO.Path]::GetFullPath([string]$authority.run_root).TrimEnd('\') -ine $Root -or $authority.producer_hostname -ine $env:COMPUTERNAME -or @($authority.allowed_labels) -cnotcontains $Label -or -not $authority.authority_id -or -not $authority.human_authorization_ref) {throw 'Authority identity/scope differs'}
if (-not (Positive-Number $authority.per_job_wall_seconds) -or -not (Positive-Number $authority.max_compute_threads) -or $authority.max_compute_threads -gt 4 -or [Math]::Floor([double]$authority.max_compute_threads) -ne $authority.max_compute_threads) {throw 'Explicit per-job timeout and integer thread cap 1..4 required'}
if ((Read-Utc $authority.authorized_at_utc) -gt [DateTime]::UtcNow.AddMinutes(1)) {throw 'Authority timestamp is in the future'}
$WallSeconds=[double]$authority.per_job_wall_seconds;$maxThreads=[int]$authority.max_compute_threads
$deadline=$null
if ($null -ne $authority.global_deadline_utc) {$deadline=Read-Utc $authority.global_deadline_utc;if ([DateTime]::UtcNow -ge $deadline) {throw 'Explicit global deadline elapsed'}}
$armWall=$null
if ($RequireArms) {if (-not (Positive-Number $authority.arm_wall_seconds)) {throw 'Native arms require an explicit positive timeout'};$armWall=[double]$authority.arm_wall_seconds}
# A fresh Windows Job Object contains only our suspended child and its future
# descendants. Handles avoid PID reuse. Closing the watchdog closes the Job
# Object and kills that tree, including compiler subprocesses after failures.
# CWD is bound by CreateProcess(lpCurrentDirectory), not a claimed live-CWD read.
Add-Type -TypeDefinition @'
using System;using System.Text;using System.IO;using System.Runtime.InteropServices;using System.ComponentModel;
public sealed class E036OwnedJob : IDisposable {
 [StructLayout(LayoutKind.Sequential)] struct SA {public int size;public IntPtr descriptor;public int inherit;}
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct SI {
  public int cb;public string reserved,desktop,title;public int x,y,xs,ys,xc,yc,fill,flags;
  public short show,reserved2;public IntPtr reservedPtr,input,output,error;
 }
 [StructLayout(LayoutKind.Sequential)] struct PI {public IntPtr process,thread;public uint pid,tid;}
 [StructLayout(LayoutKind.Sequential)] struct BASIC {public long perProcess,perJob;public uint flags;public UIntPtr minWorking,maxWorking;public uint activeProcesses;public UIntPtr affinity;public uint priority,scheduling;}
 [StructLayout(LayoutKind.Sequential)] struct IO {public ulong a,b,c,d,e,f;}
 [StructLayout(LayoutKind.Sequential)] struct EXT {public BASIC basic;public IO io;public UIntPtr processMemory,jobMemory,peakProcess,peakJob;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref SI si,out PI pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateFile(string name,uint access,uint share,ref SA sa,uint mode,uint flags,IntPtr template);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attr,string name);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int kind,ref EXT info,int size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
 [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetProcessTimes(IntPtr process,out long creation,out long exit,out long kernel,out long user);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder text,ref int size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetProcessAffinityMask(IntPtr process,out UIntPtr allowed,out UIntPtr system);
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 IntPtr process=IntPtr.Zero,thread=IntPtr.Zero,job=IntPtr.Zero,stdout=IntPtr.Zero,stderr=IntPtr.Zero,stdin=IntPtr.Zero;
 long creation;bool assigned=false;
 public uint Id {get;private set;} public string Image {get;private set;} public ulong AffinityMask {get;private set;}
 public DateTime CreatedUtc {get{return DateTime.FromFileTimeUtc(creation);}}
 static void Check(bool ok) {if(!ok)throw new Win32Exception(Marshal.GetLastWin32Error());}
 static string ImageOf(IntPtr h) {var s=new StringBuilder(32768);int n=s.Capacity;Check(QueryFullProcessImageName(h,0,s,ref n));return s.ToString();}
 static long CreationOf(IntPtr h) {long c,e,k,u;Check(GetProcessTimes(h,out c,out e,out k,out u));return c;}
 public static string Quote(string text) {
  var b=new StringBuilder("\"");int slash=0;
  foreach(char c in text){if(c=='\\'){slash++;continue;}if(c=='"'){b.Append('\\',2*slash+1);b.Append('"');}else{b.Append('\\',slash);b.Append(c);}slash=0;}
  b.Append('\\',2*slash);b.Append('"');return b.ToString();
 }
 public E036OwnedJob(string executable,string command,string cwd,string output,string error,int maxCores) {
  Image=Path.GetFullPath(executable);
  try {
   job=CreateJobObject(IntPtr.Zero,null);Check(job!=IntPtr.Zero);
   UIntPtr allowed,system;Check(GetProcessAffinityMask(GetCurrentProcess(),out allowed,out system));
   ulong bits=allowed.ToUInt64(),mask=0;int count=0;
   for(int i=0;i<64 && count<maxCores;i++)if((bits&(1UL<<i))!=0){mask|=1UL<<i;count++;}
   Check(count>0);AffinityMask=mask;
   var limits=new EXT();limits.basic.flags=0x2000|0x10;limits.basic.affinity=new UIntPtr(mask);
   Check(SetInformationJobObject(job,9,ref limits,Marshal.SizeOf(typeof(EXT))));
   var sa=new SA();sa.size=Marshal.SizeOf(typeof(SA));sa.inherit=1;
   stdout=CreateFile(output,0x40000000,1,ref sa,1,0x80,IntPtr.Zero);Check(stdout!=new IntPtr(-1));
   stderr=CreateFile(error,0x40000000,1,ref sa,1,0x80,IntPtr.Zero);Check(stderr!=new IntPtr(-1));
   stdin=CreateFile("NUL",0x80000000,3,ref sa,3,0x80,IntPtr.Zero);Check(stdin!=new IntPtr(-1));
   var si=new SI();si.cb=Marshal.SizeOf(typeof(SI));si.flags=0x100;si.input=stdin;si.output=stdout;si.error=stderr;
   PI pi;Check(CreateProcess(Image,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,true,0x4|0x08000000,IntPtr.Zero,Path.GetFullPath(cwd),ref si,out pi));
   process=pi.process;thread=pi.thread;Id=pi.pid;creation=CreationOf(process);
   Check(String.Equals(ImageOf(process),Image,StringComparison.OrdinalIgnoreCase));
   Check(AssignProcessToJobObject(job,process));assigned=true;
  }catch{Dispose();throw;}
 }
 public void VerifyIdentity(){if(process==IntPtr.Zero || creation!=CreationOf(process) || !String.Equals(ImageOf(process),Image,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Owned handle identity changed");}
 public void Resume(){VerifyIdentity();Check(ResumeThread(thread)!=0xffffffff);CloseHandle(thread);thread=IntPtr.Zero;}
 public bool Wait(int ms){uint r=WaitForSingleObject(process,(uint)ms);if(r==0)return true;if(r==258)return false;throw new Win32Exception(Marshal.GetLastWin32Error());}
 public uint ExitCode {get{uint code;Check(GetExitCodeProcess(process,out code));return code;}}
 public void Stop(){VerifyIdentity();Check(TerminateJobObject(job,124));Wait(10000);}
 public void Dispose(){
  if(process!=IntPtr.Zero && !assigned)TerminateProcess(process,125); // Our still-suspended handle only.
  if(job!=IntPtr.Zero){CloseHandle(job);job=IntPtr.Zero;}
  if(process!=IntPtr.Zero){WaitForSingleObject(process,10000);CloseHandle(process);process=IntPtr.Zero;}
  if(thread!=IntPtr.Zero){CloseHandle(thread);thread=IntPtr.Zero;}
  foreach(var h in new[]{stdin,stdout,stderr})if(h!=IntPtr.Zero && h!=new IntPtr(-1))CloseHandle(h);
  stdin=stdout=stderr=IntPtr.Zero;
 }
}
'@
$threads=1;$argumentsHash=$null
if ($Kind -eq 'Matlab') {
 if ([IO.Path]::GetExtension($Entry) -ine '.m') {throw 'MATLAB entry must be an m file'}
 if (@(Get-Process MATLAB -ErrorAction SilentlyContinue).Count -gt 0) {throw 'Another MATLAB process exists; no concurrent solver'}
 $executable='C:\Program Files\MATLAB\R2025b\bin\win64\MATLAB.exe'
 $entryMatlab=$Entry.Replace('\','/').Replace("'","''")
 $childArgs=@('-singleCompThread','-batch',("run('"+$entryMatlab+"')"),'-logfile',($job+'_matlab.log'))
} else {
 if ($RequireArms -or [IO.Path]::GetFileName($Entry) -ine 'compare_frozen_states.py') {throw 'Only the frozen Python comparator is admitted'}
 if (-not $PythonExecutable -or -not $ArgumentsFile) {throw 'Explicit Python executable and task argv JSON required'}
 $executable=[IO.Path]::GetFullPath($PythonExecutable);$ArgumentsFile=[IO.Path]::GetFullPath($ArgumentsFile)
 if ([IO.Path]::GetFileName($executable) -ine 'python.exe' -or -not (In-Task $ArgumentsFile)) {throw 'Invalid Python identity/argv path'}
 $values=@(Get-Content -LiteralPath $ArgumentsFile -Raw|ConvertFrom-Json)
 $allowed=@('--input','--input-sha256','--common-problem','--common-problem-sha256','--output','--threads');$seen=@{}
 if ($values.Count%2 -ne 0) {throw 'Comparator argv requires flag/value pairs'}
 for ($i=0;$i -lt $values.Count;$i+=2) {
  $flag=$values[$i];$value=$values[$i+1]
  if ($flag -isnot [string] -or $value -isnot [string] -or $flag -notin $allowed -or $seen.ContainsKey($flag)) {throw 'Invalid/duplicate comparator option'}
  $seen[$flag]=$value
 }
 foreach ($flag in $allowed[0..4]) {if (-not $seen.ContainsKey($flag)) {throw 'Missing comparator argument'}}
 foreach ($flag in @('--input','--common-problem','--output')) {if (-not (In-Task $seen[$flag])) {throw 'Comparator paths must be task-local'}}
 foreach ($flag in @('--input-sha256','--common-problem-sha256')) {if ($seen[$flag] -cnotmatch '^[a-f0-9]{64}$') {throw 'SHA256 required'}}
 if ($seen.ContainsKey('--threads')) {if ($seen['--threads'] -notmatch '^[1-4]$' -or [int]$seen['--threads'] -gt $maxThreads) {throw 'Thread limit exceeded'};$threads=[int]$seen['--threads']} else {$values+=@('--threads','1')}
 $argumentsHash=File-Hash $ArgumentsFile;$childArgs=@('-u',$Entry)+$values
}
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {throw 'Executable is unavailable'}
foreach ($name in @('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')) {[Environment]::SetEnvironmentVariable($name,[string]$threads,'Process')}
$env:CUDA_VISIBLE_DEVICES='';$env:MPLBACKEND='Agg'
$command=([E036OwnedJob]::Quote($executable))+' '+(($childArgs|ForEach-Object {[E036OwnedJob]::Quote([string]$_)}) -join ' ')
$started=[DateTime]::UtcNow;if ($null -ne $deadline -and $started -ge $deadline) {throw 'Explicit global deadline elapsed'}
$process=$null;$lock=$null;$reason='not_started';$wrapperFailure=$null;$exitCode=$null;$attemptOwned=$false;$armHashes=@{}
function Check-ArmDeadlines([bool]$Final) {
 if (-not (Test-Path -LiteralPath $armDirectory)) {if ($Final -and $RequireArms) {throw 'Required arm receipts missing'};return}
 if ($Kind -ne 'Matlab' -or -not $RequireArms) {throw 'Unexpected native arm receipts'}
 $now=[DateTime]::UtcNow;$previousFinished=$null
 foreach ($mode in @('absent','false')) {
  $begin=Join-Path $armDirectory ($mode+'_started.json');$end=Join-Path $armDirectory ($mode+'_finished.json')
  if (-not (Test-Path -LiteralPath $begin)) {if ($Final -or (Test-Path -LiteralPath $end)) {throw ('Incomplete arm: '+$mode)};continue}
  foreach ($path in @($begin,$end)) {
   if (-not (Test-Path -LiteralPath $path)) {continue};$hash=File-Hash $path
   if ($armHashes.ContainsKey($path) -and $armHashes[$path] -cne $hash) {throw 'Immutable arm receipt changed'};$armHashes[$path]=$hash
  }
  $arm=Get-Content -LiteralPath $begin -Raw|ConvertFrom-Json
  if ($arm.schema -cne 'e036-stage-a-arm-v1' -or $arm.watchdog_id -cne $Label -or $arm.mode -cne $mode -or $arm.matlab_pid -ne $process.Id -or $arm.wall_seconds -ne $armWall -or $arm.authority_id -cne $authority.authority_id -or $arm.authority_sha256 -cne $AuthoritySha256) {throw 'Arm identity differs'}
  $beginTime=Read-Utc $arm.arm_started_utc;$armEnd=Read-Utc $arm.deadline_utc
  if ([Math]::Abs(($armEnd-$beginTime).TotalSeconds-$armWall) -gt .001 -or $beginTime -lt $started.AddSeconds(-1) -or $beginTime -gt $now.AddSeconds(1)) {throw 'Invalid arm time window'}
  if ($mode -eq 'false' -and ($null -eq $previousFinished -or $beginTime -lt $previousFinished)) {throw 'Second arm precedes first verified completion'}
  if (Test-Path -LiteralPath $end) {
   $done=Get-Content -LiteralPath $end -Raw|ConvertFrom-Json
   if ($done.schema -cne $arm.schema -or $done.watchdog_id -cne $Label -or $done.mode -cne $mode -or $done.matlab_pid -ne $process.Id -or $done.authority_id -cne $authority.authority_id -or $done.authority_sha256 -cne $AuthoritySha256) {throw 'Arm completion identity differs'}
   $finished=Read-Utc $done.arm_finished_utc
   if ($finished -lt $beginTime -or $finished -gt $armEnd -or $finished -gt $now.AddSeconds(1)) {throw ('Arm deadline exceeded: '+$mode)}
   if ($mode -eq 'absent') {$previousFinished=$finished}
  } elseif ($Final -or $now -ge $armEnd) {throw ('Arm incomplete or timed out: '+$mode)}
 }
}
try {
 $lock=[IO.File]::Open((Join-Path $logs 'stage_a_active.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $attempt=[ordered]@{schema='e036-stage-a-watchdog-v3';label=$Label;kind=$Kind;entry=$Entry;entry_sha256=(File-Hash $Entry);argv_file=$ArgumentsFile;argv_sha256=$argumentsHash;executable=$executable;command=$command;launch_cwd=$Root;created_utc=$started.ToString('o');global_deadline_utc=$authority.global_deadline_utc;wall_seconds=$WallSeconds;max_compute_threads=$threads;affinity_cpu_cap=$maxThreads;parent_wrapper_pid=$PID;authority_id=$authority.authority_id;authority_file=$AuthorityFile;authority_sha256=$AuthoritySha256;effective_execution_policy=[string](Get-ExecutionPolicy)}
 Write-NewJson ($job+'_attempt.json') $attempt;$attemptOwned=$true
 $process=[E036OwnedJob]::new($executable,$command,$Root,($job+'_stdout.log'),($job+'_stderr.log'),$maxThreads)
 $identity=Get-CimInstance Win32_Process -Filter ('ProcessId='+$process.Id)
 if (-not $identity -or $identity.CommandLine -cne $command -or $identity.ExecutablePath -ine $executable -or [Math]::Abs(($identity.CreationDate.ToUniversalTime()-$process.CreatedUtc).TotalSeconds) -gt 1) {throw 'Suspended process identity differs'}
 $record=[ordered]@{label=$Label;pid=$process.Id;entry=$Entry;command=$identity.CommandLine;creation_utc=$process.CreatedUtc.ToString('o');launch_cwd=$Root;cwd_binding='CreateProcess lpCurrentDirectory; not a live CWD read';max_compute_threads=$threads;affinity_mask=$process.AffinityMask;arm_deadline_dir=$armDirectory;require_arms=[bool]$RequireArms;job_object='fresh kill-on-close, descendants included';state='suspended_identity_verified'}
 Write-NewJson ($job+'_started.json') $record
 if ((File-Hash $Entry) -cne $attempt.entry_sha256 -or (File-Hash $AuthorityFile) -cne $AuthoritySha256 -or ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline) -or $stopwatch.Elapsed.TotalSeconds -ge $WallSeconds) {throw 'Entry/authority changed or timeout elapsed before resume'}
 if ($Kind -eq 'Python' -and (File-Hash $ArgumentsFile) -cne $argumentsHash) {throw 'Comparator argv changed'}
 $process.Resume();$reason='exited';$lastStorage=-10
 while (-not $process.Wait(500)) {
  Check-ArmDeadlines $false
  if ($stopwatch.Elapsed.TotalSeconds -ge $WallSeconds) {$reason='per_job_wall_limit';break}
  if ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline) {$reason='explicit_global_wall_limit';break}
  if ($stopwatch.Elapsed.TotalSeconds-$lastStorage -ge 10) {
   $lastStorage=$stopwatch.Elapsed.TotalSeconds;$used=(Get-ChildItem -LiteralPath $Root -Recurse -File | Measure-Object Length -Sum).Sum
   if ($used -gt 5GB) {$reason='task_storage_limit';break}
   if ((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace -lt 10GB) {$reason='free_space_limit';break}
  }
 }
 if ($reason -ne 'exited') {$process.Stop()};$exitCode=$process.ExitCode
 Check-ArmDeadlines $true
 if ($reason -eq 'exited' -and ($stopwatch.Elapsed.TotalSeconds -ge $WallSeconds -or ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline))) {$reason='deadline_at_exit'}
} catch {
 $wrapperFailure=$_.Exception.ToString();$reason='watchdog_or_arm_failure'
 if ($null -ne $process) {try {if (-not $process.Wait(0)) {$process.Stop()};$exitCode=$process.ExitCode} catch {$wrapperFailure+='; cleanup: '+$_.Exception.ToString()}}
} finally {
 # Unconditional own-Job cleanup also covers identity/receipt/IO exceptions.
 if ($null -ne $process) {$process.Dispose()};if ($null -ne $lock) {$lock.Dispose()}
}
if ($attemptOwned) {Write-NewJson ($job+'_finished.json') ([ordered]@{label=$Label;exit_code=$exitCode;stop_reason=$reason;wrapper_error=$wrapperFailure;elapsed_seconds=$stopwatch.Elapsed.TotalSeconds;ended_utc=[DateTime]::UtcNow.ToString('o');arm_receipt_hashes=$armHashes;job_object_closed=$true;authority_id=$authority.authority_id;authority_sha256=$AuthoritySha256})}
if ($wrapperFailure -or $reason -ne 'exited' -or $exitCode -ne 0) {throw ('Stage A job did not complete within authority: '+$reason+'; exit='+$exitCode+'; '+$wrapperFailure)}
