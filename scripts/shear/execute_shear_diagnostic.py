from pathlib import Path
import subprocess,base64,hashlib,json,time,datetime,argparse
parser=argparse.ArgumentParser()
parser.add_argument("--execute",action="store_true")
parser.add_argument("--authority-start-utc")
parser.add_argument("--run-id",default="S04-E035-R004")
args=parser.parse_args()
if args.execute and not args.authority_start_utc: parser.error("Fresh explicit authority-start-utc required; do not reuse expired envelope")
case_root=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
assert args.run_id == 'S04-E035-R004', 'Only the newly authorized R004 is admitted'
root=case_root/'runs'/args.run_id
root.mkdir(parents=True,exist_ok=True)
deadline=None
if args.authority_start_utc:
    deadline=datetime.datetime.fromisoformat(args.authority_start_utc.replace('Z','+00:00')).timestamp()+900
deadline_iso=datetime.datetime.fromtimestamp(deadline,datetime.timezone.utc).isoformat() if deadline else 'AUTHORITY_NOT_SUPPLIED'
ps=(root/'supervise.ps1').read_text()
ps=ps.replace('$childHandle=$proc.Handle', '''$childHandle=$proc.Handle
try { $proc.ProcessorAffinity=[IntPtr]15 } catch { $proc.Kill(); $proc.WaitForExit(); @{reason='resource_binding_failed';pid=$proc.Id;exit_code=$proc.ExitCode}|ConvertTo-Json|Set-Content (Join-Path $c.root 'exit.json'); throw }
$peakRSS=0''')
ps=ps.replace('[Math]::Min(30000,$remaining)','[Math]::Min(1000,$remaining)')
ps=ps.replace('    $bytes=(Get-ChildItem', '''    $sample=$null
    try {
        $sample=[System.Diagnostics.Process]::GetProcessById($proc.Id)
        $peakBytes=$sample.PeakWorkingSet64
        $peakRSS=[Math]::Max($peakRSS,$peakBytes)
    } catch {
        if ($proc.HasExited) { break }
        $reason='monitor_failed'; $proc.Kill(); $proc.WaitForExit(); break
    } finally { if ($null -ne $sample) { $sample.Dispose() } }
    if ($proc.HasExited) { break }
    if ($peakBytes -gt 16GB) { $reason='memory_stopped'; $proc.Kill(); $proc.WaitForExit(); break }
    $bytes=(Get-ChildItem''')
