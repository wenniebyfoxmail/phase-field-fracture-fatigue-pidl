"""Single fresh measurement, exact authority, gated worker and pidfd watchdog.
No reconnect/resume/retry, no candidate/witness/optimization path.
"""
import argparse,json,os,signal,socket,subprocess,sys,time
from pathlib import Path
from control import bytes_under,consume_claim,digest,seal_outputs,stop_owned,verify_package,wait_guard_ready,write_json
from launch import host_check,gpu_snapshot,resource_check,controller_gate,process_tree


def checked_argv(argv):
    sizes=[len(x.encode())+1 for x in argv]
    if max(sizes)>16384 or sum(sizes)>65536:raise RuntimeError('command exceeds16KiB single/64KiB total argv')
    return argv


def validate(card,authority,manifest_sha,now=None):
    now=time.time() if now is None else now
    if not (authority.get('approved_by')=='human_delegated_HQ' and authority.get('execute_one_frozen_pair_completion') is True
        and authority.get('package_sha256')==manifest_sha and authority.get('run_id')==card['run_id']
        and authority.get('family')==card['family'] and authority.get('authority_ref')):raise RuntimeError('exact new measurement authority missing')
    if card.get('mode')!='frozen_completion_only' or card.get('execution_enabled') is not False:raise RuntimeError('closed measurement card required')
    if now>=card['envelope_deadline_epoch'] or card['measurement_seconds']!=300 or card['envelope_seconds']!=1800:raise RuntimeError('expired/changed time envelope')
    if card['work_caps']['energy_force_field']!=250 or card['work_caps']['head_assembly']!=30 or card['work_caps']['svd']!=0:raise RuntimeError('changed scientific work caps')
    if card['mechanical_max_seconds']!=90 or authority.get('mechanical_max_seconds')!=90:raise RuntimeError('mechanical90 envelope required')
    limits=card['resource_limits_bytes'];G=1024**3
    if card['work_caps']['Qv']!=2 or card['work_caps']['hidden_jvp']!=8 or card['work_caps']['hidden_vjp']!=8:raise RuntimeError('derivative caps differ')
    if card['science']['arms']!=['frozen_constant','frozen_zero'] or card['work_caps']['native_tangent']!=0:raise RuntimeError('native recomputation forbidden')
    if limits!={'host_RSS':16*G,'GPU_allocated':16*G,'GPU_reserved':16*G,'fresh_root_outputs':8*G}:raise RuntimeError('resource envelope differs')


def worker(root,card):
    from worker import gate
    gate()  # before numerical imports/loading/CUDA
    import warnings
    warnings.simplefilter('error')
    from telemetry import Reporter
    archive=Path(card['archive_root']);reporter=Reporter(archive/'telemetry.json',[root,archive],card['resource_limits_bytes'])
    reporter.start();sock=socket.socket(fileno=int(os.environ['E011_GUARD_FD']))
    try:
        here=root/'code/tools/s04_e011_analysis';sys.path.insert(0,str(here))
        from profiled_residual_branch_measurement import run
        result=run(card,root,archive,reporter,float(os.environ['E011_STARTED']))
        reporter.ratio();reporter.close()
        write_json(archive/'worker_terminal.json',dict(status='FROZEN_PAIR_COMPLETE_NO_OPTIMIZATION',run_id=card['run_id'],arms=len(result['arms'])))
        sock.send(json.dumps(dict(event='step_done',step=1,finished=time.monotonic())).encode())
    except BaseException as err:
        try:write_json(archive/'worker_failure.json',dict(type=type(err).__name__,message=str(err),retry_allowed=False))
        finally:
            try:reporter.close()
            except BaseException:pass
        raise
    finally:sock.close()


