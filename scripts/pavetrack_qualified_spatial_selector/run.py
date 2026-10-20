"""E029 bounded managed controller and isolated role worker. No execution on import."""
import time
START=time.monotonic()
import argparse,collections,copy,json,os,subprocess,sys,threading,uuid
from pathlib import Path
import e029_support as c
from e029_guard import Guard
from e029_permissions import Files,request
import e029_phases as phases

ORDER=[('bank',None),('spatial',None),*[('fit',k) for k in range(3)],*[('held',k) for k in range(3)],('evaluate',None),('render',None)]
def name(role,fold):return role if fold is None else f'{role}_{fold}'

def authority(value,manifest,commit,plan):
    expected=dict(run_id=plan['proposed_run_id'],reviewed_commit=commit,source_manifest_sha256=manifest,execute_once=True,wall_seconds=3600,GPU_uuid=plan['producer']['gpu_uuid'])
    if value!=expected or type(value.get('execute_once')) is not bool or value['execute_once'] is not True or type(value.get('wall_seconds')) is not int:raise PermissionError('exact new E029 one-shot authorisation required')

def barrier(run,files,label):
    if not files:raise ValueError('empty freeze')
    result=dict(label=label,files={f:c.sha(run/f) for f in files})
    c.write(run/(label+'.json'),result);return result

def verify_barrier(run,label,trusted):
    value=c.read(run/(label+'.json'))
    if value!=trusted or value['label']!=label or not value['files']:raise ValueError('freeze identity')
    for f,h in value['files'].items():c.checked(run/f,h)
    return value

def transition(completed,role,fold):
    if len(completed)>=len(ORDER) or ORDER[len(completed)]!=(role,fold):raise PermissionError('out-of-order role/fold')
    return completed+[(role,fold)]

