"""Single-admission full FEM producer; prepare by default, never retries a solve."""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,subprocess,time,uuid,zipfile

CASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
WORK=Path(__file__).resolve().parents[2]
RUN=CASE/'runs/S04-E035-R019'
REMOTE='C:/q4runs/S04-E035-R019-20261022'
HOST='gpu-server'
DEADLINE='2026-10-22T06:14:22Z'
WINDOW=CASE/'renewed_20261022/window.json'

def remaining_gpu_seconds():
    # New explicitly approved3GPUh; all old costs remain in separate ledgers.
    w=json.loads(WINDOW.read_text())
    assert w['answer']=='批准新6小时计算窗口' and w['PIDL_max_gpu_seconds']==10800
    assert w['total_end_utc']=='2026-10-22T06:14:22+00:00'
    remaining=min(w['PIDL_max_gpu_seconds'],datetime.datetime.fromisoformat(DEADLINE.replace('Z','+00:00')).timestamp()-time.time()-1800)
    assert __import__('math').isfinite(remaining) and remaining>0,'No PIDL time before original science deadline'
    return remaining

def ps_command(s):
    return 'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '+base64.b64encode(s.encode('utf-16le')).decode()

def mechanical_remaining():
    paths=list(RUN.glob('identity_cost*.json'))+list(RUN.glob('status_*.json'))
    paths += [RUN/'upload.json',RUN/'bundle_upload.json',RUN/'launch_transport.json']
    costs=[json.loads(p.read_text())['seconds'] for p in paths if p.exists()]
    assert all(__import__('math').isfinite(v) and v>=0 for v in costs),'Invalid receipt seconds'
    spent=sum(costs)
    left=180-spent
    if (RUN/'invocation.json').exists():
        end=json.loads((RUN/'invocation.json').read_text())['mechanical_end_utc']
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
    assert time.time()<datetime.datetime.fromisoformat(json.loads(WINDOW.read_text())['preparation_end_utc']).timestamp(),'Renewed preparation window exhausted'
    assert not (RUN/'invocation.json').exists(), 'Preserve consumed invocation'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).strip()
    mesh=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/examples/SENS_shear/meshed_geom2.msh')
    manifest=json.loads((CASE/'manav_static_20261021/source_manifest.json').read_text())
    assert hashlib.sha256(mesh.read_bytes()).hexdigest()==manifest['NNmesh']['sha256']
    tracked=subprocess.check_output(['git','ls-files','source'],cwd=WORK,text=True).splitlines()
    files={('code/'+name):(WORK/name).read_bytes() for name in tracked if name.endswith('.py')}
    for name in ['SENS_tensile/field_computation.py','scripts/shear/run_manav_static_pidl_box.py','scripts/shear/launch_manav_static_pidl_box.py']:
        files['code/'+name]=(WORK/name).read_bytes()
    for path in (RUN/'deps').rglob('*'):
        if path.is_file(): files[str(path.relative_to(RUN))]=path.read_bytes()
    files['mesh.msh']=mesh.read_bytes()
    files['deps_manifest.json']=(RUN/'deps_manifest.json').read_bytes()
    bundle=RUN/'code_bundle.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)
    hashes={name:hashlib.sha256(content).hexdigest() for name,content in files.items()}
    bundle_sha=hashlib.sha256(bundle.read_bytes()).hexdigest()
    args='-B -u "'+REMOTE+'/code/scripts/shear/launch_manav_static_pidl_box.py" --mesh "'+REMOTE+'/mesh.msh" --output "'+REMOTE+'/pidl" --epochs 10000'
    config=dict(kind='pidl',root=REMOTE,output=REMOTE+'/pidl',executable='C:/Users/xw436/pavetrack_env/Scripts/python.exe',arguments=args,commit=commit,timeout_seconds=remaining_gpu_seconds(),total_deadline_utc=DEADLINE,gpu_uuid='GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7',reference_sha256='REFERENCE_SHA')
    payload={'supervise.ps1':(WORK/'scripts/shear/supervise_manav_pidl_renewed.ps1').read_bytes(),'config.json':json.dumps(config,indent=2).encode()}
    lines=["$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'", "$r='"+REMOTE+"'", "if($env:COMPUTERNAME -ne 'D-26-09'){throw 'Wrong host'}", "if(Test-Path $r){throw 'Existing root, no retry'}", "if((Get-PSDrive C).Free -lt 15GB){throw 'Disk headroom'}", "if((Get-FileHash 'BUNDLE_PATH').Hash.ToLower() -ne '"+bundle_sha+"'){throw 'Bundle transfer mismatch'}", "New-Item -ItemType Directory $r|Out-Null", "Expand-Archive -LiteralPath 'BUNDLE_PATH' -DestinationPath $r"]
    for name,sha in hashes.items():
        lines.append("if((Get-FileHash ($r+'/%s')).Hash.ToLower() -ne '%s'){throw 'Bundle file mismatch'}"%(name,sha))
    for name,content in payload.items():
        lines.append("[IO.File]::WriteAllBytes(($r+'/%s'),[Convert]::FromBase64String('%s'))"%(name,base64.b64encode(content).decode()))
    lines += ["$config=Get-Content ($r+'/config.json') -Raw;$config.Replace('REFERENCE_SHA','REFERENCE_SHA_VALUE')|Set-Content ($r+'/config.json')", "[IO.File]::WriteAllBytes(($r+'/GPU_RELEASED.json'),[Convert]::FromBase64String('REFERENCE_BASE64'))", "$tok=$null;$errs=$null;[Management.Automation.Language.Parser]::ParseFile(($r+'/supervise.ps1'),[ref]$tok,[ref]$errs)|Out-Null;if($errs.Count){throw 'Supervisor parse failed'}", "if([DateTime]::UtcNow -gt [DateTime]::Parse('MECHANICAL_DEADLINE').ToUniversalTime()){throw 'Admission deadline'}"]
    command='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File '+REMOTE+'/supervise.ps1 -Config '+REMOTE+'/config.json'
    lines += ["$cmd='"+command+"'", "$x=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory=$r};$x|Select-Object ProcessId,ReturnValue|ConvertTo-Json|Set-Content ($r+'/supervisor_submission.json');if($x.ReturnValue -ne 0){throw 'Supervisor creation failed'};Get-Content ($r+'/supervisor_submission.json')"]
    script="try { & {\n"+'\n'.join(lines)+"\n} } catch { [Console]::Error.WriteLine($_.Exception.ToString());exit 1 };exit 0\n"
    (RUN/'stage_and_launch.template.ps1').write_text(script)
    (RUN/'prepared.json').write_text(json.dumps(dict(commit=commit,remote_root=REMOTE,total_deadline_utc=DEADLINE,kind='pidl',bundle_sha256=bundle_sha,files=hashes),indent=2))
    print(json.dumps(dict(prepared=True,no_ssh=True,commit=commit,bundle_bytes=bundle.stat().st_size,files=len(files))))


