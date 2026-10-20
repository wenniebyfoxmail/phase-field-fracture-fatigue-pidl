"""One approved Linux lifecycle: bootstrap -> exact controller -> fixed stop/success pack."""
import argparse,hashlib,json,os,pwd,shutil,signal,socket,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import e029_linux_process as managed
DOC=HERE.parents[1]/'docs/research/S01/S01-E029'

def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def authorization(a,cfg,commit,manifest):
    expected=dict(run_id='S01-E029-R001',reviewed_commit=commit,source_manifest_sha256=manifest,execute_once=True,wall_seconds=None,GPU_uuid=cfg['producer']['gpu_uuid'])
    if a!=expected or type(a.get('execute_once')) is not bool or a.get('wall_seconds') is not None:raise PermissionError('exact Linux no-wall one-shot approval')
def verify_source(root,manifest_sha):
    mp=root/'docs/research/S01/S01-E029/taobo_source_manifest.json'
    if sha(mp)!=manifest_sha:raise ValueError('Linux manifest identity')
    for rel,h in read(mp)['files'].items():
        p=root/rel
        if Path(rel).is_absolute() or '..' in Path(rel).parts or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()) or sha(p)!=h:raise ValueError('Linux source binding')
    return mp

def invoke(cmd,tag,cfg,logs,env):
    import e029_system_proc as psutil
    root=Path(cfg['linux_paths']['root']);records={};child=None;failure=None;clean_errors=[];peak=0;started=time.monotonic()
    def stop():
        nonlocal records
        if child is None:return
        # Find only members of our retained child session. Never kill by UID/name.
        for process in psutil.process_iter():
            try:
                if process.uids().real!=os.getuid() or os.getsid(process.pid)!=child.pid:continue
                rec=managed.identity(process)
                if rec['uid']!=os.getuid() or not (str(root) in ' '.join(rec['cmd']) or Path(rec['cwd']).is_relative_to(root)):raise PermissionError('session member outside task')
                old=records.get(rec['pid'])
                if old and old['birth']!=rec['birth']:raise PermissionError('session PID reuse')
                records[rec['pid']]=rec
            except (psutil.NoSuchProcess,psutil.AccessDenied,ProcessLookupError):continue
            except BaseException as e:clean_errors.append(repr(e))
        for sig in (signal.SIGTERM,signal.SIGKILL):
            for rec in reversed(list(records.values())):
                try:
                    p=psutil.Process(rec['pid'])
                    if p.status()==psutil.STATUS_ZOMBIE:continue
                    if not managed.matches(p,rec):raise PermissionError('PID birth/UID/cmd/cwd changed')
                    p.send_signal(sig)
                except psutil.NoSuchProcess:pass
                except BaseException as e:clean_errors.append(repr(e))
            until=time.monotonic()+2
            while time.monotonic()<until:
                alive=[]
                for rec in records.values():
                    try:
                        p=psutil.Process(rec['pid'])
                        if p.create_time()==rec['birth'] and p.status()!=psutil.STATUS_ZOMBIE:alive.append(p)
                    except psutil.NoSuchProcess:pass
                if not alive:break
                time.sleep(.05)
        try:child.wait(timeout=2)
        except BaseException as e:clean_errors.append(repr(e))
        for rec in records.values():
            try:
                p=psutil.Process(rec['pid'])
                if p.create_time()==rec['birth'] and p.status()!=psutil.STATUS_ZOMBIE:clean_errors.append('surviving owned PID '+str(rec['pid']))
            except psutil.NoSuchProcess:pass
    try:
        with (logs/(tag+'.stdout')).open('xb') as out,(logs/(tag+'.stderr')).open('xb') as err:
            parent_birth=psutil.Process(os.getpid()).create_time()
            watched=['/usr/bin/python3','-I',str(HERE/'e029_parent_watch.py'),'--parent',str(os.getpid()),'--birth',str(parent_birth),'--note',str(logs/(tag+'.parent_stop.json')),'--',*cmd]
            child=subprocess.Popen(watched,stdout=out,stderr=err,env=env,cwd=root,start_new_session=True)
            try:records[child.pid]=managed.identity(psutil.Process(child.pid))
            except psutil.NoSuchProcess:pass
            write(logs/(tag+'.launch.json'),dict(pid=child.pid,command=cmd,lifeline_command=watched,started=time.time(),session=child.pid))
            while child.poll() is None:
                try:
                    p=psutil.Process(child.pid);family=[p,*p.children(recursive=True)]
                except psutil.NoSuchProcess:
                    if child.poll() is not None:break
                    time.sleep(.05);continue
                rss=psutil.Process(os.getpid()).memory_info().rss
                for q in family:
                    try:
                        rec=managed.identity(q);records[q.pid]=rec;rss+=q.memory_info().rss
                    except psutil.NoSuchProcess:continue
                peak=max(peak,rss)
                if peak>cfg['budget']['RSS_bytes']:raise MemoryError('aggregate Linux lifecycle RSS')
                size=0
                for folder in [root/'run',logs]:
                    for f in folder.rglob('*'):
                        try:
                            if f.is_file():size+=f.stat().st_size
                        except FileNotFoundError:pass
                if size>cfg['budget']['output_bytes']:raise RuntimeError('Linux output cap')
                if psutil.disk_usage(root).free<cfg['budget']['minimum_free_disk_bytes']:raise RuntimeError('Linux disk reserve')
                time.sleep(.25)
            if child.returncode!=0:raise RuntimeError(tag+' stopped '+str(child.returncode))
    except BaseException as e:failure=e
    finally:
        # Log writes, signal exceptions and normal exits all pass through owned-session cleanup.
        try:stop()
        except BaseException as e:clean_errors.append(repr(e))
        try:write(logs/(tag+'.resource.json'),dict(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=peak,failure=repr(failure) if failure else None,cleanup_uncertain=clean_errors,owned=list(records.values())))
        except BaseException as e:
            if failure is None:failure=e
    if clean_errors:raise RuntimeError('cleanup_uncertain; original='+repr(failure)+'; '+repr(clean_errors))
    if failure:raise failure

