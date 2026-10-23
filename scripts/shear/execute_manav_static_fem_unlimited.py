"""Single-admission full FEM producer; prepare by default, never retries a solve."""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,subprocess,time,uuid,math

CASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
WORK=Path(__file__).resolve().parents[2]
RUN=CASE/'runs/S04-E035-R022'
REMOTE='C:/q4runs/S04-E035-R022-20261023'
NATIVE='C:/Users/xw436/GRIPHFiTH'
HOST='citpc12-ssh'
AUTHORITY=CASE/'descent_no_compute_cap_20261023/authority.json'

def ps_command(s):
    return 'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '+base64.b64encode(s.encode('utf-16le')).decode()

def call(argv,timeout,receipt,mechanical=False):
    started=time.monotonic();out=err='';rc=None
    try:
        p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,errors='replace')
        out,err,rc=p.stdout,p.stderr,p.returncode
        return p
    except subprocess.TimeoutExpired as failure:
        out=failure.stdout or b'';err=failure.stderr or b''
        if isinstance(out,bytes):out=out.decode(errors='replace')
        if isinstance(err,bytes):err=err.decode(errors='replace')
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
    source_modules=json.loads((CASE/'runs/S04-E035-R012/range_resolution/actual_source_manifest.json').read_text())
    locks.update({x['relative']:x['sha256'] for x in source_modules})
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).strip(),'Commit reviewed source first'
    native_eq=NATIVE+'/Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64'
    native_pf=NATIVE+'/Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_PENALTY.mexw64'
    matlab=("maxNumCompThreads(4); addpath('"+REMOTE+"'); addpath('"+NATIVE+"/Sources'); "
        "ep=which('phase_field.mex.fem.assembly.equilibrium.AMOR'); pp=which('phase_field.mex.fem.assembly.pf.AT1_PENALTY'); "
        "assert(strcmpi(strrep(ep,char(92),'/'),'"+native_eq+"')); assert(strcmpi(strrep(pp,char(92),'/'),'"+native_pf+"')); "
        "id=struct('matlab',version,'AMOR',ep,'AT1_PENALTY',pp,'code_commit','"+commit+"'); "
        "f=fopen('"+REMOTE+"/mex_runtime_identity.json','w'); fprintf(f,'%s',jsonencode(id)); fclose(f); "
        "run_manav_static_fem_box_unlimited('"+NATIVE+"','"+REMOTE+"/fem')")
    authority=AUTHORITY.read_bytes()
    config=dict(kind='fem',host='CITPC12',root=REMOTE,output=REMOTE+'/fem',executable='C:/Program Files/MATLAB/R2025b/bin/win64/MATLAB.exe',arguments='-batch "'+matlab+'"',commit=commit,unlimited_compute=True,authority_sha256=hashlib.sha256(authority).hexdigest())
    payload={name:(WORK/'scripts/shear'/name).read_bytes() for name in ['box_kkt_residual.m','box_q4_geometry.m','box_q4_pf_energy.m','bounded_mechanical_newton.m']}
    payload.update({name:(WORK/'scripts/shear/proposals'/name).read_bytes() for name in ['run_manav_static_fem_box_unlimited.m','box_phase_ray_descent.m','box_q4_ray_curvature.m','box_q4_ray_step.m']})
    payload.update({'supervise.ps1':(WORK/'scripts/shear/supervise_manav_unlimited.ps1').read_bytes(),'config.json':json.dumps(config,indent=2).encode(),'native_identity.json':json.dumps(identity,indent=2).encode(),'authority.json':authority})
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
    command='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File '+REMOTE+'/supervise.ps1 -Config '+REMOTE+'/config.json'
    lines += ["$tok=$null;$errs=$null;[Management.Automation.Language.Parser]::ParseFile(($r+'/supervise.ps1'),[ref]$tok,[ref]$errs)|Out-Null;if($errs.Count){throw 'Supervisor parse failed'}", "$cmd='"+command+"'", "$x=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory=$r}; $x|Select-Object ProcessId,ReturnValue|ConvertTo-Json|Set-Content ($r+'/supervisor_submission.json'); if($x.ReturnValue -ne 0){throw 'Supervisor creation failed'}; Get-Content ($r+'/supervisor_submission.json')"]
    script="try { & {\n"+'\n'.join(lines)+"\n} } catch { [Console]::Error.WriteLine($_.Exception.ToString());exit 1 };exit 0\n"
    (RUN/'stage_and_launch.template.ps1').write_text(script)
    (RUN/'prepared.json').write_text(json.dumps(dict(commit=commit,remote_root=REMOTE,unlimited_compute=True,kind='prepared_only',native_source_locks=locks),indent=2))
    print(json.dumps({'prepared':True,'commit':commit,'no_ssh':True}))


