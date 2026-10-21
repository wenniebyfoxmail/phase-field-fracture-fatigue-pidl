"""Single-admission full FEM producer; prepare by default, never retries a solve."""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,subprocess,time,uuid

CASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
WORK=Path(__file__).resolve().parents[2]
RUN=CASE/'runs/S04-E035-R011'
REMOTE='C:/q4runs/S04-E035-R011-20261021'
NATIVE='C:/Users/xw436/GRIPHFiTH'
HOST='citpc12-ssh'
DEADLINE='2026-10-22T00:20:00Z'

def ps_command(s):
    return 'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '+base64.b64encode(s.encode('utf-16le')).decode()

def mechanical_remaining():
    paths=list(RUN.glob('identity_cost*.json'))+list(RUN.glob('status_*.json'))
    paths += [RUN/'upload.json',RUN/'approved_upload.json',RUN/'launch_transport.json']
    spent=sum(json.loads(p.read_text())['seconds'] for p in paths if p.exists())
    left=180-spent
    admission=RUN/'approved_admission.json'
    if not admission.exists(): admission=RUN/'invocation.json'
    if admission.exists():
        end=json.loads(admission.read_text())['mechanical_end_utc']
        left=min(left,datetime.datetime.fromisoformat(end).timestamp()-time.time())
    return left


def call(argv,timeout,receipt,mechanical=False):
    remaining=datetime.datetime.fromisoformat(DEADLINE.replace('Z','+00:00')).timestamp()-time.time()
    if remaining<=0: raise RuntimeError('Original total deadline exhausted; no remote call')
    timeout=min(timeout,remaining)
    if mechanical:
        left=mechanical_remaining()
        if left<=0: raise RuntimeError('Mechanical180s envelope exhausted; no remote call or reset')
        timeout=min(timeout,left)
    started=time.monotonic();out=err='';rc=None
    normalise=lambda v: v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
    try:
        p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,errors='replace')
        out,err,rc=p.stdout,p.stderr,p.returncode
        return p
    except subprocess.TimeoutExpired as failure:
        out,err=normalise(failure.stdout),normalise(failure.stderr)
        raise
    finally:
        (RUN/(receipt+'.log')).write_text(out+'\nSTDERR\n'+err)
        (RUN/(receipt+'.json')).write_text(json.dumps(dict(seconds=time.monotonic()-started,returncode=rc,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),unknown_if_interrupted=rc is None),indent=2))