def execution_environment(root):
    tmp=root/'tmp';cache=root/'cache'
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','PIP_CONFIG_FILE':'/dev/null','CONFIG_SITE':'/dev/null','CC':'/usr/bin/gcc','CXX':'/usr/bin/g++','AR':'/usr/bin/ar','RANLIB':'/usr/bin/ranlib','CFLAGS':'-O2','CPPFLAGS':'','LDFLAGS':'','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
    env.update(CUDA_VISIBLE_DEVICES='5',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(root/'mplconfig'),TMPDIR=str(tmp),XDG_CACHE_HOME=str(cache),XDG_CONFIG_HOME=str(root/'config'),CUDA_CACHE_PATH=str(cache/'cuda'),TORCH_HOME=str(cache/'torch'),TRITON_CACHE_DIR=str(cache/'triton'))
    return env


def main():
    p=argparse.ArgumentParser();p.add_argument('--reviewed-commit',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--approval',type=Path,required=True);args=p.parse_args()
    cfg=read(DOC/'taobo_run_config.json');lp=cfg['linux_paths'];root=Path(lp['root']);source=Path(lp['source']);manifest=verify_source(source,args.manifest_sha256)
    if cfg['execution_enabled'] is not False or cfg['budget']['wall_seconds'] is not None or cfg['budget']['total_task_wall_seconds'] is not None:raise PermissionError('disabled package/no wall limit')
    if sys.platform!='linux' or socket.gethostname()!='GPUServer8' or pwd.getpwuid(os.getuid()).pw_name!='drtao' or HERE.parents[1]!=source:raise PermissionError('exact Linux task host/source')
    if args.approval!=Path(lp['approval']):raise PermissionError('exact approval file')
    authorization(read(args.approval),cfg,args.reviewed_commit,args.manifest_sha256)
    import e029_system_proc as proc
    for key in ['run','logs','runtime','runtime_lock','archive','launch_claim']:
        if Path(lp[key]).exists():raise FileExistsError('fresh once-only '+key)
    with Path(lp['launch_claim']).open('x') as f:json.dump(dict(commit=args.reviewed_commit,manifest=args.manifest_sha256,approval_sha256=sha(args.approval),time=time.time(),pid=os.getpid(),wrapper_birth=proc.Process().create_time(),birth_clock='Linux starttime ticks'),f)
    logs=Path(lp['logs']);logs.mkdir();tmp=root/'tmp';tmp.mkdir();cache=root/'cache';cache.mkdir();env=execution_environment(root)
    started=time.monotonic();state='stopped';reason=None
    def interrupted(signum,frame):raise RuntimeError('wrapper signal '+str(signum))
    for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupted)
    try:
        # Shared-system metadata only, no torch/model/GT access before the isolated runtime exists.
        import e029_linux_environment as environment
        environment.admission(cfg,proc)
        catalogue=read(DOC/'taobo_transfer_lock.json')
        private=Path(lp['private']);cat=private/'private_catalogue.json'
        if sha(cat)!=catalogue['catalogue_sha256']:raise ValueError('private catalogue identity')
        migration=__import__('e029_migration');rows=migration.validate_catalogue(read(cat))
        actual={v.relative_to(private).as_posix() for v in private.rglob('*') if v.is_file()}
        if actual!={r['relative'] for r in rows}|{'private_catalogue.json'}:raise ValueError('exact509 private inventory')
        for r in rows:
            f=private/r['relative']
            if f.is_symlink() or not f.resolve().is_relative_to(private) or sha(f)!=r['sha256']:raise ValueError('private raw-byte identity')
        invoke(['/usr/bin/python3','-I',str(HERE/'e029_linux_bootstrap.py')],'bootstrap',cfg,logs,env)
        trusted_runtime=sha(lp['runtime_lock']);shutil.copyfile(lp['runtime_lock'],logs/'runtime_lock.json')
        def sealed(command):return ['/usr/bin/python3','-I',str(HERE/'e029_runtime_exec.py'),'--lock',lp['runtime_lock'],'--expected-sha256',trusted_runtime,'--',*command]
        py=cfg['producer']['python'];verify_source(source,args.manifest_sha256)
        # Imports verify versions/device; zero model/GT/sample probe.
        preflight="import sys;sys.path.insert(0,"+repr(str(HERE))+");import e029_linux_environment as e,json;cfg=json.load(open("+repr(str(DOC/'taobo_run_config.json'))+"));e.production_environment(cfg);print('Linux exact runtime verified; zero model/GT')"
        invoke(sealed([py,'-I','-c',preflight]),'preflight',cfg,logs,env)
        cmd=[py,str(HERE/'run.py'),'--profile','taobo','--run',lp['run'],'--paths',str(DOC/'taobo_private_paths.json'),'--reviewed-commit',args.reviewed_commit,'--manifest-sha256',args.manifest_sha256,'--approval-file',str(args.approval),'--runtime-lock-sha256',trusted_runtime]
        invoke(sealed(cmd),'controller',cfg,logs,env);state='completed'
    except BaseException as e:reason=repr(e)
    finally:
        try:write(logs/'wrapper_status.json',dict(state=state,reason=reason,elapsed_seconds=time.monotonic()-started,wall_seconds=None,no_retry=True,source_commit=args.reviewed_commit,manifest=args.manifest_sha256))
        except BaseException as e:print('status persistence failed '+repr(e),file=sys.stderr)
    # Packaging reuses the exact source reader and no budget extension/second scientific run.
    invoke(['/usr/bin/python3','-I',str(HERE/'pack.py'),'--run',lp['run'],'--logs',lp['logs'],'--manifest',str(manifest),'--output',lp['archive']],'package',cfg,logs,env)
    if state!='completed':raise RuntimeError(reason)
if __name__=='__main__':main()