def execute(root,authority_path,authority_sha,deadline_epoch):
    def interrupt(sig,frame):raise TimeoutError('whole-task absolute deadline/signal')
    signal.signal(signal.SIGALRM,interrupt);signal.signal(signal.SIGTERM,interrupt)
    signal.setitimer(signal.ITIMER_REAL,max(.01,deadline_epoch-time.time()-10))
    root=Path(root).resolve();manifest=json.loads((root/'package_manifest.json').read_text());verify_package(root,manifest)
    card=json.loads((root/'execution_card.json').read_text());authority=json.loads(Path(authority_path).read_text())
    if digest(authority_path)!=authority_sha:raise RuntimeError('authority hash differs')
    validate(card,authority,digest(root/'package_manifest.json'))
    if deadline_epoch!=card['envelope_deadline_epoch']:raise RuntimeError('outer/card absolute deadline differs')
    if root!=Path(card['run_root']) or not sys.platform.startswith('linux'):raise RuntimeError('exact Linux producer root required')
    claim=Path(card['family_claim']);claim.parent.mkdir(exist_ok=True);consume_claim(claim,authority_sha,card['run_id'])
    archive=Path(card['archive_root']);child=guardian=None;left=right=None;fds=[];usage={};reason=None;gate_opened=False
    try:
        host_check(card,root,archive)
        if not (0<=time.monotonic()-authority['mechanical_started_monotonic']<=90 and authority['mechanical_checks']<=2):raise RuntimeError('mechanical zero-start budget')
        admission=gpu_snapshot(card)
        if admission['free_mib']<20*1024:raise RuntimeError('need16GiB cap plus4GiB initial physical margin')
        cpus=sorted(os.sched_getaffinity(0))[:4];os.sched_setaffinity(0,cpus)
        archive.mkdir()
        for name in ['tmp','cache','.jitcache']:(root/name).mkdir()
        started=time.monotonic();absolute=min(started+300,started+card['envelope_deadline_epoch']-time.time()-30)
        if absolute-started<100:raise RuntimeError('insufficient remaining whole-task budget for panel')
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        start_r,start_w=os.pipe();ready_r,ready_w=os.pipe();fds=[start_r,start_w,ready_r,ready_w]
        env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=card['producer']['gpu_uuid'],CUDA_DEVICE_ORDER='PCI_BUS_ID',PIDL_ARCHIVE_DIR=str(archive),
            TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),TORCH_EXTENSIONS_DIR=str(root/'.jitcache'),MPLCONFIGDIR=str(root/'cache/mpl'),
            PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
            E011_SUPERVISOR_PID=str(os.getpid()),E011_START_FD=str(start_r),E011_GUARD_FD=str(right.fileno()),E011_STARTED=str(started))
        cmd=[sys.executable,'-B',str(root/'code/tools/s04_e011_execution/frozen_completion_launch.py'),'--worker','--package',str(root)]
        with (root/'worker.log').open('xb') as log,(root/'guardian.log').open('xb') as glog:
            child=subprocess.Popen(checked_argv(cmd),cwd=root/'code',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(start_r,right.fileno()))
            gcmd=[sys.executable,'-B',str(root/'code/tools/s04_e011_execution/deadline_guard.py'),'--worker',str(child.pid),'--supervisor',str(os.getpid()),
                '--fd',str(left.fileno()),'--deadline',str(absolute),'--step-seconds','300','--phase-seconds-json','[300]',
                '--report',str(root/'deadline_guard.json'),'--ready-fd',str(ready_w)]
            guardian=subprocess.Popen(checked_argv(gcmd),cwd=root/'code',env=env,stdin=subprocess.DEVNULL,stdout=glog,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(left.fileno(),ready_w))
            os.close(ready_w);fds.remove(ready_w);wait_guard_ready(ready_r)
            # Still gated. Fresh no-conflict check is part of the same second mechanical batch.
            admission=gpu_snapshot(card)
            if time.monotonic()-authority['mechanical_started_monotonic']>90:raise RuntimeError('mechanical allowance exhausted before gate')
            write_json(root/'launch_receipt.json',dict(run_id=card['run_id'],source_commit=manifest['source_commit'],package_sha256=digest(root/'package_manifest.json'),
                worker_pid=child.pid,guardian_pid=guardian.pid,command=cmd,started_monotonic=started,deadline=absolute,
                source_branch=manifest['source_branch'],admission=admission,CPU_affinity=cpus,authority=authority,log=str(root/'worker.log')))
            right.send(json.dumps(dict(event='step_start',step=1,started=started)).encode());os.write(start_w,b'1');gate_opened=True
            last_gpu=0.;seen=False
            while child.poll() is None:
                if guardian.poll() is not None:raise RuntimeError('guardian exited while worker alive')
                if time.monotonic()>=absolute:raise RuntimeError('measurement300s/whole-envelope deadline')
                row,seen=resource_check(child,root,archive,dict(resource_limits_bytes=card['resource_limits_bytes']),started,seen)
                tree_rss=process_tree(int(os.environ['E011_OUTER_PID']))
                extra_files=[Path(card['family_claim'])]+[root.parent/'.s04_e011_profiled_hidden_claims'/(root.name+suffix) for suffix in ['.bootstrap.stdout','.bootstrap.stderr','.outer_return.json']]
                outside=sum(p.stat().st_size for p in extra_files if p.is_file())
                row['outer_tree_rss']=tree_rss;row['owned_external_bytes']=outside
                if tree_rss>card['resource_limits_bytes']['host_RSS'] or row['task_bytes']+outside>card['resource_limits_bytes']['fresh_root_outputs']:raise RuntimeError('whole owned tree RSS/storage cap')
                usage['peak_tree_rss']=max(usage.get('peak_tree_rss',0),tree_rss);usage['latest']=row
                if time.monotonic()-last_gpu>=2:
                    usage['gpu']=gpu_snapshot(card,{child.pid});last_gpu=time.monotonic()
                    if usage['gpu']['free_mib']<4096:raise RuntimeError('physical GPU4GiB spare margin')
                write_json(root/'monitor.json',dict(elapsed=time.monotonic()-started,usage=usage));time.sleep(.2)
            child.wait(timeout=1);guardian.wait(timeout=5)
            terminal=json.loads((archive/'worker_terminal.json').read_text()) if (archive/'worker_terminal.json').exists() else {}
            audit=json.loads((root/'deadline_guard.json').read_text())
            if child.returncode or guardian.returncode or audit.get('reason') or terminal.get('status')!='FROZEN_PAIR_COMPLETE_NO_OPTIMIZATION':raise RuntimeError('measurement worker/guard failed or incomplete; inspect primary worker_failure')
    except BaseException as err:reason=type(err).__name__+': '+str(err)
    finally:
        if child is not None:stop_owned(child)
        if guardian is not None:
            try:guardian.wait(timeout=2)
            except subprocess.TimeoutExpired:stop_owned(guardian)
        for fd in fds:os.close(fd)
        for sock in [left,right]:
            if sock is not None:sock.close()
        result=dict(status='MEASUREMENT_COMPLETE' if reason is None else 'STOPPED_NO_RETRY',reason=reason,gate_opened=gate_opened,usage=usage,
            worker_exit=None if child is None else child.returncode,guardian_exit=None if guardian is None else guardian.returncode)
        write_json(root/'controller_terminal.json',result)
        if archive.exists():seal_outputs({'run':root,'archive':archive},root/'export_manifest.json',card['run_id'],result['status'],
            [('run',name) for name in ['outer_guard.json','outer_guard.log','outer_controller.log']])
        signal.setitimer(signal.ITIMER_REAL,0)
    return result