ps=ps.replace("  reason=$reason;completed_marker=", "  peak_RSS_bytes=$peakRSS;cpu_affinity=15;reason=$reason;completed_marker=")
(root/'supervise_resource_bound.ps1').write_text(ps)
c=json.loads((root/'config.template.json').read_text())
c['arguments']="-batch \"maxNumCompThreads(4); checkcode('C:/q4runs/S04-E035-R004-20261021/run_shear_fem.m','-id'); addpath('C:/q4runs/S04-E035-R004-20261021'); run_shear_fem('C:/Users/xw436/GRIPHFiTH','C:/q4runs/S04-E035-R004-20261021/fem',1)\""
(root/'config.json').write_text(json.dumps(c,indent=2))
payload={'run_shear_fem.m':(root/'run_shear_fem.m').read_bytes(),'supervise.ps1':ps.encode(),'config.json':(root/'config.json').read_bytes()}
manifest={k:hashlib.sha256(v).hexdigest() for k,v in payload.items()}
(root/'deployment_manifest.json').write_text(json.dumps(manifest,indent=2))
lines=["$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'", "$r='C:/q4runs/S04-E035-R004-20261021'", "if ($env:COMPUTERNAME -ne 'CITPC12') {throw 'Wrong producer'}", "if ([Security.Principal.WindowsIdentity]::GetCurrent().Name.Split([char]92)[-1] -ne 'xw436') {throw 'Wrong account'}", "if (Test-Path $r) {throw 'Run root already exists'}", "if (@(Get-CimInstance Win32_Process -Filter \"Name='MATLAB.exe'\").Count -gt 0) {throw 'Competing MATLAB'}", "if ((Get-PSDrive C).Free -lt 15GB) {throw 'Insufficient disk'}", "if ((git -C C:/Users/xw436/GRIPHFiTH rev-parse HEAD) -ne '2098dc9114fe9e8140f1f25607e1c74ddc4a032e') {throw 'Native source identity changed'}", "New-Item -ItemType Directory $r | Out-Null"]
lines.pop() # Check retained dirty native files before creating the run root.
native_root=case_root/'preparation/native_sources'
native_paths={
    'newton_raphson.m':'Sources/+phase_field/+fem/+solver/newton_raphson.m',
    'post_iter_update.m':'Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m',
    'material_characteristic.m':'Sources/+phase_field/+init/material_characteristic.m',
    'AMOR.f90':'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.f90',
    'AT1_PENALTY.f90':'Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_PENALTY.f90',
}
native_hashes={rel:hashlib.sha256((native_root/name).read_bytes()).hexdigest() for name,rel in native_paths.items()}
(root/'native_source_lock.json').write_text(json.dumps(native_hashes,indent=2))
for rel,sha in native_hashes.items():
    lines.append("if ((Get-FileHash 'C:/Users/xw436/GRIPHFiTH/%s' -Algorithm SHA256).Hash.ToLower() -ne '%s') {throw 'Reviewed native file changed'}"%(rel,sha))
lines.append("New-Item -ItemType Directory $r | Out-Null")
for name,b in payload.items():
 lines.append("[IO.File]::WriteAllBytes(($r+'/%s'),[Convert]::FromBase64String('%s'))"%(name,base64.b64encode(b).decode()))
 lines.append("if ((Get-FileHash ($r+'/%s') -Algorithm SHA256).Hash.ToLower() -ne '%s') {throw 'Stage mismatch'}"%(name,manifest[name]))
lines += ["$tokens=$null; $parseErrors=$null; [Management.Automation.Language.Parser]::ParseFile(($r+'/supervise.ps1'),[ref]$tokens,[ref]$parseErrors)|Out-Null; if($parseErrors.Count){throw 'Supervisor syntax error'}", "$end=[DateTime]::Parse('{deadline_iso}').ToUniversalTime(); $remaining=($end-[DateTime]::UtcNow).TotalSeconds; if($remaining -lt 210){throw 'Insufficient remaining total budget'}", "$c=Get-Content ($r+'/config.json') -Raw|ConvertFrom-Json; $c.timeout_seconds=[Math]::Min(90,[Math]::Floor($remaining-120)); $c|ConvertTo-Json|Set-Content ($r+'/config.json')", "$mechanicalEnd=[DateTime]::Parse('{mechanical_deadline_iso}').ToUniversalTime(); if([DateTime]::UtcNow -gt $mechanicalEnd){throw 'Mechanical admission budget exceeded'}; $cmd='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\q4runs\\S04-E035-R004-20261021\\supervise.ps1 -Config C:\\q4runs\\S04-E035-R004-20261021\\config.json'", "$launch=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory='C:\\q4runs\\S04-E035-R004-20261021'}; if($launch.ReturnValue -ne 0){throw 'Create failed'}; $launch|Select-Object ProcessId,ReturnValue|ConvertTo-Json|Set-Content ($r+'/supervisor_submission.json')", "while (-not (Test-Path ($r+'/exit.json'))) { if([DateTime]::UtcNow -ge $end.AddSeconds(-120)){throw 'Retrieval deadline reached; inspect existing worker before any further action'}; Start-Sleep -Milliseconds 500 }", "Compress-Archive -Path ($r+'/launch.json'),($r+'/exit.json'),($r+'/stdout.log'),($r+'/stderr.log'),($r+'/fem'),($r+'/config.json'),($r+'/run_shear_fem.m'),($r+'/supervise.ps1'),($r+'/supervisor_submission.json') -DestinationPath ($r+'/result.zip')", "Write-Output 'ARCHIVE_BEGIN'; [Convert]::ToBase64String([IO.File]::ReadAllBytes($r+'/result.zip')); Write-Output 'ARCHIVE_END'", "Get-Content ($r+'/exit.json'); Get-Content ($r+'/stdout.log') -Tail 7; Get-Content ($r+'/stderr.log') -Tail 12"]
script='try { & {\n'+'\n'.join(lines)+'\n} } catch { [Console]::Error.WriteLine($_.Exception.ToString()); exit 1 }; exit 0\n'
script=script.replace('{deadline_iso}',deadline_iso)
mechanical_deadline_iso=datetime.datetime.fromtimestamp(time.time()+60,datetime.timezone.utc).isoformat()
script=script.replace('{mechanical_deadline_iso}',mechanical_deadline_iso)
(root/'stage_and_run.ps1').write_text(script)
if not args.execute:
    print(json.dumps({"prepared_only":True,"manifest":manifest,"authority_required":True}));raise SystemExit(0)