def launch():
    with (RUN/'invocation.json').open('x') as f:
        json.dump(dict(no_retry=True,authority=str(AUTHORITY),unlimited_compute=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f)
    script=(RUN/'stage_and_launch.template.ps1').read_text()
    local=RUN/'stage_and_launch.ps1';local.write_text(script)
    remote='C:/q4staging/S04E035_R022_'+uuid.uuid4().hex+'.ps1'
    (RUN/'staging_identity.json').write_text(json.dumps(dict(remote_outer_path=remote,outer_sha256=hashlib.sha256(script.encode()).hexdigest()),indent=2))
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(local),HOST+':'+remote],120,'upload')
    assert p.returncode==0,'Upload failed; no invocation'
    cmd="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';if((Get-FileHash '"+remote+"').Hash.ToLower() -ne '"+hashlib.sha256(script.encode()).hexdigest()+"'){throw 'Outer transfer mismatch'};& '"+remote+"'"
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(cmd)],120,'launch_transport')
    print(p.stdout,p.stderr[-500:]);assert p.returncode==0,'Unknown launch state; inspect before further action'


def status():
    s="$ProgressPreference='SilentlyContinue';$r='"+REMOTE+"';$o=@{root_exists=(Test-Path $r)};foreach($n in @('launch.json','exit.json','supervisor_submission.json','supervisor_exception.json')){if(Test-Path ($r+'/'+$n)){$o[$n]=Get-Content ($r+'/'+$n) -Raw|ConvertFrom-Json}};$o['states']=@(Get-ChildItem ($r+'/fem/state_*.mat') -ErrorAction SilentlyContinue).Count;$o['stdout_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stdout.log') -Tail 4 -ErrorAction SilentlyContinue));$o['stderr_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stderr.log') -Tail 12 -ErrorAction SilentlyContinue));$o|ConvertTo-Json -Depth 4 -Compress"
    label='status_'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(s)],30,label)
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
    remote_manifest="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$r='"+REMOTE+"';@(Get-ChildItem -LiteralPath $r -Recurse -File|ForEach-Object {@{path=$_.FullName.Substring($r.Length+1).Replace([char]92,'/');bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()}})|ConvertTo-Json -Depth 3 -Compress"
    m=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(remote_manifest)],120,'remote_manifest')
    assert m.returncode==0
    expected=json.loads(m.stdout)
    (RUN/'remote_file_manifest.json').write_text(json.dumps(expected,indent=2))
    p=call(['scp','-q','-r','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST+':'+REMOTE,str(dest)],540,'retrieval')
    assert p.returncode==0,'Partial retrieval preserved; inspect before further actions'
    files=[x for x in dest.rglob('*') if x.is_file()]
    bypath={str(x.relative_to(dest)):x for x in files}
    assert set(bypath)=={x['path'] for x in expected},'Retrieved file set mismatch'
    for item in expected:
        local=bypath[item['path']]
        assert local.stat().st_size==item['bytes'] and hashlib.sha256(local.read_bytes()).hexdigest()==item['sha256'],'Retrieved bytes mismatch: '+item['path']
    record=dict(all_remote_hashes_matched=True,files=len(files),bytes=sum(x.stat().st_size for x in files),exit=json.loads((dest/'exit.json').read_text()),completed=(dest/'fem/COMPLETED.txt').exists())
    (RUN/'retrieval_verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','launch','status','retrieve'],default='prepare',nargs='?');a=p.parse_args();globals()[a.action]()