def prepare():
    assert not (RUN/'invocation.json').exists(),'Preserve consumed invocation and immutable payload'
    identity=json.loads((RUN/'native_identity.json').read_text())
    assert identity['host']=='CITPC12' and identity['head']=='2098dc9114fe9e8140f1f25607e1c74ddc4a032e'
    locks=json.loads((CASE/'runs/S04-E035-R004/native_source_lock.json').read_text())
    locks.update({x['path']:x['sha256'].lower() for x in identity['sources']})
    actual=json.loads((RUN/'actual_helpers.json').read_text())
    locks.update({x['path']:x['sha256'].lower() for x in actual['sources']})
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).strip(),'Commit reviewed source first'
    native_eq=NATIVE+'/Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64'
    native_pf=NATIVE+'/Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_PENALTY.mexw64'
    matlab=("maxNumCompThreads(4); addpath('"+REMOTE+"'); addpath('"+NATIVE+"/Sources'); "
        "ep=which('phase_field.mex.fem.assembly.equilibrium.AMOR'); pp=which('phase_field.mex.fem.assembly.pf.AT1_PENALTY'); "
        "assert(strcmpi(strrep(ep,char(92),'/'),'"+native_eq+"')); assert(strcmpi(strrep(pp,char(92),'/'),'"+native_pf+"')); "
        "id=struct('matlab',version,'AMOR',ep,'AT1_PENALTY',pp,'code_commit','"+commit+"'); "
        "f=fopen('"+REMOTE+"/mex_runtime_identity.json','w'); fprintf(f,'%s',jsonencode(id)); fclose(f); "
        "checkcode('"+REMOTE+"/run_manav_static_fem_native_pf.m','-id'); checkcode('"+REMOTE+"/bounded_mechanical_newton.m','-id'); test_bounded_mechanics(); run_manav_static_fem_native_pf('"+NATIVE+"','"+REMOTE+"/fem')")
    config=dict(kind='fem',root=REMOTE,output=REMOTE+'/fem',executable='C:/Program Files/MATLAB/R2025b/bin/win64/MATLAB.exe',arguments='-batch "'+matlab+'"',commit=commit,timeout_seconds=9750,total_deadline_utc=DEADLINE,authority='HUMAN-DELEGATED-HQ-MANAV-NATIVE-PF-20261021; one24stateattempt;3hscience/1800sstep;recovery600s')
    payload={name:(WORK/'scripts/shear'/name).read_bytes() for name in ['run_manav_static_fem_native_pf.m','bounded_mechanical_newton.m','test_bounded_mechanics.m']}
    payload.update({'supervise.ps1':(WORK/'scripts/shear/supervise_manav_static.ps1').read_bytes(),'config.json':json.dumps(config,indent=2).encode(),'native_identity.json':json.dumps(identity,indent=2).encode()})
    lines=["$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'", "$r='"+REMOTE+"'", "if($env:COMPUTERNAME -ne 'CITPC12'){throw 'Wrong host'}", "if([Security.Principal.WindowsIdentity]::GetCurrent().Name.Split([char]92)[-1] -ne 'xw436'){throw 'Wrong account'}", "if(Test-Path $r){throw 'Existing producer root; no retry'}", "if(@(Get-CimInstance Win32_Process -Filter \"Name='MATLAB.exe'\").Count){throw 'Competing MATLAB'}", "if((Get-PSDrive C).Free -lt 15GB){throw 'Disk headroom'}", "if((git -C '"+NATIVE+"' rev-parse HEAD) -ne '"+identity['head']+"'){throw 'Native commit changed'}"]
    for rel,sha in locks.items():
        lines.append("if((Get-FileHash '"+NATIVE+'/'+rel+"').Hash.ToLower() -ne '"+sha+"'){throw 'Reviewed native source changed'}")
    for m in identity['mex']:
        lines.append("if((Get-FileHash '"+m['path']+"').Hash.ToLower() -ne '"+m['sha256'].lower()+"'){throw 'Installed MEX bytes changed'}")
    lines.append("New-Item -ItemType Directory $r|Out-Null")
    lines.append("@(Get-ChildItem 'C:/Users/xw436/GRIPHFiTH/Dependencies' -Recurse -Filter 'cholmod2.mexw64'|ForEach-Object {@{path=$_.FullName;bytes=$_.Length;sha256=(Get-FileHash $_.FullName).Hash}})|ConvertTo-Json|Set-Content ($r+'/linear_algebra_identity.json')")
    for name,b in payload.items():
        (RUN/name).write_bytes(b)
        lines += ["[IO.File]::WriteAllBytes(($r+'/%s'),[Convert]::FromBase64String('%s'))"%(name,base64.b64encode(b).decode()),"if((Get-FileHash ($r+'/%s')).Hash.ToLower() -ne '%s'){throw 'Transfer mismatch'}"%(name,hashlib.sha256(b).hexdigest())]
    lines += ["$tok=$null;$errs=$null;[Management.Automation.Language.Parser]::ParseFile(($r+'/supervise.ps1'),[ref]$tok,[ref]$errs)|Out-Null;if($errs.Count){throw 'Supervisor parse failed'}", "if([DateTime]::UtcNow -gt [DateTime]::Parse('"+DEADLINE+"').ToUniversalTime().AddSeconds(-900)){throw 'Insufficient total remainder'}", "if([DateTime]::UtcNow -gt [DateTime]::Parse('MECHANICAL_DEADLINE').ToUniversalTime()){throw 'Admission deadline'}", "$cmd='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\q4runs\\S04-E035-R011-20261021\\supervise.ps1 -Config C:\\q4runs\\S04-E035-R011-20261021\\config.json'", "$x=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory='C:\\q4runs\\S04-E035-R011-20261021'}; $x|Select-Object ProcessId,ReturnValue|ConvertTo-Json|Set-Content ($r+'/supervisor_submission.json'); if($x.ReturnValue -ne 0){throw 'Supervisor creation failed'}; Get-Content ($r+'/supervisor_submission.json')"]
    script="try { & {\n"+'\n'.join(lines)+"\n} } catch { [Console]::Error.WriteLine($_.Exception.ToString());exit 1 };exit 0\n"
    (RUN/'stage_and_launch.template.ps1').write_text(script)
    (RUN/'prepared.json').write_text(json.dumps(dict(commit=commit,remote_root=REMOTE,total_deadline_utc=DEADLINE,kind='prepared_only',native_source_locks=locks),indent=2))
    print(json.dumps({'prepared':True,'commit':commit,'no_ssh':True}))


