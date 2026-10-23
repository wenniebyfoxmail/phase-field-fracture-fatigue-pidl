#!/usr/bin/env python3
"""Bind a staged, isolated B payload to real Stage A files; no remote action.

The payload must already contain byte-identical native/build/input copies.
This only writes an authority-bound config/manifest/entry; missing evidence or
bytes are errors. It never creates an accepted Stage A receipt or starts a job.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text())


def require(test,message):
    if not test:raise ValueError(message)


def win(path):return str(PureWindowsPath(path)).replace('\\','/')


def relative(path,root):
    p,r=PureWindowsPath(path),PureWindowsPath(root)
    try:rel=p.relative_to(r)
    except ValueError as e:raise ValueError('bound path outside producer root') from e
    require(not any(part in ('..','.') for part in rel.parts),'noncanonical path')
    return Path(*rel.parts).as_posix()


def write_new(path,value):
    data=value if isinstance(value,str) else json.dumps(value,indent=2,allow_nan=False)+'\n'
    with Path(path).open('x') as f:f.write(data)


PUBLISHED_MAIN = ('main_config','main_driver_binding','main_input_binding','main_authority','main_manifest')


def validate_published_main_spec(pred,request,local,root):
    """Check original JSON identity and relocated proof paths; MATLAB checks arrays.

    This path asserts publication of an old step only, never completion of its
    parent window. Original JSON/MAT paths remain unchanged inside copied bytes.
    """
    fields={name+suffix for name in PUBLISHED_MAIN for suffix in ('_file','_sha256')}
    if not fields.intersection(pred):return None
    require(fields.issubset(pred),'all five published-main file/hash pairs are required')
    steps=request['substeps'];steps=steps if isinstance(steps,list) else [steps]
    require(pred['kind']=='verified_window_step' and request['role'] in ('tightening','nodal_oracle')
            and request['cycle'] in (1,83) and steps in ([2],[4])
            and not {'main_window_result_file','main_window_result_sha256'}.intersection(pred),
            'published main proof is exclusive to strict/oracle old-step admission')
    for name in PUBLISHED_MAIN:
        path,digest=pred[name+'_file'],pred[name+'_sha256']
        relative(path,root)
        require(re.fullmatch('[0-9a-f]{64}',digest) and sha(local(path))==digest,
                'published main bytes differ: '+name)
    c=read(local(pred['main_config_file']));a=read(local(pred['main_authority_file']))
    m=read(local(pred['main_manifest_file']));label=c['watchdog_id'];original=win(c['run_root'])
    expected=dict(cycle=request['cycle'],substeps=[1,2,3,4,5],role='main')
    require(c['request']==expected and c['execution_approved'] is True
            and re.fullmatch('[a-z0-9_]+',label)
            and win(c['output_dir'])==original+'/output/'+label,
            'original config must name the same-cycle main five-step request')
    require(c['authority_sha256']==pred['main_authority_sha256']
            and c['manifest_sha256']==pred['main_manifest_sha256']
            and win(c['authority_file'])==original+'/'+label+'_authority.json'
            and win(c['manifest_path'])==original+'/'+label+'_manifest.json',
            'original config authority/manifest identity differs')
    require(a['schema']=='e036-stage-b-authority-v1' and a['stage']=='B'
            and a['request']==expected and a['allowed_labels']==[label]
            and win(a['run_root'])==original
            and a['stage_a_evidence_sha256']==c['stage_a_evidence_sha256'],
            'original main authority differs')
    require(m['schema']=='e036-stage-b-source-v1','original main source manifest required')
    rows=[r for r in m['files'] if r['path']==label+'_authority.json']
    require(len(rows)==1 and rows[0]['sha256']==c['authority_sha256'],
            'original manifest must bind its original authority')
    proof=win(PureWindowsPath(pred['main_config_file']).parent)
    expected_paths=dict(main_config=proof+'/'+label+'_config.json',
        main_authority=proof+'/'+label+'_authority.json',main_manifest=proof+'/'+label+'_manifest.json',
        main_driver_binding=proof+'/output/'+label+'/driver_binding.mat',
        main_input_binding=proof+'/output/'+label+'/window/input_binding.mat')
    for name,path in expected_paths.items():
        require(win(pred[name+'_file']).casefold()==path.casefold(),'relocated main proof layout differs: '+name)
    key=pred['state_key'];step=steps[0]-1
    expected_key=dict(trajectory=c['predecessor']['state_key']['trajectory'],nominal_umax=.12,
        cycle=request['cycle'],substep=step,displacement=[.02999988,.05999988,.08999988][step-1],
        timing='post_commit',gp_order='(+,+),(-,+),(+,-),(-,-)')
    require(key==expected_key,'published main source must be the exact immediate predecessor')
    folder=proof+f'/output/{label}/window/c{request["cycle"]:04d}_s{step:02d}'
    for name,filename in (('path','step_checkpoint.mat'),('proposal_file','proposal.mat'),('completion_file','completion.mat')):
        require(win(pred[name]).casefold()==(folder+'/'+filename).casefold(),'selected old-step path differs')
    return c


def prepare(args):
    a=read(args.stage_a_config);authority=read(args.authority);pred=read(args.predecessor_spec)
    evidence=read(args.stage_a_evidence);root=win(authority['run_root']);a_root=win(a['run_root'])
    require(root.casefold()!=a_root.casefold(),'B root must differ from Stage A root')
    require(authority['schema']=='e036-stage-b-authority-v1' and authority['stage']=='B','wrong authority')
    require(authority['global_deadline_utc'] is None,'current scope has no cumulative deadline')
    require(authority['allowed_labels']==[args.label] and re.fullmatch('[a-z0-9_]+',args.label),'one unique label required')
    require(authority['stage_a_evidence_sha256']==sha(args.stage_a_evidence),'authority Stage A evidence hash differs')
    require(evidence['schema']=='e036-stage-a-evidence-v1','real Stage A evidence manifest required')
    request=authority['request'];steps=request['substeps'];cycle=request['cycle'];role=request['role']
    steps=steps if isinstance(steps,list) else [steps]
    require((role=='main' and ((cycle in (1,83) and steps==[1,2,3,4,5]) or (cycle in (20,60) and steps==[4]))) or
            (role in ('tightening','nodal_oracle') and cycle in (1,83) and steps in ([2],[4])),'undeclared request')
    require(authority['max_compute_threads'] in (1,2,3,4) and
            0<authority['step_wall_seconds']<=authority['per_job_wall_seconds'],'explicit finite job clock required')
    for name in ('per_job_wall_seconds','step_wall_seconds'):
        require(isinstance(authority[name],(int,float)) and authority[name]<float('inf'),'finite clock required')
    payload=args.payload.resolve();require(payload.is_dir(),'existing staged payload required')
    def moved(path):return root+'/'+relative(path,a_root)
    def local(path):return payload/relative(path,root)
    def checked(path,digest):require(local(path).is_file() and sha(local(path))==digest,'staged bytes differ: '+str(path))
    keep=('code_root','native_snapshot','overlay_root','build_root','common_file','mesh_file')
    c={name:moved(a[name]) for name in keep}
    for name in ('common_sha256','mesh_sha256','build_completion_sha256','source_checks'):
        c[name]=a[name]
    checked(c['common_file'],c['common_sha256']);checked(c['mesh_file'],c['mesh_sha256'])
    checked(c['build_root']+'/completion.json',c['build_completion_sha256'])
    done=read(local(c['build_root']+'/completion.json'))
    checked(c['build_root']+'/build_receipt.json',done['receipt_sha256'])
    built=read(local(c['build_root']+'/build_receipt.json'))
    for r in built['source_records']:
        for prefix in (c['native_snapshot']+'/Sources/+phase_field/+mex/',c['build_root']+'/source/'):
            checked(prefix+r['relative_path'],r['sha256'])
    runtime=[]
    for r in a['runtime_bindings']:
        new=dict(r)
        if r['name']!='cholmod2':new['path']=moved(r['path']);checked(new['path'],r['sha256'])
        runtime.append(new)
    for r in c['source_checks']:checked(c['native_snapshot']+'/'+r['path'],r['sha256'])
    checked(pred['path'],pred['sha256'])
    for prefix in ('origin','proposal','completion','main_window_result'):
        if prefix+'_file' in pred:checked(pred[prefix+'_file'],pred[prefix+'_sha256'])
    original_main=validate_published_main_spec(pred,request,local,root)
    if original_main is not None:
        require(original_main['common_sha256']==c['common_sha256'] and
                original_main['mesh_sha256']==c['mesh_sha256'],'main and strict/oracle support differ')
    for helper in ('e036_final_candidate','e036_native_candidate','e036_policy'):
        h=sha(local(c['code_root']+'/tools/s04_e036_fem/'+helper+'.m'))
        checked(c['overlay_root']+'/Sources/+phase_field/+audit/'+helper+'.m',h)
    initial=None
    require((role=='nodal_oracle') == (args.initial_fields_spec is not None),'initial fields belong only to oracle')
    if args.initial_fields_spec is not None:
        initial=read(args.initial_fields_spec)
        for name in ('path','source_snapshot_path','source_completion_path'):
            digest='sha256' if name=='path' else name.replace('_path','_sha256')
            checked(initial[name],initial[digest])
        for akey,ikey in (('initial_fields_sha256','sha256'),('initial_source_snapshot_sha256','source_snapshot_sha256'),
                         ('initial_source_completion_sha256','source_completion_sha256')):
            require(authority[akey]==initial[ikey],'oracle authority differs from exact source bytes')
    # Manifest every staged source/support/input file. Config/entry/manifest are
    # added afterward to avoid a self-referential hash cycle; entry is bound by
    # the supervisor and config is passed with its exact hash.
    names={k:args.label+'_'+k+ext for k,ext in [('authority','.json'),('evidence','.json'),('manifest','.json'),('config','.json'),('entry','.m')]}
    for k in ('authority','evidence','manifest','config','entry'):require(not (payload/names[k]).exists(),'attempt filename already exists')
    for k,src in [('authority',args.authority),('evidence',args.stage_a_evidence)]:
        with (payload/names[k]).open('xb') as f:f.write(src.read_bytes())
    records=[]
    for path in sorted(payload.rglob('*')):
        if path.is_file():
            require(not path.is_symlink(),'payload symlinks forbidden')
            records.append(dict(path=path.relative_to(payload).as_posix(),sha256=sha(path)))
    require(records,'empty payload')
    write_new(payload/names['manifest'],dict(schema='e036-stage-b-source-v1',files=records))
    c.update(run_root=root,stage_a_root=a_root,output_dir=root+'/output/'+args.label,
        execution_approved=True,runtime_bindings=runtime,request=request,predecessor=pred,watchdog_id=args.label,
        authority_file=root+'/'+names['authority'],authority_sha256=sha(payload/names['authority']),
        stage_a_evidence_file=root+'/'+names['evidence'],stage_a_evidence_sha256=sha(payload/names['evidence']),
        manifest_path=root+'/'+names['manifest'],manifest_sha256=sha(payload/names['manifest']),
        source_commit=a['provenance']['original_native_source_commit'],
        provenance=dict(stage_a_config_sha256=sha(args.stage_a_config),stage_a_provenance=a['provenance'],
            generator_sha256=sha(__file__),scope='byte-identical native/build relocation; new B controls only'))
    if initial is not None:c['initial_fields']=initial
    write_new(payload/names['config'],c)
    quote=lambda s:"'"+s.replace("'","''")+"'"
    entry='addpath('+quote(c['code_root']+'/tools/s04_e036_fem')+",'-begin');\n"
    entry+='e036_stage_b_driver('+quote(root+'/'+names['config'])+','+quote(sha(payload/names['config']))+');\n'
    write_new(payload/names['entry'],entry)
    return dict(schema='e036-stage-b-preparation-v1',status='prepared_not_launched',native_solves=0,
                root=root,label=args.label,config=dict(path=str(payload/names['config']),sha256=sha(payload/names['config'])),
                entry=dict(path=str(payload/names['entry']),sha256=sha(payload/names['entry'])))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stage-a-config','stage-a-evidence','authority','predecessor-spec','payload'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--initial-fields-spec',type=Path)
    p.add_argument('--label',required=True)
    print(json.dumps(prepare(p.parse_args()),indent=2))


if __name__=='__main__':main()
