"""Closed, host-local E011 launcher. --check does not inspect host/GPU/inputs.

No SSH/scp/reconnection/resume/retry implementation exists. --execute requires
one exact human authority overlay and consumes the family claim before admission.
"""
import argparse,csv,io,json,math,os,platform,pwd,signal,socket,subprocess,sys,time
from pathlib import Path
from control import (FAMILY,RESERVE,SECONDS,PHASES,allowed_phases,bind_attempt_clock,bytes_under,consume_claim,digest,
    seal_outputs,stop_owned,validate_authority,validate_telemetry,verify_package,wait_guard_ready,write_json)


def command(args):return subprocess.check_output(args,text=True,timeout=2).strip()


def gpu_snapshot(card,allowed=()):
    p=card['producer'];rows=list(csv.reader(io.StringIO(command(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu,memory.total','--format=csv,noheader,nounits']))))
    selected=next((r for r in rows if r[1].strip()==p['gpu_uuid']),None)
    if selected is None or int(selected[0])!=p['gpu_index']:raise RuntimeError('bound GPU index/UUID changed')
    apps=list(csv.reader(io.StringIO(command(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader,nounits']))))
    owned=[]
    for row in apps:
        if len(row)==3 and row[1].strip()==p['gpu_uuid']:
            if int(row[0]) not in allowed:raise RuntimeError('foreign/unknown selected-GPU process; stop only our worker')
            owned.append(dict(pid=int(row[0]),used_mib=float(row[2])))
    admission=card.get('admission_revision',{})
    required=admission.get('required_initial_free_VRAM_bytes',28*1024**3)
    if admission and len(selected)!=5:raise RuntimeError('physical GPU capacity unavailable')
    free_mib=float(selected[2]);util=float(selected[3]);total_mib=float(selected[4]) if len(selected)==5 else None
    values=[free_mib,util]+([] if total_mib is None else [total_mib])
    if not all(math.isfinite(v) for v in values) or free_mib<0 or not 0<=util<=100 or (total_mib is not None and (total_mib<=0 or free_mib>total_mib)):raise RuntimeError('nonfinite/invalid GPU capacity telemetry')
    if total_mib is not None and total_mib*1024**2<required:raise RuntimeError('GPU admission configuration exceeds physical GPU capacity')
    if not allowed and (free_mib*1024**2<required or util>=10):raise RuntimeError('GPU admission capacity/activity failure')
    return dict(index=int(selected[0]),uuid=p['gpu_uuid'],free_mib=free_mib,utilization=util,total_mib=total_mib,required_initial_free_bytes=required,owned=owned)


def host_check(card,root,archive):
    if platform.system()!='Linux' or socket.gethostname()!=card['producer']['hostname'] or pwd.getpwuid(os.geteuid()).pw_name!='drtao':raise RuntimeError('exact Taobo producer only; Mac execution forbidden')
    if not Path('/mnt/data2').is_mount():raise RuntimeError('canonical data2 mount missing')
    for path,parent in [(root,Path('/mnt/data2/drtao/wennie')),(archive,Path('/mnt/data2/drtao/pidl_archives'))]:
        if path.parent!=parent or path.name!=card['run_id'] or path.is_symlink():raise RuntimeError('fresh attributable root differs')
    mem={r.split(':')[0]:int(r.split()[1]) for r in Path('/proc/meminfo').read_text().splitlines()}
    if mem['MemAvailable']<32*1024**2:raise RuntimeError('less than original32GiB available host RAM')
    stat=os.statvfs('/mnt/data2')
    if stat.f_bavail*stat.f_frsize<24*1024**3:raise RuntimeError('insufficient full output allowance on data2')
    if archive.exists() or any((root/n).exists() for n in ['launch_receipt.json','worker.log','controller_terminal.json','inputs']):raise RuntimeError('used/staged scientific attempt; no resume')


def process_tree(pid):
    # Same /proc aggregate-RSS pattern as E011 PC16 guard; only root descendants.
    rows={}
    for p in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields=p.read_text().rsplit(')',1)[1].split();rows[int(p.parent.name)]=(int(fields[1]),int(fields[21]))
        except (OSError,ValueError,IndexError):continue
    ids={pid}
    while True:
        new={i for i,(parent,_) in rows.items() if parent in ids}
        if new<=ids:break
        ids|=new
    return sum(rows[i][1] for i in ids if i in rows)*os.sysconf('SC_PAGE_SIZE')


def resource_check(child,root,archive,science,started,seen_active=False):
    limits=science['resource_limits_bytes'];rss=process_tree(child.pid);total=bytes_under(root)+bytes_under(archive)
    if rss>limits['host_RSS'] or total>limits['fresh_root_outputs']:raise RuntimeError('external RSS/storage cap')
    telemetry=archive/'telemetry.json'
    if not telemetry.exists():
        if time.monotonic()-started>5:raise RuntimeError('worker telemetry absent')
        return dict(peak_tree_rss=rss,task_bytes=total,telemetry=None),seen_active
    row=json.loads(telemetry.read_text());validate_telemetry(row,time.monotonic(),limits,allow_boot=not seen_active)
    return dict(peak_tree_rss=rss,task_bytes=total,telemetry=row),seen_active or row['cuda_state']=='active'


def managed(root,archive,card,science,authority,started,admit):
    """Reuse pidfd guardian + ready pipe + start gate, one persistent worker."""
    child=guardian=None;left=right=None;fds=[];usage={};reason=None
    names=allowed_phases(authority['scope']);scope=authority['scope'];code=root/'code'
    phases=[SECONDS[PHASES.index(n)]-RESERVE for n in names]
    report=root/'deadline_guard.json';gate_opened=False;last_gpu=-1.;seen_active=False
    try:
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        start_r,start_w=os.pipe();ready_r,ready_w=os.pipe();fds=[start_r,start_w,ready_r,ready_w]
        env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=card['producer']['gpu_uuid'],PIDL_ARCHIVE_DIR=str(archive),
            TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),TORCH_EXTENSIONS_DIR=str(root/'.jitcache'),MPLCONFIGDIR=str(root/'cache/mpl'),
            PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
            E011_SUPERVISOR_PID=str(os.getpid()),E011_START_FD=str(start_r),E011_GUARD_FD=str(right.fileno()),
            E011_STARTED=str(started),E011_SCOPE=scope,E011_PACKAGE=str(root))
        worker=[sys.executable,'-B',str(code/'tools/s04_e011_execution/worker.py')]
        with (root/'worker.log').open('xb') as log,(root/'guardian.log').open('xb') as glog:
            globalfd=int(env['E011_GLOBAL_GUARD_FD'])
            child=subprocess.Popen(worker,cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,pass_fds=(right.fileno(),start_r,globalfd))
            guardcmd=[sys.executable,'-B',str(code/'tools/s04_e011_execution/deadline_guard.py'),'--worker',str(child.pid),
                '--supervisor',str(os.getpid()),'--fd',str(left.fileno()),'--deadline',str(started+3000-RESERVE),
                '--step-seconds','3000','--phase-seconds-json',json.dumps(phases),'--report',str(report),'--ready-fd',str(ready_w)]
            guardian=subprocess.Popen(guardcmd,cwd=code,env=env,stdout=glog,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(left.fileno(),ready_w))
            os.close(ready_w);fds.remove(ready_w);wait_guard_ready(ready_r)
            right.send(json.dumps(dict(event='step_start',step=1,started=started)).encode())
            # GPU/resource checks happen only AFTER guardian is armed, while
            # worker is still blocked before imports/loading/CUDA.
            admission=admit()
            write_json(root/'launch_receipt.json',dict(run_id=card['run_id'],family=FAMILY,scope=scope,authority=authority,
                child_pid=child.pid,guardian_pid=guardian.pid,command=worker,log=str(root/'worker.log'),
                root=str(root),archive=str(archive),producer=card['producer'],started_monotonic=started,admission=admission,
                guardian_armed_before_gate=True,execution_package_sha256=digest(root/'package_manifest.json')))
            if guardian.poll() is not None or child.poll() is not None:raise RuntimeError('guardian/worker exited before gate')
            os.write(start_w,b'1');gate_opened=True;gated=time.monotonic()
            while child.poll() is None:
                if guardian.poll() is not None:raise RuntimeError('independent guardian exited while worker alive')
                if time.monotonic()>=started+3000-RESERVE:raise RuntimeError('supervisor total reserve deadline')
                row,seen_active=resource_check(child,root,archive,science,gated,seen_active)
                usage['peak_tree_rss']=max(usage.get('peak_tree_rss',0),row['peak_tree_rss']);usage['peak_task_bytes']=max(usage.get('peak_task_bytes',0),row['task_bytes'])
                usage['worker_telemetry']=row['telemetry']
                if time.monotonic()-last_gpu>=2:usage['gpu']=gpu_snapshot(card,{child.pid});last_gpu=time.monotonic()
                write_json(root/'monitor.json',dict(usage=usage,elapsed=time.monotonic()-started))
                time.sleep(.2)
            child.wait(timeout=1);guardian.wait(timeout=5)
            if child.returncode!=0 or guardian.returncode!=0:raise RuntimeError('worker/guardian nonzero exit')
            audit=json.loads(report.read_text());terminal=json.loads((archive/'worker_terminal.json').read_text())
            expected='PREFLIGHT_ONLY_COMPLETE_NOT_SCIENTIFIC_SUCCESS' if scope=='preflight_only' else 'FULL_COMPARISON_COMPLETE'
            if audit.get('reason') is not None or audit.get('last_step')!=len(names) or terminal.get('status')!=expected:raise RuntimeError('incomplete/invalid authorised chain terminal')
            if time.monotonic()-started>3000:raise RuntimeError('late global terminal')
            return dict(status=expected,usage=usage,deadline_guard=audit,gate_opened=gate_opened,exit_code=child.returncode)
    except BaseException as exc:
        reason=type(exc).__name__+': '+str(exc)
        raise
    finally:
        if child is not None:stop_owned(child)
        if guardian is not None:
            try:guardian.wait(timeout=2)
            except subprocess.TimeoutExpired:stop_owned(guardian)
        for fd in fds:os.close(fd)
        for s in [left,right]:
            if s is not None:s.close()
        write_json(root/'managed_exit.json',dict(reason=reason,usage=usage,gate_opened=gate_opened,
            worker_exit=None if child is None else child.returncode,guardian_exit=None if guardian is None else guardian.returncode,
            no_retry=True,no_reconnection=True,elapsed_seconds=time.monotonic()-started))


def load_package(root):
    root=Path(root);manifest=json.loads((root/'package_manifest.json').read_text());verify_package(root,manifest)
    card=json.loads((root/'execution_card.json').read_text())
    if card['family']!=FAMILY or card['execution_enabled'] is not False or card['phase_seconds']!=dict(zip(PHASES,SECONDS)):raise RuntimeError('closed card/frozen phase envelope differs')
    science_path=root/'code'/card['science_card']
    if digest(science_path)!=card['science_card_sha256']:raise RuntimeError('immutable scientific card differs')
    science=json.loads(science_path.read_text())
    if science['total_seconds']!=3000 or science['execution_enabled'] is not False:raise RuntimeError('scientific preparation boundary changed')
    return manifest,card,science


def execute_inner(root,authority_path,authority_sha):
    root=Path(root).resolve();manifest,card,science=load_package(root)
    authority=json.loads(Path(authority_path).read_text());validate_authority(authority,authority_sha,authority_path,card,digest(root/'package_manifest.json'))
    if platform.system()!='Linux':raise RuntimeError('Mac is Dev only; no authority consumption or producer start')
    started=float(os.environ['E011_STARTED']);archive=Path(card['archive_root'])
    status='STOPPED_NO_RETRY';result={}
    def interrupt(signum,frame):raise KeyboardInterrupt('supervisor signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupt)
    try:
        if root!=Path(card['run_root']):raise RuntimeError('exact prepared run root required')
        host_check(card,root,archive);archive.mkdir()
        for name in ['tmp','cache','.jitcache']:(root/name).mkdir()
        result=managed(root,archive,card,science,authority,started,lambda:gpu_snapshot(card))
        status=result['status']
    finally:
        write_json(root/'controller_terminal.json',dict(run_id=card['run_id'],family=FAMILY,status=status,result=result,
            scope=authority['scope'],authority_sha256=authority_sha,source_commit=manifest['source_commit'],
            elapsed_seconds=time.monotonic()-started,retry_allowed=False,SSH_reconnect_allowed=False))
        if archive.exists():seal_outputs({'run':root,'archive':archive},root/'export_manifest.json',card['run_id'],status,POSTEXIT)
    return result


POSTEXIT=(('run','global_guard.json'),('run','global_guard.log'),('run','controller.log'))


def controller_gate():
    import ctypes
    expected=int(os.environ['E011_OUTER_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0 or os.getppid()!=expected:raise RuntimeError('controller parent-death safeguard unavailable')
    fd=int(os.environ['E011_CONTROLLER_START_FD'])
    if os.read(fd,1)!=b'1':raise RuntimeError('global guardian gate denied')
    os.close(fd)


def execute(root,authority_path,authority_sha):
    root=Path(root).resolve();manifest,card,science=load_package(root)
    authority=json.loads(Path(authority_path).read_text());names=validate_authority(authority,authority_sha,authority_path,card,digest(root/'package_manifest.json'))
    if platform.system()!='Linux':raise RuntimeError('Mac is Dev only; no producer execution')
    if root!=Path(card['run_root']):raise RuntimeError('exact candidate root required')
    started=bind_attempt_clock(card,authority,time.monotonic());claim=Path(card['family_claim']);claim.parent.mkdir(exist_ok=True)
    consume_claim(claim,authority_sha,card['run_id'])
    controller=guardian=None;left=right=None;fds=[];status='STOPPED_NO_RETRY';error=None
    phase_limits=[SECONDS[PHASES.index(n)]-10 for n in names]  # outer:10s sealing +10s kill/reap inside original cap
    try:
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        gate_r,gate_w=os.pipe();ready_r,ready_w=os.pipe();fds=[gate_r,gate_w,ready_r,ready_w]
        env=os.environ.copy();env.update(E011_OUTER_PID=str(os.getpid()),E011_CONTROLLER_START_FD=str(gate_r),
            E011_GLOBAL_GUARD_FD=str(right.fileno()),E011_STARTED=str(started),PYTHONDONTWRITEBYTECODE='1')
        cmd=[sys.executable,'-B',str(root/'code/tools/s04_e011_execution/launch.py'),'--internal-controller',
            '--package',str(root),'--authority',str(authority_path),'--authority-sha256',authority_sha]
        with (root/'controller.log').open('xb') as log,(root/'global_guard.log').open('xb') as glog:
            controller=subprocess.Popen(cmd,cwd=root/'code',env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                start_new_session=True,pass_fds=(gate_r,right.fileno()))
            guardian=subprocess.Popen([sys.executable,'-B',str(root/'code/tools/s04_e011_execution/deadline_guard.py'),
                '--worker',str(controller.pid),'--supervisor',str(os.getpid()),'--fd',str(left.fileno()),
                '--deadline',str(started+sum(SECONDS[PHASES.index(n)] for n in names)-10),'--step-seconds','3000',
                '--phase-seconds-json',json.dumps(phase_limits),'--report',str(root/'global_guard.json'),'--ready-fd',str(ready_w)],
                cwd=root/'code',env=env,stdout=glog,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(left.fileno(),ready_w))
            os.close(ready_w);fds.remove(ready_w);wait_guard_ready(ready_r)
            right.send(json.dumps(dict(event='step_start',step=1,started=started)).encode())
            if controller.poll() is not None or guardian.poll() is not None:raise RuntimeError('global guardian/controller exited before gate')
            os.write(gate_w,b'1')
            while controller.poll() is None:
                if guardian.poll() is not None:raise RuntimeError('global guardian lost')
                if time.monotonic()-started>=sum(SECONDS[PHASES.index(n)] for n in names)-10:raise RuntimeError('outer deadline reserve')
                time.sleep(.1)
            controller.wait(timeout=1);guardian.wait(timeout=5)
            audit=json.loads((root/'global_guard.json').read_text())
            expected='PREFLIGHT_ONLY_COMPLETE_NOT_SCIENTIFIC_SUCCESS' if len(names)==1 else 'FULL_COMPARISON_COMPLETE'
            terminal=json.loads((root/'controller_terminal.json').read_text())
            if controller.returncode or guardian.returncode or audit.get('reason') is not None or audit.get('last_step')!=len(names) or terminal.get('status')!=expected:raise RuntimeError('global controller/guard terminal incomplete')
            status=expected
    except BaseException as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        if controller is not None:stop_owned(controller)
        if guardian is not None:
            try:guardian.wait(timeout=2)
            except subprocess.TimeoutExpired:stop_owned(guardian)
        for fd in fds:os.close(fd)
        for endpoint in [left,right]:
            if endpoint is not None:endpoint.close()
    # Only three <=1MiB post-exit administrative files remain. No raw-tree
    # scan/hash after guardians exit. Their SHA is returned out-of-band; the
    # offline verifier requires it in addition to the guarded payload manifest.
    entries=[]
    for label,name in POSTEXIT:
        p=root/name
        if p.exists() and p.stat().st_size<=1024**2:entries.append(dict(root=label,path=name,bytes=p.stat().st_size,sha256=digest(p)))
        else:error=error or 'postexit small receipt missing/oversized';status='STOPPED_NO_RETRY'
    manifest_path=root/'export_manifest.json';manifest_sha=None
    if manifest_path.is_file() and not manifest_path.is_symlink() and manifest_path.stat().st_size<=1024**2:manifest_sha=digest(manifest_path)
    else:status='STOPPED_NO_RETRY';error=error or 'export manifest missing/oversized'
    wall=time.monotonic()-started
    if wall>sum(SECONDS[PHASES.index(n)] for n in names):status='STOPPED_NO_RETRY';error=error or 'late outer exit'
    return dict(run_id=card['run_id'],status=status,error=error,scope=authority['scope'],elapsed_seconds=wall,
        export_manifest_sha256=manifest_sha,
        postexit_files=entries,retry_allowed=False,reconnect_allowed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--check',action='store_true');parser.add_argument('--execute',action='store_true')
    parser.add_argument('--authority',type=Path);parser.add_argument('--authority-sha256');parser.add_argument('--internal-controller',action='store_true',help=argparse.SUPPRESS)
    a=parser.parse_args()
    if a.internal_controller:
        controller_gate();execute_inner(a.package,a.authority,a.authority_sha256)
    elif a.execute:
        if a.check or a.authority is None or a.authority_sha256 is None:raise SystemExit('one exact approved overlay required')
        result=execute(a.package,a.authority,a.authority_sha256);print(json.dumps(result))
        if result['status']=='STOPPED_NO_RETRY':raise SystemExit(1)
    else:
        _,card,_=load_package(a.package);print(json.dumps(dict(package_valid=True,execution_enabled=False,run_id=card['run_id'],host_GPU_inputs_inspected=False)))