def launch():
    # All identity/failed-transport costs remain counted; the guard never resets them.
    remaining=mechanical_remaining()
    prior=180-remaining
    assert remaining>=100, 'Require staging plus start and45s attribution reserve'
    mechanical_full_end=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=remaining)
    with (RUN/'invocation.json').open('x') as f:json.dump(dict(prior_identity_seconds=prior,remaining_mechanical_seconds=remaining,no_retry=True,deadline_utc=DEADLINE,mechanical_end_utc=mechanical_full_end.isoformat(),attribution_reserve_seconds=45,authority='HUMAN-DELEGATED-HQ-MANAV-NATIVE-PF-20261021'),f)
    end=time.monotonic()+remaining
    mechanical_end=mechanical_full_end-datetime.timedelta(seconds=45)
    script=(RUN/'stage_and_launch.template.ps1').read_text().replace('MECHANICAL_DEADLINE',mechanical_end.isoformat())
    local=RUN/'stage_and_launch.ps1';local.write_text(script)
    remote='C:/q4staging/S04E035_R011_'+uuid.uuid4().hex+'.ps1'
    with (RUN/'staging_identity.json').open('x') as f:
        json.dump(dict(remote_outer_path=remote,outer_sha256=hashlib.sha256(script.encode()).hexdigest(),mechanical_deadline_utc=mechanical_end.isoformat()),f,indent=2)
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(local),HOST+':'+remote],max(1,end-time.monotonic()-75),'upload',mechanical=True)
    assert p.returncode==0,'Upload failed; no invocation'
    assert mechanical_remaining()>=75, 'Insufficient start30s+attribution45s; no start request'
    cmd="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';if((Get-FileHash '"+remote+"').Hash.ToLower() -ne '"+hashlib.sha256(script.encode()).hexdigest()+"'){throw 'Outer transfer mismatch'};& '"+remote+"'"
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(cmd)],max(1,min(30,mechanical_remaining()-45)),'launch_transport',mechanical=True)
    print(p.stdout,p.stderr[-500:]);assert p.returncode==0,'Unknown launch state; inspect receipt before any further action'