def launch():
    # All identity/failed-transport costs remain counted; the guard never resets them.
    verification=CASE/'runs/S04-E035-R018/analysis/reference_verification.json'
    qualified=json.loads(verification.read_text())
    assert qualified['complete_valid_reference'] and qualified['accepted_prefix']==24
    reference=json.dumps(dict(reference=qualified,authority='HQ-SHEAR-RENEWED-MAIN-COMPARISON-WINDOW-20261022',reservation='Prior D5 route closed, explicitly no future reservation; direct human conditional PIDL authority; fresh admission enforced by supervisor'),indent=2).encode()
    (RUN/'GPU_RELEASED.json').write_bytes(reference)
    remaining_gpu_seconds()
    assert qualified['model_contract']=='common-box-at1-seed1-20261021'
    assert qualified['kkt_definition']=='normal_cone_unscaled_original_gradient_units'
    remaining=mechanical_remaining()
    prior=180-remaining
    assert remaining>=100, 'Require staging plus start and45s attribution reserve'
    mechanical_full_end=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=remaining)
    with (RUN/'invocation.json').open('x') as f:json.dump(dict(prior_identity_seconds=prior,remaining_mechanical_seconds=remaining,no_retry=True,deadline_utc=DEADLINE,mechanical_end_utc=mechanical_full_end.isoformat(),attribution_reserve_seconds=45,authority='HQ-SHEAR-RENEWED-MAIN-COMPARISON-WINDOW-20261022'),f)
    end=time.monotonic()+remaining
    mechanical_end=mechanical_full_end-datetime.timedelta(seconds=45)
    script=(RUN/'stage_and_launch.template.ps1').read_text().replace('MECHANICAL_DEADLINE',mechanical_end.isoformat())
    local=RUN/'stage_and_launch.ps1'
    remote='C:/Users/xw436/S04E035_R019_'+uuid.uuid4().hex+'.ps1'
    bundle_remote=remote+'.zip'
    script=script.replace('BUNDLE_PATH',bundle_remote).replace('REFERENCE_SHA_VALUE',hashlib.sha256(reference).hexdigest()).replace('REFERENCE_BASE64',base64.b64encode(reference).decode())
    local.write_text(script)
    with (RUN/'staging_identity.json').open('x') as f:
        json.dump(dict(remote_outer_path=remote,outer_sha256=hashlib.sha256(script.encode()).hexdigest(),mechanical_deadline_utc=mechanical_end.isoformat()),f,indent=2)
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(RUN/'code_bundle.zip'),HOST+':'+bundle_remote],max(1,end-time.monotonic()-90),'bundle_upload',mechanical=True)
    assert p.returncode==0,'Bundle upload failed, no invocation'
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(local),HOST+':'+remote],max(1,end-time.monotonic()-75),'upload',mechanical=True)
    assert p.returncode==0,'Upload failed; no invocation'
    assert mechanical_remaining()>=75, 'Insufficient start30s+attribution45s; no start request'
    cmd="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';if((Get-FileHash '"+remote+"').Hash.ToLower() -ne '"+hashlib.sha256(script.encode()).hexdigest()+"'){throw 'Outer transfer mismatch'};& '"+remote+"'"
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(cmd)],max(1,min(30,mechanical_remaining()-45)),'launch_transport',mechanical=True)
    print(p.stdout,p.stderr[-500:]);assert p.returncode==0,'Unknown launch state; inspect receipt before any further action'