def phase_inventory(out,role,fold):
    required={'resource.json'}
    if role=='bank':required|={'bank.json','B1.json'}
    elif role=='spatial':
        required|={'native_max.npy','descriptors.json','cases.json','progress.json','runtime.json','spatial_freeze.json'}
        cases=c.read(out/'cases.json')['cases']
        if len(cases)!=6 or len({r['index'] for r in cases})!=6:raise ValueError('six fixed case inventory')
        required|={f"case_{r['index']}_rgb.npy" for r in cases}
    elif role=='fit':required|={a+suffix for a in c.adapter.ARMS for suffix in ['_FIT.json','_inference.json']}
    elif role=='held':required|={a+'.json' for a in ['saved_E018_geometry',*c.adapter.ARMS]}
    elif role=='evaluate':required|={'result.json','evaluation.json'}
    elif role=='render':required|={'F00_utility.png','F01_capacity.png','F02_cases.png','README_analysis.md'}
    actual={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
    visible={n for n in actual if not n.startswith('.mplconfig/')}
    if visible!=required:raise ValueError('strict phase inventory '+role+': '+str(visible^required))
    return actual


def read_caps(role,k,run,paths,bank=None):
    local=[run/'bank/bank.json'];extras=[]
    if role=='bank':return [],[paths[x] for x in ['E017_zip','contexts','E018_OOF',*[f'E018_model_{j}' for j in range(3)]]]
    if role=='spatial':
        extras=[paths[x] for x in ['R002_scope','R002_projections','checkpoint','network']]
        extras += [v['prepared_image'] for im,v in bank['images'].items() if v['location'] not in ['24','1638','2027']]
    elif role=='fit':
        local += [run/'spatial/descriptors.json',run/'spatial/spatial_freeze.json'];extras=[paths['E017_zip'],paths['metadata']]
    elif role=='held':local += [run/'spatial/descriptors.json',run/'bank/B1.json',run/'models_freeze.json',*[run/f'fit_{k}/{a}_inference.json' for a in c.adapter.ARMS]]
    elif role=='evaluate':
        local += [run/'prediction_freeze.json',*[run/f'held_{j}/{a}.json' for j in range(3) for a in ['saved_E018_geometry',*c.adapter.ARMS]],*[run/f'fit_{j}/{a}_inference.json' for j in range(3) for a in c.adapter.ARMS]];extras=[paths['metadata']]
    elif role=='render':
        local += [run/'evaluate/result.json',run/'evaluate/evaluation.json',run/'spatial/cases.json',run/'spatial/native_max.npy',*[run/f'fit_{j}/{a}_FIT.json' for j in range(3) for a in c.adapter.ARMS]]
        local += list((run/'spatial').glob('case_*_rgb.npy'))
    return local,extras

def runtime_reads(lock):
    if len(lock['files'])!=121:raise ValueError('frozen Pillow runtime inventory')
    out=[]
    for rel in lock['files']:
        if Path(rel).is_absolute() or '..' in Path(rel).parts or '\\' in rel:raise ValueError('unsafe library path')
        out.append(Path(lock['overlay'])/rel)
    return out


def role_counts(role,k,bank,plan):
    if role=='bank' or role=='render':return {}
    if role=='spatial':return {key:plan['counts'][key] for key in ['source_image_reads','source_image_decodes','native_tiles','reused_contexts','new_contexts','descriptor_rows','case_captures']}
    if role=='evaluate':return dict(evaluation_baselines=6,evaluation_comparisons=24)
    held=set(plan['held_groups'][k]);n=sum(r['eligible'] and ((r['location'] in held)==(role=='held')) for r in bank['candidates'])
    if role=='fit':return dict(model_sets=2,model_fits=6,linear_solves=6,training_target_rows=2*n,prediction_rows=2*n,context_builds=1,FIT_baselines=1,FIT_policy_comparisons=10)
    if role=='held':return dict(prediction_rows=2*n,B1_replay_rows=n,context_builds=1)
    raise ValueError('phase')


def persist_then_cleanup(path,payload,cleanup):
    try:
        try:c.write(path,payload)
        except BaseException:
            try:os.write(2,('E029 first stop persistence failed: '+repr(payload)+'\n').encode()[:4096])
            except BaseException:pass
    finally:cleanup()


def worker(args,plan,cfg,lock,paths,manifest_sha):
    env=c.core.module('e029_environment',c.ROOT/'scripts/pavetrack_target_spatial/environment.py');env.production_environment(plan)
    launch=c.read(args.run/'launch.json');authority(launch['approval_value'],manifest_sha,args.reviewed_commit,plan)
    control=c.read(args.run/'control.json');ident=request(c.read(args.request),args.role,args.fold)
    import psutil
    for label,h in ident['input_freezes'].items():
        c.checked(args.run/(label+'.json'),h)
        frozen=c.read(args.run/(label+'.json'))
        for f,binding in frozen['files'].items():c.checked(args.run/f,binding)
    if ident['manifest']!=manifest_sha or control['expected']!=ident or control['controller_pid'] not in [p.pid for p in psutil.Process().parents()]:raise PermissionError('worker parent/control identity')
    out=args.run/name(args.role,args.fold);out.mkdir(exist_ok=False)
    bank=c.read(args.run/'bank/bank.json') if args.role!='bank' else None
    expected_counts=role_counts(args.role,args.fold,bank,plan);role_plan=copy.deepcopy(plan);role_plan['counts']=expected_counts
    guard=Guard(role_plan,args.run);guard.note=out
    local,extras=read_caps(args.role,args.fold,args.run,paths,bank)
    # These checks spawn identity/inventory commands, before restricting subprocesses.
    t=None;engine=None
    if args.role=='spatial':
        source=c.core.module('e029_frozen_source',c.ROOT/'scripts/pavetrack_spatial_source/run.py')
        t,identity=env.production_checks(plan,guard,source.prior.runtime.desktop_inventory,c.sha);c.write(out/'runtime.json',identity)
    code_roots=[Path(sys.prefix),Path(sys.base_prefix),Path(os.environ.get('WINDIR','C:/Windows'))/'System32',Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts']
    library_files=runtime_reads(c.read(c.ROOT/'docs/research/S01/S01-E028/runtime_lock.json'))
    source_files=[c.ROOT/f for f in c.read(c.DOC/'source_manifest.json')['files'] if f.startswith('scripts/') and f.endswith('.py')]
    if os.environ['MPLCONFIGDIR']!=str(args.run/('_mplcache_'+name(args.role,args.fold))):raise PermissionError('own phase font cache only')
    caps=Files(local+extras+source_files+library_files,[out,Path(os.environ['MPLCONFIGDIR'])],code_roots);sys.addaudithook(caps.hook)
    stop=guard.watch()
    try:
        if args.role=='bank':phases.bank(paths,lock,plan,cfg,args.run,out,guard)
        elif args.role=='spatial':
            # Verify code/checkpoint filenames are exactly the pinned ones.
            if Path(paths['network']).name!='deepcrack.py' or Path(paths['checkpoint']).name!='DeepCrack_CT260_FT1.pth' or Path(paths['network']).parent!=Path(paths['checkpoint']).parent:raise ValueError('fixed network directory')
            engine=source.Engine(t,plan,Path(paths['checkpoint']).parent)
            phases.spatial(paths,lock,plan,cfg,args.run,out,guard,engine)
        elif args.role=='fit':phases.fit(paths,lock,plan,cfg,args.run,out,guard,args.fold)
        elif args.role=='held':phases.held(paths,lock,plan,cfg,args.run,out,guard,args.fold)
        elif args.role=='evaluate':phases.evaluate(paths,lock,plan,cfg,args.run,out,guard)
        elif args.role=='render':
            from e029_analyze import render
            render(args.run,out,plan)
        guard.check()
        if dict(guard.counts)!=expected_counts:raise ValueError('exact role counts')
        c.write(out/'resource.json',guard.receipt());phase_inventory(out,args.role,args.fold)
        c.write(out/'receipt.json',dict(role=args.role,fold=args.fold,manifest=manifest_sha,files={p.relative_to(out).as_posix():c.sha(p) for p in out.rglob('*') if p.is_file()}))
    finally:stop.set()


def terminate_owned(child,run,controller_pid):
    import psutil
    p=psutil.Process(child.pid)
    if controller_pid not in [q.pid for q in p.parents()] or str(run) not in ' '.join(p.cmdline()):raise RuntimeError('own child identity uncertain; external wrapper must inspect')
    ids=[(q.pid,q.create_time()) for q in [p,*p.children(recursive=True)]]
    subprocess.run(['taskkill.exe','/PID',str(child.pid),'/T','/F'],check=True,stdout=subprocess.DEVNULL,timeout=5)
    child.wait(timeout=10)
    for pid,birth in ids:
        try:
            live=psutil.Process(pid)
            if live.create_time()==birth:raise RuntimeError('owned child survives; no retry')
        except psutil.NoSuchProcess:pass


def controller(args,plan,cfg,lock,paths,manifest_sha):
    env=c.core.module('e029_environment_main',c.ROOT/'scripts/pavetrack_target_spatial/environment.py');env.production_environment(plan)
    authority(c.read(args.approval_file),manifest_sha,args.reviewed_commit,plan)
    if paths!=c.read(c.DOC/'private_paths.template.json'):raise ValueError('exact private input placement')
    if args.run!=Path(plan['run_path']) or args.run.exists():raise PermissionError('fresh named run only')
    args.run.mkdir(parents=True,exist_ok=False);guard=Guard(plan,args.run,start=START);guard.note=args.run;done=[];counts=collections.Counter();active=[None];trusted={};cleanup_lock=threading.Lock()
    def cleanup():
        with cleanup_lock:
            if active[0] is not None and active[0].poll() is None:terminate_owned(active[0],args.run,os.getpid())
            active[0]=None
    guard.on_fatal=cleanup;stop=guard.watch()
    try:
        c.write(args.run/'launch.json',dict(reviewed_commit=args.reviewed_commit,source_manifest_sha256=manifest_sha,paths_sha256=c.sha(args.paths),approval_sha256=c.sha(args.approval_file),approval_value=c.read(args.approval_file),pid=os.getpid(),command=sys.argv,producer=plan['producer'],execution_enabled_in_package=False))
        for key,rec in lock['input_files'].items():
            p=Path(paths[key]);guard.check()
            if rec['bytes'] is not None and p.stat().st_size!=rec['bytes']:raise ValueError('input bytes '+key)
            if p.stat().st_size>256*1024**2:raise ValueError('single input cap '+key)
            c.checked(p,rec['sha256'])
        for role,k in ORDER:
            transition(done,role,k)
            for label,value in trusted.items():verify_barrier(args.run,label,value)
            if role=='fit':
                for f,h in c.read(args.run/'spatial/spatial_freeze.json')['files'].items():c.checked(args.run/'spatial'/f,h)
            if role=='held':verify_barrier(args.run,'models_freeze',trusted['models_freeze'])
            if role=='evaluate':verify_barrier(args.run,'prediction_freeze',trusted['prediction_freeze'])
            req=dict(role=role,fold=k,manifest=manifest_sha,run_id='S01-E029-R001',input_freezes={label:c.sha(args.run/(label+'.json')) for label in trusted});rp=args.run/(name(role,k)+'_request.json');c.write(rp,req);c.write(args.run/'control.json',dict(controller_pid=os.getpid(),expected=req))
            stdout=args.run/(name(role,k)+'.stdout.log');stderr=args.run/(name(role,k)+'.stderr.log')
            cmd=[sys.executable,str(Path(__file__).resolve()),'--run',str(args.run),'--paths',str(args.paths),'--reviewed-commit',args.reviewed_commit,'--manifest-sha256',manifest_sha,'--role',role,'--request',str(rp)]
            if k is not None:cmd+=['--fold',str(k)]
            with stdout.open('wb') as so,stderr.open('wb') as se:
                child=subprocess.Popen(cmd,stdout=so,stderr=se,env=dict(os.environ,MPLCONFIGDIR=str(args.run/('_mplcache_'+name(role,k)))));active[0]=child
                try:
                    while child.poll() is None:guard.check();time.sleep(.1)
                except BaseException as exc:
                    # Persist the trigger before attempting our exact Popen tree cleanup.
                    try:persist_then_cleanup(args.run/'first_stop.json',dict(reason=repr(exc),phase=name(role,k),child_pid=child.pid,no_retry=True),cleanup)
                    except BaseException as failure:
                        try:c.write(args.run/'cleanup_uncertain.json',dict(reason=repr(failure),child_pid=child.pid,no_retry=True))
                        except BaseException:pass
                    raise
            active[0]=None
            if child.returncode!=0:raise RuntimeError(f'first-stop {name(role,k)} exit={child.returncode}; see stderr; no retry')
            receipt=c.read(args.run/name(role,k)/'receipt.json')
            if (receipt['role'],receipt['fold'],receipt['manifest'])!=(role,k,manifest_sha):raise ValueError('phase receipt identity')
            for f,h in receipt['files'].items():c.checked(args.run/name(role,k)/f,h)
            resource=c.read(args.run/name(role,k)/'resource.json');counts.update(resource['counts'])
            if any(key not in plan['counts'] or value>plan['counts'][key] for key,value in counts.items()):raise RuntimeError('aggregate count cap before next phase')
            for key in ['peak_RSS_bytes','peak_GPU_allocated_bytes','peak_GPU_reserved_bytes']:
                if resource[key]>4*1024**3:raise MemoryError('phase memory cap')
            done=transition(done,role,k)
            if role=='spatial':trusted['spatial_freeze']=barrier(args.run,['spatial/'+f for f in receipt['files']],'spatial_freeze')
            if role=='bank':trusted['bank_freeze']=barrier(args.run,['bank/bank.json','bank/B1.json'],'bank_freeze')
            if (role,k)==('fit',2):trusted['models_freeze']=barrier(args.run,[f'fit_{j}/{a}_inference.json' for j in range(3) for a in c.adapter.ARMS],'models_freeze')
            if (role,k)==('held',2):trusted['prediction_freeze']=barrier(args.run,[f'held_{j}/{a}.json' for j in range(3) for a in ['saved_E018_geometry',*c.adapter.ARMS]]+[f'fit_{j}/{a}_inference.json' for j in range(3) for a in c.adapter.ARMS],'prediction_freeze')
            c.write(args.run/'progress.json',dict(completed=done,counts=dict(counts),resource=guard.receipt()));guard.check()
        if dict(counts)!=plan['counts']:raise ValueError('final exact phase counters')
        verify_barrier(args.run,'models_freeze',trusted['models_freeze']);verify_barrier(args.run,'prediction_freeze',trusted['prediction_freeze'])
        c.write(args.run/'resource.json',dict(controller=guard.receipt(),counts=dict(counts),phase_resources={name(r,k):c.read(args.run/name(r,k)/'resource.json') for r,k in ORDER}))
        c.write(args.run/'status.json',dict(state='completed',scientific_verdict=c.read(args.run/'evaluate/result.json')['scientific_verdict'],counts=dict(counts),completed=done))
        c.write(args.run/'output_receipt.json',dict(files={p.relative_to(args.run).as_posix():dict(bytes=p.stat().st_size,sha256=c.sha(p)) for p in args.run.rglob('*') if p.is_file()}));guard.check()
    except BaseException as ex:
        c.write(args.run/'status.json',dict(state='stopped',reason=repr(ex),completed=done,counts=dict(counts),science=None,no_retry=True));raise
    finally:
        stop.set();cleanup()


def main():
    p=argparse.ArgumentParser()
    for key in ['run','paths','request','approval-file']:p.add_argument('--'+key,type=Path)
    p.add_argument('--reviewed-commit',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--role',choices=[r for r,k in ORDER]);p.add_argument('--fold',type=int);args=p.parse_args()
    plan,cfg=c.config()
    if plan['execution_enabled'] is not False:raise PermissionError('immutable package must remain disabled; exact external approval required')
    lock=c.read(c.DOC/'data_lock.json');manifest=c.DOC/'source_manifest.json'
    if c.sha(manifest)!=args.manifest_sha256:raise ValueError('exact source manifest')
    for f,h in c.read(manifest)['files'].items():c.checked(c.ROOT/f,h)
    paths=c.read(args.paths)
    if args.role:worker(args,plan,cfg,lock,paths,args.manifest_sha256)
    else:
        if args.approval_file is None:raise PermissionError('one-shot approval-file required; package execution_enabled=false')
        controller(args,plan,cfg,lock,paths,args.manifest_sha256)
if __name__=='__main__':main()