def approved_resume():
    """Resume proven zero-start transport only after the exact human approval."""
    approval=json.loads((RUN/'direct_user_approval.json').read_text())
    assert approval['authority']=='direct_user_specific_R011_approval'
    assert approval['FEM_cap_seconds']==9750 and approval['original_deadline_utc']==DEADLINE
    assert json.loads((RUN/'upload.json').read_text())['returncode']==255
    assert 'Could not resolve hostname' in (RUN/'upload.log').read_text()
    assert not (RUN/'launch_transport.json').exists(),'Unknown or consumed start; inspect only'
    remaining=180-json.loads((RUN/'upload.json').read_text())['seconds']
    full_end=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=remaining)
    with (RUN/'approved_admission.json').open('x') as f:
        json.dump(dict(mechanical_end_utc=full_end.isoformat(),authority=approval['authority'],prior_invocation_preserved=True,scientific_starts_allowed=1),f)
    end=full_end-datetime.timedelta(seconds=45)
    script=(RUN/'stage_and_launch.template.ps1').read_text().replace('MECHANICAL_DEADLINE',end.isoformat())
    local=RUN/'approved_stage_and_launch.ps1';local.write_text(script)
    remote='C:/q4staging/S04E035_R011_approved_'+uuid.uuid4().hex+'.ps1'
    with (RUN/'approved_staging_identity.json').open('x') as f:
        json.dump(dict(remote_outer_path=remote,outer_sha256=hashlib.sha256(script.encode()).hexdigest(),mechanical_deadline_utc=end.isoformat()),f,indent=2)
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(local),HOST+':'+remote],min(30,mechanical_remaining()-75),'approved_upload',mechanical=True)
    assert p.returncode==0,'Second zero-start transport failed; stop'
    assert mechanical_remaining()>=75,'No start budget'
    cmd="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';if((Get-FileHash '"+remote+"').Hash.ToLower() -ne '"+hashlib.sha256(script.encode()).hexdigest()+"'){throw 'Outer transfer mismatch'};& '"+remote+"'"
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(cmd)],min(30,mechanical_remaining()-45),'launch_transport',mechanical=True)
    print(p.stdout,p.stderr[-500:]);assert p.returncode==0,'Unknown launch; inspect own receipt, never repeat start'


def status():
    s="$ProgressPreference='SilentlyContinue';$r='"+REMOTE+"';$o=@{root_exists=(Test-Path $r)};foreach($n in @('launch.json','exit.json','supervisor_submission.json')){if(Test-Path ($r+'/'+$n)){$o[$n]=Get-Content ($r+'/'+$n) -Raw|ConvertFrom-Json}};$o['states']=@(Get-ChildItem ($r+'/fem/state_*.mat') -ErrorAction SilentlyContinue).Count;$o['stdout_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stdout.log') -Tail 4 -ErrorAction SilentlyContinue));$o['stderr_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stderr.log') -Tail 12 -ErrorAction SilentlyContinue));$o|ConvertTo-Json -Depth 4 -Compress"
    label='status_'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(s)],30,label,mechanical=not (RUN/'producer_started.json').exists())
    print(p.stdout,p.stderr[-300:]);assert p.returncode==0
    state=json.loads(p.stdout)
    if state.get('launch.json'):
        launch=state['launch.json']
        expected=json.loads((RUN/'prepared.json').read_text())['commit']
        assert launch['root']==REMOTE and launch['code_commit']==expected and launch['host']=='CITPC12'
        assert launch['kind']=='fem' and launch['pid']>0
        (RUN/'producer_started.json').write_text(json.dumps(launch,indent=2))
    if state.get('exit.json'):
        assert (RUN/'producer_started.json').exists()
        terminal=state['exit.json']; started=json.loads((RUN/'producer_started.json').read_text())
        assert terminal['pid']==started['pid']
        (RUN/'producer_terminal.json').write_text(json.dumps(terminal,indent=2))


def retrieve():
    # Direct copy avoids duplicating a 10GiB producer tree with an archive.
    assert (RUN/'producer_terminal.json').exists(),'Verify terminal receipt before copying a producer tree'
    dest=RUN/'retrieved'
    assert not dest.exists(),'Existing retrieval; verify before another transfer'
    p=call(['scp','-q','-r','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST+':'+REMOTE,str(dest)],540,'retrieval')
    assert p.returncode==0,'Partial retrieval preserved; inspect before further actions'
    files=[x for x in dest.rglob('*') if x.is_file()]
    record=dict(files=len(files),bytes=sum(x.stat().st_size for x in files),exit=json.loads((dest/'exit.json').read_text()),completed=(dest/'fem/COMPLETED.txt').exists())
    (RUN/'retrieval_verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','launch','approved_resume','status','retrieve'],default='prepare',nargs='?');a=p.parse_args();globals()[a.action]()