def status():
    s="$ProgressPreference='SilentlyContinue';$r='"+REMOTE+"';$o=@{root_exists=(Test-Path $r)};foreach($n in @('launch.json','exit.json','supervisor_submission.json')){if(Test-Path ($r+'/'+$n)){$o[$n]=Get-Content ($r+'/'+$n) -Raw|ConvertFrom-Json}};$o['states']=@(Get-ChildItem ($r+'/pidl/state_*.npz') -ErrorAction SilentlyContinue).Count;$o['stdout_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stdout.log') -Tail 4 -ErrorAction SilentlyContinue));$o['stderr_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stderr.log') -Tail 12 -ErrorAction SilentlyContinue));$o|ConvertTo-Json -Depth 4 -Compress"
    label='status_'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(s)],30,label,mechanical=not (RUN/'producer_started.json').exists())
    print(p.stdout,p.stderr[-300:]);assert p.returncode==0
    state=json.loads(p.stdout)
    if state.get('launch.json'):
        launch=state['launch.json']
        expected=json.loads((RUN/'prepared.json').read_text())['commit']
        assert launch['root']==REMOTE and launch['code_commit']==expected and launch['host']=='D-26-09'
        assert launch['kind']=='pidl' and launch['pid']>0
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
    record=dict(files=len(files),bytes=sum(x.stat().st_size for x in files),exit=json.loads((dest/'exit.json').read_text()),completed=(dest/'pidl/COMPLETED.txt').exists())
    (RUN/'retrieval_verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','launch','status','retrieve'],default='prepare',nargs='?');a=p.parse_args();globals()[a.action]()
