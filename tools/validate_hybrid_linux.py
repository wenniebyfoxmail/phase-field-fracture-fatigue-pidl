"""Bounded Linux admission: real controller, saved full mesh, one cost cycle.

No training or test/holdout access. The five-step cost cycle is diagnostic,
never appended to complete-trajectory labels. First physical failure stops.
"""
import argparse
import hashlib
import select
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


CARD_RELATIVE='docs/research/S04/hybrid_constrained_design_20261019/execution_validation_card_v3.json'


def verify_contract(a):
    # Pure stdlib: bind the supplied card and paths BEFORE numerical imports,
    # root creation, CPU work or any test process.
    card=json.loads(a.card.read_text());manifest=json.loads(a.package.read_text())
    digest=hashlib.sha256(a.card.read_bytes()).hexdigest()
    if manifest['files'].get(CARD_RELATIVE)!=digest:raise RuntimeError('validation card not bound to source manifest')
    if hashlib.sha256(json.dumps(manifest['files'],sort_keys=True,allow_nan=False).encode()).hexdigest()!=manifest['artifact_id']:
        raise RuntimeError('invalid validation source artifact')
    for f,h in manifest['files'].items():
        if Path(f).is_absolute() or '..' in Path(f).parts or hashlib.sha256((a.code/f).read_bytes()).hexdigest()!=h:
            raise RuntimeError('validation source bytes differ')
    v=card['validation_contract']
    if card.get('execution_enabled') is not False or card['authority'].get('validation_permitted') is not True:
        raise RuntimeError('validation-only authority missing')
    if a.root.resolve()!=Path(v['root']) or a.root.parent!=Path('/mnt/data2/drtao/wennie'):
        raise RuntimeError('validation root differs')
    if (card['base_load_cycle']!=[.02999988,.05999988,.08999988,.11999988,0.] or card['solver']['wall_seconds']!=120
            or v['wall_cap_seconds']!=1800 or v['max_extra_diagnostic_substeps']!=5 or v['operator_tolerance']!=1.e-10):
        raise RuntimeError('frozen validation path/caps differ')
    return card


def cpu_environment(root):
    # Affinity precedes NumPy/OpenBLAS/torch imports and child creation.
    available=sorted(os.sched_getaffinity(0))
    if len(available)<16:raise RuntimeError('insufficient CPU pool')
    os.sched_setaffinity(0,set(available[:16]))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='16'
    os.environ['CUDA_VISIBLE_DEVICES']=''
    for key,name in (('TMPDIR','tmp'),('XDG_CACHE_HOME','cache'),('TORCH_EXTENSIONS_DIR','jitcache')):
        d=root/name;d.mkdir(parents=True,exist_ok=True);os.environ[key]=str(d)


