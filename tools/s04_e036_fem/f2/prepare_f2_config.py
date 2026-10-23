#!/usr/bin/env python3
"""Prepare one isolated F2 c1s4 packet from a committed source and real strict inputs.

Pure local file I/O and git object reads; no native/NN calls, SSH or dispatch.
Default controls reject dispatch. Root may generate a new approved packet only
when it explicitly chooses F2 as the next serial job. Existing packets are immutable.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import subprocess
import zipfile


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text())
def require(x,m):
    if not x:raise ValueError(m)
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    data=x if isinstance(x,bytes) else (x if isinstance(x,str) else json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
    with p.open('xb') as f:f.write(data)
def rel(p,root):
    q=PureWindowsPath(p).relative_to(PureWindowsPath(root))
    require(not any(x in ('.','..') for x in q.parts),'unsafe producer relative path')
    return Path(*q.parts).as_posix()
def git(checkout,*args):return subprocess.check_output(['git','-C',str(checkout),*args])


def prepare(a):
    require(re.fullmatch('[0-9a-f]{40}',a.source_commit),'full committed source required')
    require(git(a.checkout,'rev-parse',a.source_commit+'^{commit}').decode().strip()==a.source_commit,'invalid commit')
    strict=read(a.strict_config);base=a.strict_config.parent;root=strict['run_root'].replace('\\','/')
    require(strict['watchdog_id']=='strict_c1s4_01' and strict['request']==dict(cycle=1,substeps=[4],role='tightening'),'exact original c1s4 strict config required')
    require(strict['predecessor']['sha256']=='36193d74aba9b0d894524a391271412068bd8ebd220ce5d8b074d795f7eb937b','exact F1 c1s3 preimage required')
    def local(p):return base/rel(p,root)
    oldmanifest=local(strict['manifest_path']);require(sha(oldmanifest)==strict['manifest_sha256'],'strict manifest changed')
    oldauthority=local(strict['authority_file']);require(sha(oldauthority)==strict['authority_sha256'],'strict authority changed')
    evidence=local(strict['stage_a_evidence_file']);require(sha(evidence)==strict['stage_a_evidence_sha256'],'real Stage A evidence changed')
    template=base/'launch_strict_c1s4_01.ps1';require(template.is_file(),'original launch template required')
    old_records=read(oldmanifest)['files']
    for r in old_records:
        p=base/r['path'];require(p.is_file() and not p.is_symlink() and sha(p)==r['sha256'],'actual local reused bytes differ: '+str(p))
    require(not a.output.exists(),'fresh preparation directory required')
    payload=a.output/'payload';payload.mkdir(parents=True)
    label='f2_c1s4_01';code='code_f2_'+a.source_commit[:8]
    files=git(a.checkout,'ls-tree','-r','--name-only',a.source_commit,'tools/s04_e036_fem').decode().splitlines()
    files=[p for p in files if ('/f2/' in p or (len(Path(p).parts)==3 and Path(p).suffix in ('.m','.ps1')))]
    require('tools/s04_e036_fem/f2/e036_f2_driver.m' in files and 'tools/s04_e036_fem/f2/e036_f2_run_step.m' in files,'F2 producer must already be committed')
    source=[]
    for p in files:
        data=git(a.checkout,'show',a.source_commit+':'+p);write(payload/code/p,data)
        source.append(dict(path=p,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    lock=dict(schema='e036-f2-source-lock-v1',status='committed_exact_source',source_commit=a.source_commit,files=source)
    lockpath=payload/code/'source_lock.json';write(lockpath,lock)
    f2=dict(method='F2-frozen-f-nodal-box-u-d-u',limits=dict(max_outer=1500,u_maxeval=250,d_maxeval=250,f_tol=1e-10,d_inner_tol=4e-8),primary_F1_replacement=False)
    auth=copy.deepcopy(read(oldauthority));auth.update(authority_id='E036-B-F2-c1s4-01-root-dispatch',allowed_labels=[label],
        authorized_at_utc=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        request=dict(cycle=1,substeps=[4],role='f2_solver'),f2=f2,f2_source_lock_sha256=sha(lockpath),
        root_dispatch_approved=bool(a.root_dispatch_approved),
        human_authorization_ref='User authorized first-principles repair within E036; root 2026-10-23 directed isolated F2 c1s4 preparation, preserving original F1/strict. Execution is conditional on root_dispatch_approved and current strict natural terminal evidence (success or a complete scientific rejection), plus verified supervisor/job-object and owned-process cleanup; unknown or missing terminal evidence is not sufficient.',
        implementation_review_ref='Root read seven initial F2 files and directed producer preparation. No new test/review ladder or native validation claimed; actual two-point operator/energy validation is part of this one F2 producer job.')
    require(auth['max_compute_threads']==4 and auth['per_job_wall_seconds']==86400 and auth['step_wall_seconds']==43200 and auth['global_deadline_utc'] is None,'original finite guards changed')
    write(payload/(label+'_authority.json'),auth);write(payload/(label+'_evidence.json'),evidence.read_bytes())
    records={r['path']:r for r in old_records}
    for p in sorted(payload.rglob('*')):
        if p.is_file():records[p.relative_to(payload).as_posix()]=dict(path=p.relative_to(payload).as_posix(),sha256=sha(p))
    manifest=dict(schema='e036-f2-source-manifest-v1',files=[records[k] for k in sorted(records)])
    write(payload/(label+'_manifest.json'),manifest)
    c=copy.deepcopy(strict);c.update(code_root=root+'/'+code,watchdog_id=label,output_dir=root+'/output/'+label,
        execution_approved=bool(a.root_dispatch_approved),request=auth['request'],f2=f2,
        authority_file=root+'/'+label+'_authority.json',authority_sha256=sha(payload/(label+'_authority.json')),
        stage_a_evidence_file=root+'/'+label+'_evidence.json',stage_a_evidence_sha256=sha(payload/(label+'_evidence.json')),
        manifest_path=root+'/'+label+'_manifest.json',manifest_sha256=sha(payload/(label+'_manifest.json')),
        f2_source_lock_file=root+'/'+code+'/source_lock.json',f2_source_lock_sha256=sha(lockpath))
    c['provenance'].update(adapter_commit=a.source_commit,f2_source_lock_sha256=sha(lockpath),
        strict_template_config_sha256=sha(a.strict_config),generator_sha256=sha(__file__),
        scope='F2 new method only; exact native/build/old inputs reused; no primary F1 replacement')
    cfg=payload/(label+'_config.json');write(cfg,c)
    quote=lambda x:"'"+x.replace("'","''")+"'"
    entry='addpath('+quote(c['code_root']+'/tools/s04_e036_fem')+",'-begin');\n"
    entry+='addpath('+quote(c['code_root']+'/tools/s04_e036_fem/f2')+",'-begin');\n"
    entry+='e036_f2_driver('+quote(root+'/'+label+'_config.json')+','+quote(sha(cfg))+');\n'
    write(payload/(label+'_entry.m'),entry)
    launch=template.read_text().replace('strict_c1s4_01',label).replace('code_b34e97d',code)
    for suffix in ('authority.json','evidence.json','manifest.json','config.json','entry.m'):
        launch=launch.replace(sha(base/('strict_c1s4_01_'+suffix)),sha(payload/(label+'_'+suffix)))
    for name in ('stage_b_launcher.ps1','stage_b_watchdog.ps1'):
        launch=launch.replace(sha(base/'code_b34e97d/tools/s04_e036_fem'/name),sha(payload/code/'tools/s04_e036_fem'/name))
    guard="$a=Get-Content -LiteralPath (Join-Path $root ($label+'_authority.json')) -Raw|ConvertFrom-Json\nif($a.root_dispatch_approved -ne $true){throw 'F2 is prepared only; root has not approved dispatch'}\n"
    launch=launch.replace("foreach($suffix in @('_launch_request.json'",guard+"foreach($suffix in @('_launch_request.json'")
    write(payload/('launch_'+label+'.ps1'),launch)
    delivered=[dict(path=str(p),relative_path=p.relative_to(payload).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(payload.rglob('*')) if p.is_file()]
    zip_path=a.output/(label+'_packet.zip')
    with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED) as z:
        for r in delivered:z.write(r['path'],r['relative_path'])
    receipt=dict(schema='e036-f2-preparation-v1',status='prepared_not_dispatched',root_dispatch_approved=bool(a.root_dispatch_approved),
        root=root,label=label,source_commit=a.source_commit,source_lock_sha256=sha(lockpath),files=delivered,
        reused_bindings=len(old_records),native_calls=0,tests_run=0,
        zip=dict(path=str(zip_path),sha256=sha(zip_path),bytes=zip_path.stat().st_size),
        deployment_preconditions='Current strict has natural terminal evidence: success or complete scientific rejection, never unknown/missing terminal state; supervisor/job-object and owned-process cleanup verified, no busy compute, unused F2 label, exact source/input hash; root dispatch approval required')
    write(a.output/'preparation_receipt.json',receipt)
    return dict(receipt=str(a.output/'preparation_receipt.json'),sha256=sha(a.output/'preparation_receipt.json'),zip=receipt['zip'],root_dispatch_approved=a.root_dispatch_approved)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--strict-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--root-dispatch-approved',action='store_true')
    print(json.dumps(prepare(p.parse_args()),indent=2))
if __name__=='__main__':main()
