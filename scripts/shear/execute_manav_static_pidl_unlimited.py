"""Single-admission full FEM producer; prepare by default, never retries a solve."""
from pathlib import Path
import zipfile,argparse,base64,datetime,hashlib,json,subprocess,time,uuid,math

CASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
WORK=Path(__file__).resolve().parents[2]
RUN=CASE/'runs/S04-E035-R023'
REMOTE='C:/q4runs/S04-E035-R023-20261023'
NATIVE='C:/Users/xw436/GRIPHFiTH'
HOST='gpu-server'
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
    assert not (RUN/'invocation.json').exists(), 'Preserve consumed invocation'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).strip()
    mesh=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/examples/SENS_shear/meshed_geom2.msh')
    manifest=json.loads((CASE/'manav_static_20261021/source_manifest.json').read_text())
    assert hashlib.sha256(mesh.read_bytes()).hexdigest()==manifest['NNmesh']['sha256']
    tracked=subprocess.check_output(['git','ls-files','source'],cwd=WORK,text=True).splitlines()
    files={('code/'+name):(WORK/name).read_bytes() for name in tracked if name.endswith('.py')}
    for name in ['SENS_tensile/field_computation.py','scripts/shear/run_manav_static_pidl_unlimited.py','scripts/shear/launch_manav_static_pidl_unlimited.py']:
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
    args='-B -u "'+REMOTE+'/code/scripts/shear/launch_manav_static_pidl_unlimited.py" --mesh "'+REMOTE+'/mesh.msh" --output "'+REMOTE+'/pidl" --epochs 10000'
    config=dict(kind='pidl',root=REMOTE,output=REMOTE+'/pidl',executable='C:/Users/xw436/pavetrack_env/Scripts/python.exe',arguments=args,commit=commit,host='D-26-09',unlimited_compute=True,authority_sha256=hashlib.sha256(AUTHORITY.read_bytes()).hexdigest(),gpu_uuid='GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7',reference_sha256='REFERENCE_SHA')
    payload={'supervise.ps1':(WORK/'scripts/shear/supervise_manav_pidl_renewed.ps1').read_bytes(),'config.json':json.dumps(config,indent=2).encode(),'authority.json':AUTHORITY.read_bytes()}
    lines=["$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'", "$r='"+REMOTE+"'", "if($env:COMPUTERNAME -ne 'D-26-09'){throw 'Wrong host'}", "if(Test-Path $r){throw 'Existing root, no retry'}", "if((Get-PSDrive C).Free -lt 15GB){throw 'Disk headroom'}", "if((Get-FileHash 'BUNDLE_PATH').Hash.ToLower() -ne '"+bundle_sha+"'){throw 'Bundle transfer mismatch'}", "New-Item -ItemType Directory $r|Out-Null", "Expand-Archive -LiteralPath 'BUNDLE_PATH' -DestinationPath $r"]
    for name,sha in hashes.items():
        lines.append("if((Get-FileHash ($r+'/%s')).Hash.ToLower() -ne '%s'){throw 'Bundle file mismatch'}"%(name,sha))
    for name,content in payload.items():
        lines.append("[IO.File]::WriteAllBytes(($r+'/%s'),[Convert]::FromBase64String('%s'))"%(name,base64.b64encode(content).decode()))
    lines += ["$config=Get-Content ($r+'/config.json') -Raw;$config.Replace('REFERENCE_SHA','REFERENCE_SHA_VALUE')|Set-Content ($r+'/config.json')", "[IO.File]::WriteAllBytes(($r+'/GPU_RELEASED.json'),[Convert]::FromBase64String('REFERENCE_BASE64'))", "$tok=$null;$errs=$null;[Management.Automation.Language.Parser]::ParseFile(($r+'/supervise.ps1'),[ref]$tok,[ref]$errs)|Out-Null;if($errs.Count){throw 'Supervisor parse failed'}"]
    command='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File '+REMOTE+'/supervise.ps1 -Config '+REMOTE+'/config.json'
    lines += ["$cmd='"+command+"'", "$x=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory=$r};$x|Select-Object ProcessId,ReturnValue|ConvertTo-Json|Set-Content ($r+'/supervisor_submission.json');if($x.ReturnValue -ne 0){throw 'Supervisor creation failed'};Get-Content ($r+'/supervisor_submission.json')"]
    script="try { & {\n"+'\n'.join(lines)+"\n} } catch { [Console]::Error.WriteLine($_.Exception.ToString());exit 1 };exit 0\n"
    (RUN/'stage_and_launch.template.ps1').write_text(script)
    (RUN/'prepared.json').write_text(json.dumps(dict(commit=commit,remote_root=REMOTE,unlimited_compute=True,kind='pidl',bundle_sha256=bundle_sha,files=hashes),indent=2))
    print(json.dumps(dict(prepared=True,no_ssh=True,commit=commit,bundle_bytes=bundle.stat().st_size,files=len(files))))