def parent_safeguard(gated=False):
    import ctypes
    expected=int(os.environ['HYBRID_SUPERVISOR_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0 or os.getppid()!=expected:
        raise RuntimeError('parent-death safeguard unavailable')
    if gated:
        fd=int(os.environ['HYBRID_START_FD'])
        if os.read(fd,1)!=b'1':raise RuntimeError('outer guardian gate not ready')
        os.close(fd)


def helper(mode):
    import ctypes
    expected=int(os.environ['HYBRID_SUPERVISOR_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0 or os.getppid()!=expected:
        raise RuntimeError('parent-death safeguard unavailable')
    gate=int(os.environ['HYBRID_START_FD'])
    if os.read(gate,1)!=b'1':raise RuntimeError('no controller gate')
    os.close(gate)
    from hybrid_guard_client import notify
    notify('step_start',1)
    if mode=='hang':time.sleep(150.)
    elif mode=='success':time.sleep(.05);notify('step_done',1)
    elif mode!='incomplete':raise ValueError(mode)


def control_case(mode,root,code,card):
    from run_hybrid_producer import run_owned_worker
    root.mkdir();archive=root/'archive';archive.mkdir()
    env=dict(os.environ,HYBRID_SUPERVISOR_PID=str(os.getpid()))
    usage={};started=time.perf_counter();error=None
    spec=dict(id='controller_'+mode,kind='control',gpu=False,wall_seconds=200 if mode=='hang' else 90)
    try:
        run_owned_worker([sys.executable,str(Path(__file__).resolve()),'--helper',mode],code,env,root/'worker.log',spec,card,root,archive,
                         dict(start_monotonic=started,gpu_seconds=0.),usage=usage)
    except Exception as exc:error=str(exc)
    result=dict(mode=mode,error=error,usage=usage,wall_seconds=time.perf_counter()-started)
    expected={'success':None,'incomplete':'incomplete step completion at worker exit','hang':'physical-substep120s deadline'}[mode]
    guard=usage.get('deadline_guard',{})
    result['passed']=(error is None and guard.get('reason') is None) if expected is None else (error is not None and guard.get('reason')==expected)
    if mode=='hang':result['passed'] &= 120.<=result['wall_seconds']<=140.
    return result


def parent_death(root,code,card_path):
    import psutil
    root.mkdir();childroot=root/'owned_parent'
    owned={};cleanup=[];proc=None
    def bind(pid):
        if pid not in owned:
            try:owned[pid]=os.pidfd_open(pid)
            except ProcessLookupError:pass
    def alive(fd):return not bool(select.select([fd],[],[],0)[0])
    try:
        with (root/'parent.log').open('w') as log:
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--parent-only','--root',str(childroot),'--code',str(code),'--card',str(card_path)],
                  env=dict(os.environ,HYBRID_SUPERVISOR_PID=str(os.getpid())),start_new_session=True,stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+15.;worker=guardian=None
        while time.monotonic()<deadline:
            try:
                for child in psutil.Process(proc.pid).children(recursive=True):bind(child.pid)
            except psutil.NoSuchProcess:pass
            p=childroot/'phases.jsonl'
            if p.exists():
                try:
                    r=json.loads(p.read_text().splitlines()[-1]);worker=r['pid'];guardian=r['guardian_pid']
                    if worker not in owned or guardian not in owned:raise RuntimeError('controller descendants not independently bound')
                    break
                except (ValueError,IndexError,KeyError):pass
            if proc.poll() is not None:raise RuntimeError('parent control exited before admission')
            time.sleep(.05)
        if worker is None:raise RuntimeError('parent control startup timeout')
        proc.kill();proc.wait(timeout=5)
        deadline=time.monotonic()+15.
        while time.monotonic()<deadline and any(alive(fd) for fd in owned.values()):time.sleep(.05)
        # Record the TEST outcome before fallback cleanup; cleanup cannot turn
        # a failed death-signal/pidfd test into a passing observation.
        observed={pid:alive(fd) for pid,fd in owned.items()}
        report=childroot/'guard_controller_hang.json'
        receipt=json.loads(report.read_text()) if report.exists() else None
        result=dict(passed=not any(observed.values()) and receipt is not None and receipt['reason']=='supervisor exited',
                    parent_pid=proc.pid,worker_pid=worker,guardian_pid=guardian,observed_running=observed,guard=receipt)
        return result
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill();proc.wait(timeout=5)
        for pid,fd in owned.items():
            try:
                if alive(fd):
                    signal.pidfd_send_signal(fd,signal.SIGTERM)
                    if not select.select([fd],[],[],5)[0]:signal.pidfd_send_signal(fd,signal.SIGKILL)
                    if not select.select([fd],[],[],5)[0]:raise RuntimeError('owned benign test process survived cleanup')
                    cleanup.append(pid)
            except ProcessLookupError:pass
            finally:os.close(fd)
        if 'result' in locals():result['fallback_cleanup_pids']=cleanup


def full_mesh(inputs,out):
    import numpy as np
    from damage_conditioned_equilibrium import assemble_amor_stiffness
    from hybrid_inputs import load_backend,read_manifest
    from replay_hybrid_native_operators import replay
    from hybrid_producer_common import write_json
    started=time.perf_counter();backend,old,dofs,bc=load_backend(inputs,read_manifest(inputs/'inputs.json'))
    rows=[]
    for step in range(1,6):
        t=time.perf_counter()
        with np.load(inputs/f'seen_s{step}.npz',allow_pickle=False) as z:
            cached=backend.mechanics_workspace.assemble(z['d'],z['u'])
            legacy=assemble_amor_stiffness(backend.kin,z['d'],z['u'],**backend.material)
            delta=cached-legacy
            rel=float(np.linalg.norm(delta.data)/max(np.linalg.norm(legacy.data),np.finfo(float).eps))
            force=float(np.max(np.abs(cached@z['u']-legacy@z['u'])))
            row=dict(step=step,matrix_relative_frobenius=rel,force_absolute_inf=force,passed=bool(np.isfinite([rel,force]).all() and max(rel,force)<=1.e-10),wall_seconds=time.perf_counter()-t)
            rows.append(row);write_json(out/'full_mesh_progress.json',dict(rows=rows))
            if not row['passed']:raise RuntimeError('full-grid cached/legacy operator parity failed')
    reuse_bytes=sum(a.nbytes for a in backend.mechanics_workspace.dev+backend.mechanics_workspace.vol)+sum(getattr(backend.mechanics_workspace,k).nbytes for k in ('scatter','indptr','indices'))
    del backend
    original=replay(inputs)
    result=dict(passed=all(x['passed'] for x in rows) and original['passed'],rows=rows,tolerance=1.e-10,replay=original,workspace_array_bytes=reuse_bytes,wall_seconds=time.perf_counter()-started,new_fem_solves=0,training_updates=0)
    write_json(out/'full_mesh.json',result)
    if not result['passed']:raise RuntimeError('native saved-field replay failed')
    return result


def main(a):
    if not sys.platform.startswith('linux'):raise RuntimeError('Linux producer only')
    if a.parent_only:
        return control_case('hang',a.root.resolve(),a.code.resolve(),json.loads(a.card.read_text()))
    if not a.outer_worker:raise RuntimeError('validation driver requires independent outer controller and gate')
    card=verify_contract(a)
    root=a.root.resolve();code=a.code.resolve()
    if root.exists():raise FileExistsError('validation root already exists; no automatic retry')
    root.mkdir();cpu_environment(root)
    from hybrid_inputs import read_manifest,sha256
    from hybrid_producer_common import verify_package,write_json
    from run_hybrid_producer import host_admission,run_owned_worker
    import psutil,resource,socket,importlib
    start=time.perf_counter();cpu0=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(passed=False,started_epoch=time.time(),source_artifact=read_manifest(a.package)['artifact_id'],card_sha256=sha256(a.card),training_updates=0,diagnostic_substeps_max=5,gpu_seconds=0.)
    def timeout(sig,frame):raise RuntimeError('30minute validation host wall cap')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(1800)
    try:
        verify_package(code,read_manifest(a.package))
        if sha256(a.inputs/'inputs.json')!=card['inputs_sha256']:raise RuntimeError('input manifest mismatch')
        result['host']=host_admission(card,Path(card['run_root']),Path(card['archive_root']))
        result['hostname']=socket.gethostname()
        result['runtime']={n:getattr(importlib.import_module(n),'__version__','unknown') for n in card['runtime_expected']}
        if result['runtime']!=card['runtime_expected']:raise RuntimeError('producer runtime mismatch')
        result['controls']=[]
        for mode in ('success','incomplete','hang'):
            r=control_case(mode,root/mode,code,card);result['controls'].append(r);write_json(root/'progress.json',result)
            if not r['passed']:raise RuntimeError('actual controller case failed: '+mode)
        result['parent_death']=parent_death(root/'parent_death',code,a.card)
        write_json(root/'progress.json',result)
        if not result['parent_death']['passed']:raise RuntimeError('actual parent-death control failed')
        result['full_mesh']=full_mesh(a.inputs,root)
        # The exact trajectory worker writes labels/commits/trace just as in the
        # future producer, but only one diagnostic cycle, never fit or resume.
        diagnostic=json.loads(json.dumps(card));spec=dict(id='cost_cycle',kind='trajectory',gpu=False,wall_seconds=900,cycles=1,amplitude_multiplier=.8,role='labels',initializer='previous')
        diagnostic['phases']=[spec]
        dp=root/'diagnostic_card.json';write_json(dp,diagnostic)
        archive=root/'cost_archive';archive.mkdir();out=root/'cost_run';out.mkdir()
        env=dict(os.environ,HYBRID_SUPERVISOR_PID=str(os.getpid()))
        usage={};tick=time.perf_counter()
        try:
            run_owned_worker([sys.executable,'-u',str(code/'tools/hybrid_producer_worker.py'),'--card',str(dp),'--phase','cost_cycle','--inputs',str(a.inputs),'--out',str(out),'--archive',str(archive)],code,env,out/'worker.log',spec,card,out,archive,dict(start_monotonic=start,gpu_seconds=0.),usage=usage)
        finally:
            usage['wall_seconds']=time.perf_counter()-tick;result['cost_cycle_usage']=usage;write_json(root/'progress.json',result)
        summary=read_manifest(archive/'cost_cycle/summary.json')
        result['cost_cycle_summary']=summary
        result['cost_cycle_steps']=[json.loads(line) for line in (archive/'cost_cycle/events.jsonl').read_text().splitlines() if '"total_step_wall_seconds"' in line]
        if not summary['completed'] or summary['states']!=5:raise RuntimeError('diagnostic cycle incomplete')
        result['passed']=True
    except BaseException as exc:
        result['failure']=str(exc);raise
    finally:
        signal.alarm(0);cpu=resource.getrusage(resource.RUSAGE_CHILDREN);own=resource.getrusage(resource.RUSAGE_SELF)
        result.update(wall_seconds=time.perf_counter()-start,cpu_seconds_children=cpu.ru_utime+cpu.ru_stime-cpu0.ru_utime-cpu0.ru_stime,cpu_seconds_self=own.ru_utime+own.ru_stime,peak_self_rss_bytes=own.ru_maxrss*1024,finished_epoch=time.time())
        write_json(root/'admission.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--helper',choices=['success','incomplete','hang']);p.add_argument('--parent-only',action='store_true');p.add_argument('--outer-worker',action='store_true')
    for key in ('root','code','card','inputs','package'):p.add_argument('--'+key,type=Path)
    a=p.parse_args()
    if a.helper:helper(a.helper)
    else:
        if a.outer_worker or a.parent_only:parent_safeguard(gated=a.outer_worker)
        main(a)