remaining=deadline-time.time()
print(json.dumps({'remaining_total_seconds':remaining,'required_child_plus_retrieval_seconds':210,'deployment_sha256':manifest}),flush=True)
if remaining<210: raise SystemExit('Insufficient remaining budget before SSH; no launch')
started=time.monotonic()
if (root/'result.zip').exists(): raise SystemExit('Existing result archive; inspect, do not overwrite')
with (root/'invocation.json').open('x') as claim:
    json.dump({'authority_start_utc':args.authority_start_utc,'deadline_utc':deadline_iso,'no_retry':True},claim)
out=err=''; returncode=None; archive_retrieved=False; transport_error=None
normalize=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else (v or '')
try:
    try:
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','citpc12-ssh','powershell -NoProfile -NonInteractive -Command -'],input=script,text=True,capture_output=True,errors='replace',timeout=max(1,remaining-2))
        out=normalize(p.stdout); err=normalize(p.stderr); returncode=p.returncode
    except subprocess.TimeoutExpired as exc:
        out=normalize(exc.stdout); err=normalize(exc.stderr); transport_error='TIMEOUT_REMOTE_STATE_UNKNOWN_NO_RETRY'
    except Exception as exc:
        transport_error=type(exc).__name__+': '+str(exc)
    if 'ARCHIVE_BEGIN' in out and 'ARCHIVE_END' in out.split('ARCHIVE_BEGIN',1)[1]:
        before,rest=out.split('ARCHIVE_BEGIN',1); b64,after=rest.split('ARCHIVE_END',1)
        payload_bytes=base64.b64decode(''.join(b64.split()),validate=True)
        with (root/'result.zip').open('xb') as archive: archive.write(payload_bytes)
        archive_retrieved=True; out=before+'ARCHIVE_RETRIEVED\n'+after
except Exception as exc:
    transport_error='ARCHIVE_CAPTURE_FAILED: '+str(exc)
finally:
    (root/'transport.log').write_text(out+'\nSTDERR\n'+err)
    receipt={'subprocess_wall_seconds':time.monotonic()-started,'returncode':returncode,'total_start_utc':args.authority_start_utc,'budget_end_utc':deadline_iso,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transport_error':transport_error,'archive_retrieved_this_invocation':archive_retrieved,'remote_state':'RETRIEVED_PENDING_INSPECTION' if archive_retrieved else 'UNKNOWN_NO_RETRY'}
    (root/'orchestration_cost.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt|{'output_tail':out[-4500:] if 'ARCHIVE_BEGIN' not in out else 'Incomplete archive retained locally; see transport.log','stderr_tail':err[-1000:]}),flush=True)
if not archive_retrieved: raise SystemExit(1)