def launch():
    verification=CASE/'runs/S04-E035-R022/analysis/reference_verification.json'
    qualified=json.loads(verification.read_text())
    assert qualified['complete_valid_reference'] and qualified['accepted_prefix']==24
    assert qualified['model_contract']=='common-box-at1-seed1-20261021'
    assert qualified['kkt_definition']=='normal_cone_unscaled_original_gradient_units'
    reference=json.dumps(dict(reference=qualified,reference_verification_sha256=hashlib.sha256(verification.read_bytes()).hexdigest(),authority=str(AUTHORITY),reservation='Direct human conditional authority, fresh GPU admission required'),indent=2).encode()
    (RUN/'GPU_RELEASED.json').write_bytes(reference)
    with (RUN/'invocation.json').open('x') as f:
        json.dump(dict(no_retry=True,authority=str(AUTHORITY),unlimited_compute=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f)
    remote='C:/Users/xw436/S04E035_R023_'+uuid.uuid4().hex+'.ps1'
    bundle_remote=remote+'.zip'
    script=(RUN/'stage_and_launch.template.ps1').read_text().replace('BUNDLE_PATH',bundle_remote).replace('REFERENCE_SHA_VALUE',hashlib.sha256(reference).hexdigest()).replace('REFERENCE_BASE64',base64.b64encode(reference).decode())
    local=RUN/'stage_and_launch.ps1';local.write_text(script)
    (RUN/'staging_identity.json').write_text(json.dumps(dict(remote_outer_path=remote,outer_sha256=hashlib.sha256(script.encode()).hexdigest()),indent=2))
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(RUN/'code_bundle.zip'),HOST+':'+bundle_remote],180,'bundle_upload')
    assert p.returncode==0,'Bundle upload failed; no invocation'
    p=call(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=25',str(local),HOST+':'+remote],120,'upload')
    assert p.returncode==0,'Upload failed; no invocation'
    cmd="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';if((Get-FileHash '"+remote+"').Hash.ToLower() -ne '"+hashlib.sha256(script.encode()).hexdigest()+"'){throw 'Outer transfer mismatch'};& '"+remote+"'"
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(cmd)],120,'launch_transport')
    print(p.stdout,p.stderr[-500:]);assert p.returncode==0,'Unknown launch state; inspect before further action'

def status():
    s="$ProgressPreference='SilentlyContinue';$r='"+REMOTE+"';$o=@{root_exists=(Test-Path $r)};foreach($n in @('launch.json','exit.json','supervisor_submission.json','supervisor_exception.json')){if(Test-Path ($r+'/'+$n)){$o[$n]=Get-Content ($r+'/'+$n) -Raw|ConvertFrom-Json}};$o['states']=@(Get-ChildItem ($r+'/pidl/state_*.npz') -ErrorAction SilentlyContinue).Count;$o['stdout_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stdout.log') -Tail 4 -ErrorAction SilentlyContinue));$o['stderr_tail']=[string]::Join([Environment]::NewLine,[string[]]@(Get-Content ($r+'/stderr.log') -Tail 12 -ErrorAction SilentlyContinue));$o|ConvertTo-Json -Depth 4 -Compress"
    label='status_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
    p=call(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=25',HOST,ps_command(s)],30,label)
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
    record=dict(all_remote_hashes_matched=True,files=len(files),bytes=sum(x.stat().st_size for x in files),exit=json.loads((dest/'exit.json').read_text()),completed=(dest/'pidl/COMPLETED.txt').exists())
    (RUN/'retrieval_verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','launch','status','retrieve'],default='prepare',nargs='?');a=p.parse_args();globals()[a.action]()