def outer(root,authority_path,authority_sha,deadline_epoch):
    """Original pidfd architecture: independently bound controller AND worker.

    The controller cannot hash/load until this global guardian is armed. A
    second guardian in execute independently bounds the numerical worker600s.
    """
    root=Path(root);controller=guardian=None;left=right=None;fds=[];error=None
    if not sys.platform.startswith('linux'):raise RuntimeError('Linux producer only')
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    def interrupt(sig,frame):raise TimeoutError('outer whole-task deadline/signal')
    signal.signal(signal.SIGALRM,interrupt);signal.signal(signal.SIGTERM,interrupt)
    signal.setitimer(signal.ITIMER_REAL,max(.01,deadline_epoch-time.time()-5))
    try:
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        gate_r,gate_w=os.pipe();ready_r,ready_w=os.pipe();fds=[gate_r,gate_w,ready_r,ready_w]
        env=os.environ.copy();env.update(E011_OUTER_PID=str(os.getpid()),E011_CONTROLLER_START_FD=str(gate_r),PYTHONDONTWRITEBYTECODE='1')
        cmd=[sys.executable,'-B',str(root/'code/tools/s04_e011_execution/frozen_completion_launch.py'),'--controller','--package',str(root),
            '--authority',str(authority_path),'--authority-sha256',authority_sha,'--envelope-deadline',str(deadline_epoch)]
        with (root/'outer_controller.log').open('xb') as log,(root/'outer_guard.log').open('xb') as glog:
            controller=subprocess.Popen(checked_argv(cmd),cwd=root/'code',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(gate_r,))
            gcmd=[sys.executable,'-B',str(root/'code/tools/s04_e011_execution/deadline_guard.py'),'--worker',str(controller.pid),
                '--supervisor',str(os.getpid()),'--fd',str(left.fileno()),'--deadline',str(time.monotonic()+max(.01,deadline_epoch-time.time()-20)),
                '--step-seconds','1800','--report',str(root/'outer_guard.json'),'--ready-fd',str(ready_w)]
            guardian=subprocess.Popen(checked_argv(gcmd),cwd=root/'code',env=env,stdin=subprocess.DEVNULL,stdout=glog,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(left.fileno(),ready_w))
            os.close(ready_w);fds.remove(ready_w);wait_guard_ready(ready_r)
            write_json(root/'outer_launch_receipt.json',dict(controller_pid=controller.pid,guardian_pid=guardian.pid,command=cmd,
                absolute_envelope_deadline_epoch=deadline_epoch,guardian_armed_before_hash_or_model=True))
            os.write(gate_w,b'1')
            while controller.poll() is None:
                if guardian.poll() is not None:raise RuntimeError('outer guardian exited before controller')
                time.sleep(.2)
            controller.wait(timeout=1);guardian.wait(timeout=5)
            audit=json.loads((root/'outer_guard.json').read_text())
            if controller.returncode or guardian.returncode or audit.get('reason'):raise RuntimeError('outer controller/guard failure')
    except BaseException as err:error=type(err).__name__+': '+str(err)
    finally:
        if controller is not None:stop_owned(controller)
        if guardian is not None:
            try:guardian.wait(timeout=2)
            except subprocess.TimeoutExpired:stop_owned(guardian)
        for fd in fds:os.close(fd)
        for sock in [left,right]:
            if sock is not None:sock.close()
        result=dict(run_id=root.name,status='STOPPED_NO_RETRY',outer_error=error,controller_pid=None if controller is None else controller.pid)
        if error is None and (root/'controller_terminal.json').exists():result.update(json.loads((root/'controller_terminal.json').read_text()))
        result['export_manifest_sha256']=digest(root/'export_manifest.json') if (root/'export_manifest.json').is_file() else None
        if any((root/name).is_file() and (root/name).stat().st_size>1048576 for name in ['outer_guard.json','outer_guard.log','outer_controller.log']):raise RuntimeError('bounded postexit log exceeds1MiB')
        result['postexit_files']=[dict(root='run',path=name,bytes=(root/name).stat().st_size,sha256=digest(root/name)) for name in
            ['outer_guard.json','outer_guard.log','outer_controller.log'] if (root/name).is_file()]
        # Return receipt is outside both sealed roots, as in the old verifier.
        receipt=root.parent/'.s04_e011_profiled_hidden_claims'/(root.name+'.outer_return.json')
        receipt.parent.mkdir(exist_ok=True)
        tmp=receipt.with_name(receipt.name+'.'+str(os.getpid())+'.tmp')
        with tmp.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.flush();os.fsync(stream.fileno())
        try:os.link(tmp,receipt)
        finally:tmp.unlink()
        signal.setitimer(signal.ITIMER_REAL,0)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--package',type=Path,required=True);ap.add_argument('--worker',action='store_true');ap.add_argument('--controller',action='store_true');ap.add_argument('--authority');ap.add_argument('--authority-sha256');ap.add_argument('--envelope-deadline',type=float);a=ap.parse_args()
    if a.worker:
        worker(a.package,json.loads((a.package/'execution_card.json').read_text()))
    elif a.controller:
        controller_gate();print(json.dumps(execute(a.package,a.authority,a.authority_sha256,a.envelope_deadline)))
    else:print(json.dumps(outer(a.package,a.authority,a.authority_sha256,a.envelope_deadline)))
