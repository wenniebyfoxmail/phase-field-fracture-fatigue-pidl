# Caller must capture this process's stdout/stderr before -File parsing.
# This supervisor blocks until the watchdog exits. No Set-ExecutionPolicy is used.
param([Parameter(Mandatory=$true)][string]$Root,
      [Parameter(Mandatory=$true)][string]$Label,
      [Parameter(Mandatory=$true)][string]$Entry,
      [Parameter(Mandatory=$true)][string]$AuthorityFile,
      [Parameter(Mandatory=$true)][string]$AuthoritySha256,
      [Parameter(Mandatory=$true)][string]$WatchdogFile,
      [Parameter(Mandatory=$true)][string]$WatchdogSha256,
      [ValidateSet('Matlab','Python')][string]$Kind='Matlab',
      [string]$PythonExecutable='', [string]$ArgumentsFile='',
      [switch]$RequireArms)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$clock=[Diagnostics.Stopwatch]::StartNew()
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\')
if ($Label -notmatch '^[a-z0-9_]+$') {throw 'Invalid attempt label'}
$logs=Join-Path $Root 'logs';$prefix=Join-Path $logs $Label
if (-not (Test-Path -LiteralPath $logs -PathType Container)) {throw 'Existing task log directory required'}
function Write-NewJson([string]$path,$value) {
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 12))
 $temp=$path+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
 $stream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)} finally {$stream.Dispose()}
 [IO.File]::Move($temp,$path)
}
function In-Task([string]$path) {return [IO.Path]::GetFullPath($path).StartsWith($Root+'\',[StringComparison]::OrdinalIgnoreCase)}
function File-Hash([string]$path) {return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read-Utc([string]$value) {
 if ($value -notmatch 'Z$') {throw 'Explicit UTC timestamp required'}
 return [DateTime]::Parse($value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
function Positive-Number($value) {
 return (($value -is [int] -or $value -is [long] -or $value -is [double] -or $value -is [decimal]) -and [double]$value -gt 0 -and -not [double]::IsInfinity([double]$value) -and -not [double]::IsNaN([double]$value))
}
function Global-Policies {
 $result=[ordered]@{}
 foreach ($scope in @('MachinePolicy','UserPolicy','CurrentUser','LocalMachine')) {$result[$scope]=[string](Get-ExecutionPolicy -Scope $scope)}
 return $result
}
function Quote-Argument([string]$value) {
 if ($value.Contains('"') -or $value.EndsWith('\') -or $value.Contains([char]0) -or $value.Contains([char]13) -or $value.Contains([char]10)) {throw 'Unsafe process argument'}
 return '"'+$value+'"'
}
foreach ($suffix in @('_supervisor_attempt.json','_supervisor_started.json','_supervisor_finished.json','_watchdog_stdout.log','_watchdog_stderr.log','_attempt.json','_started.json','_finished.json')) {
 if (Test-Path -LiteralPath ($prefix+$suffix)) {throw 'Attempt exists; do not retry this label'}
}
# Consume the label before authority loading, child Add-Type, or process start.
Write-NewJson ($prefix+'_supervisor_attempt.json') ([ordered]@{
 schema='e036-stage-a-supervisor-v1';label=$Label;supervisor_pid=$PID;
 created_utc=[DateTime]::UtcNow.ToString('o');root=$Root;entry=$Entry;kind=$Kind;
 authority_file=$AuthorityFile;authority_sha256=$AuthoritySha256;
 watchdog_file=$WatchdogFile;watchdog_sha256=$WatchdogSha256
})
$child=$null;$childStarted=$false;$heldHandle=$null;$childCreated=$null
$stdout=$null;$stderr=$null;$stdoutCopy=$null;$stderrCopy=$null
$failure=$null;$reason='preflight';$exitCode=$null;$policiesBefore=$null;$policiesAfter=$null
$policyUnchanged=$false;$authority=$null;$deadline=$null;$childStopped=$false
try {
 if ([IntPtr]::Size -ne 8) {throw '64-bit supervisor required'}
 $policiesBefore=Global-Policies
 $AuthorityFile=[IO.Path]::GetFullPath($AuthorityFile);$WatchdogFile=[IO.Path]::GetFullPath($WatchdogFile);$Entry=[IO.Path]::GetFullPath($Entry)
 foreach ($path in @($AuthorityFile,$WatchdogFile,$Entry)) {if (-not (In-Task $path) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {throw 'Task-owned existing file required'}}
 if ($AuthoritySha256 -cnotmatch '^[a-f0-9]{64}$' -or $WatchdogSha256 -cnotmatch '^[a-f0-9]{64}$' -or (File-Hash $AuthorityFile) -cne $AuthoritySha256 -or (File-Hash $WatchdogFile) -cne $WatchdogSha256) {throw 'Authority/watchdog hash differs'}
 $authority=Get-Content -LiteralPath $AuthorityFile -Raw|ConvertFrom-Json
 foreach ($field in @('schema','authority_id','stage','run_root','producer_hostname','allowed_labels','authorized_at_utc','human_authorization_ref','max_compute_threads','global_deadline_utc','per_job_wall_seconds','arm_wall_seconds')) {if ($authority.PSObject.Properties.Name -notcontains $field) {throw ('Missing authority field: '+$field)}}
 if ($authority.schema -cne 'e036-stage-a-authority-v1' -or $authority.stage -cne 'A' -or [IO.Path]::GetFullPath([string]$authority.run_root).TrimEnd('\') -ine $Root -or $authority.producer_hostname -ine $env:COMPUTERNAME -or @($authority.allowed_labels) -cnotcontains $Label -or -not $authority.authority_id -or -not $authority.human_authorization_ref) {throw 'Authority identity/scope differs'}
 if (-not (Positive-Number $authority.per_job_wall_seconds) -or -not (Positive-Number $authority.max_compute_threads) -or $authority.max_compute_threads -gt 4 -or [Math]::Floor([double]$authority.max_compute_threads) -ne $authority.max_compute_threads) {throw 'Explicit per-job timeout and integer thread cap 1..4 required'}
 if ((Read-Utc $authority.authorized_at_utc) -gt [DateTime]::UtcNow.AddMinutes(1)) {throw 'Authority timestamp is in the future'}
 if ($RequireArms -and -not (Positive-Number $authority.arm_wall_seconds)) {throw 'Native arms require an explicit timeout'}
 if ($null -ne $authority.global_deadline_utc) {$deadline=Read-Utc $authority.global_deadline_utc}
 if (($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline) -or $clock.Elapsed.TotalSeconds -ge $authority.per_job_wall_seconds) {throw 'Explicit timeout reached before start'}
 $executable=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {throw 'Full x64 Windows PowerShell path unavailable'}
 $arguments=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$WatchdogFile,'-Root',$Root,'-Label',$Label,'-Entry',$Entry,'-AuthorityFile',$AuthorityFile,'-AuthoritySha256',$AuthoritySha256,'-Kind',$Kind)
 if ($Kind -eq 'Python') {$arguments+=@('-PythonExecutable',$PythonExecutable,'-ArgumentsFile',$ArgumentsFile)}
 if ($RequireArms) {$arguments+=@('-RequireArms')}
 $argumentLine=($arguments|ForEach-Object {Quote-Argument ([string]$_)}) -join ' '
 $stdout=[IO.File]::Open(($prefix+'_watchdog_stdout.log'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 $stderr=[IO.File]::Open(($prefix+'_watchdog_stderr.log'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 $info=[Diagnostics.ProcessStartInfo]::new()
 $info.FileName=$executable;$info.Arguments=$argumentLine;$info.WorkingDirectory=$Root
 $info.UseShellExecute=$false;$info.CreateNoWindow=$true
 $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true;$info.RedirectStandardInput=$true
 $child=[Diagnostics.Process]::new();$child.StartInfo=$info
 if ((File-Hash $AuthorityFile) -cne $AuthoritySha256 -or (File-Hash $WatchdogFile) -cne $WatchdogSha256) {throw 'Launch inputs changed'}
 if (-not $child.Start()) {throw 'Watchdog process creation returned false'}
 $childStarted=$true;$heldHandle=$child.Handle;$childCreated=$child.StartTime.ToUniversalTime()
 $child.StandardInput.Close()
 # Drain both OS pipes concurrently in .NET; no PowerShell callback/runspace.
 $stdoutCopy=$child.StandardOutput.BaseStream.CopyToAsync($stdout)
 $stderrCopy=$child.StandardError.BaseStream.CopyToAsync($stderr)
 $identity=Get-CimInstance Win32_Process -Filter ('ProcessId='+$child.Id)
 if (-not $identity -or $identity.ExecutablePath -ine $executable -or [Math]::Abs(($identity.CreationDate.ToUniversalTime()-$childCreated).TotalSeconds) -gt 1) {throw 'Owned watchdog process identity differs'}
 Write-NewJson ($prefix+'_supervisor_started.json') ([ordered]@{
  label=$Label;supervisor_pid=$PID;watchdog_pid=$child.Id;watchdog_created_utc=$childCreated.ToString('o');
  executable=$executable;arguments=$argumentLine;observed_command=$identity.CommandLine;
  launch_cwd=$Root;cwd_binding='ProcessStartInfo.WorkingDirectory; not a live CWD read';
  authority_id=$authority.authority_id;authority_sha256=$AuthoritySha256;
  per_job_wall_seconds=$authority.per_job_wall_seconds;global_deadline_utc=$authority.global_deadline_utc;
  global_policies_before=$policiesBefore;effective_supervisor_policy=[string](Get-ExecutionPolicy);
  watchdog_policy='Bypass in child process only';watchdog_sha256=$WatchdogSha256
 })
 $reason='watchdog_running'
 while (-not $child.WaitForExit(500)) {
  if ($stdoutCopy.IsFaulted -or $stderrCopy.IsFaulted) {throw 'Watchdog output capture failed'}
  if ($clock.Elapsed.TotalSeconds -ge $authority.per_job_wall_seconds) {throw 'Per-job supervisor timeout reached'}
  if ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline) {throw 'Explicit global timeout reached'}
 }
 $exitCode=$child.ExitCode;$reason='watchdog_exited'
 if (-not $stdoutCopy.Wait(10000) -or -not $stderrCopy.Wait(10000)) {throw 'Watchdog pipe drain timed out'}
 $stdout.Flush($true);$stderr.Flush($true)
 if ($exitCode -ne 0) {throw ('Watchdog exited with code '+$exitCode)}
 $donePath=$prefix+'_finished.json'
 if (-not (Test-Path -LiteralPath $donePath -PathType Leaf)) {throw 'Watchdog exited without a completion receipt'}
 $done=Get-Content -LiteralPath $donePath -Raw|ConvertFrom-Json
 if ($done.label -cne $Label -or $done.exit_code -ne 0 -or $done.stop_reason -cne 'exited' -or $done.job_object_closed -ne $true -or $done.wrapper_error -or $done.authority_id -cne $authority.authority_id -or $done.authority_sha256 -cne $AuthoritySha256) {throw 'Watchdog completion does not prove success'}
 if ($clock.Elapsed.TotalSeconds -ge $authority.per_job_wall_seconds -or ($null -ne $deadline -and [DateTime]::UtcNow -ge $deadline)) {throw 'Supervisor timeout reached at exit'}
 if ((File-Hash $AuthorityFile) -cne $AuthoritySha256 -or (File-Hash $WatchdogFile) -cne $WatchdogSha256) {throw 'Launch inputs changed during job'}
 $reason='completed'
} catch {
 $failure=$_.Exception.ToString();$reason='supervisor_or_watchdog_failure'
} finally {
 # Retained process handle prevents PID reuse; never select/kill by a process name.
 if ($childStarted) {
  try {
   if (-not $child.HasExited) {
    if ($null -ne $childCreated -and $child.StartTime.ToUniversalTime() -ne $childCreated) {throw 'Owned process creation time changed'}
    $child.Kill() # Watchdog exit closes its kill-on-close Job Object.
    if (-not $child.WaitForExit(10000)) {throw 'Owned watchdog did not exit after termination'}
   }
   $exitCode=$child.ExitCode;$childStopped=$true
  } catch {$failure=([string]$failure)+'; cleanup: '+$_.Exception.ToString();$reason='cleanup_failed'}
 }
 foreach ($copy in @($stdoutCopy,$stderrCopy)) {
  if ($null -ne $copy) {try {if (-not $copy.Wait(10000)) {throw 'Pipe drain incomplete'}} catch {$failure=([string]$failure)+'; capture: '+$_.Exception.ToString();$reason='capture_failed'}}
 }
 foreach ($stream in @($stdout,$stderr)) {
  if ($null -ne $stream) {
   try {$stream.Flush($true)} catch {$failure=([string]$failure)+'; stream flush: '+$_.Exception.ToString();$reason='capture_failed'}
   try {$stream.Dispose()} catch {$failure=([string]$failure)+'; stream close: '+$_.Exception.ToString();$reason='capture_failed'}
  }
 }
 if ($null -ne $child) {$child.Dispose()}
 try {
  $policiesAfter=Global-Policies
  $policyUnchanged=($null -ne $policiesBefore -and ($policiesBefore|ConvertTo-Json -Compress) -ceq ($policiesAfter|ConvertTo-Json -Compress))
  if (-not $policyUnchanged) {$failure=([string]$failure)+'; global policy comparison failed';$reason='policy_comparison_failed'}
 } catch {$failure=([string]$failure)+'; policy check: '+$_.Exception.ToString();$reason='policy_comparison_failed'}
}
Write-NewJson ($prefix+'_supervisor_finished.json') ([ordered]@{
 schema='e036-stage-a-supervisor-v1';label=$Label;supervisor_pid=$PID;
 ended_utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=$clock.Elapsed.TotalSeconds;
 stop_reason=$reason;watchdog_exit_code=$exitCode;watchdog_stopped=$childStopped;
 failure=$failure;global_policies_before=$policiesBefore;global_policies_after=$policiesAfter;
 global_policy_unchanged=$policyUnchanged;authority_sha256=$AuthoritySha256;watchdog_sha256=$WatchdogSha256
})
if ($failure -or $reason -ne 'completed') {throw ('Stage A supervisor failed: '+$reason+'; '+$failure)}
