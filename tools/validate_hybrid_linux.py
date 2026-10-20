"""Bounded Linux admission: real controller, saved full mesh, one cost cycle.

No training or test/holdout access. The five-step cost cycle is diagnostic,
never appended to complete-trajectory labels. First physical failure stops.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


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
    proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--parent-only','--root',str(childroot),'--code',str(code),'--card',str(card_path)],
                          start_new_session=True,stdout=(root/'parent.log').open('w'),stderr=subprocess.STDOUT)
    deadline=time.monotonic()+15.;worker=guardian=None
    try:
        while time.monotonic()<deadline:
            p=childroot/'phases.jsonl'
            if p.exists():
                try:r=json.loads(p.read_text().splitlines()[-1]);worker=r['pid'];guardian=r['guardian_pid'];break
                except (ValueError,IndexError,KeyError):pass
            if proc.poll() is not None:raise RuntimeError('parent control exited before admission')
            time.sleep(.05)
        if worker is None:raise RuntimeError('parent control startup timeout')
        # Only this Popen-owned parent is killed. Its real pidfd/death-signal
        # contracts must stop its own harmless sleeping child.
        proc.kill();proc.wait(timeout=5)
        def running(pid):
            try:return psutil.Process(pid).status()!=psutil.STATUS_ZOMBIE
            except psutil.NoSuchProcess:return False
        deadline=time.monotonic()+15.
        while time.monotonic()<deadline and (running(worker) or running(guardian)):time.sleep(.05)
        report=childroot/'guard_controller_hang.json'
        receipt=json.loads(report.read_text()) if report.exists() else None
        return dict(passed=not running(worker) and not running(guardian) and receipt is not None and receipt['reason']=='supervisor exited',
                    parent_pid=proc.pid,worker_pid=worker,guardian_pid=guardian,worker_running=running(worker),guardian_running=running(guardian),guard=receipt)
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
        # Any unexpected survivor is reported; never kill unrelated processes.


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
    from hybrid_inputs import read_manifest,sha256
    from hybrid_producer_common import verify_package,write_json
    from run_hybrid_producer import host_admission,run_owned_worker
    import psutil,resource,socket,importlib
    card=read_manifest(a.card);code=a.code.resolve();root=a.root.resolve()
    if a.parent_only:
        return control_case('hang',root,code,card)
    if root.exists():raise FileExistsError('validation root already exists; no automatic retry')
    root.mkdir();start=time.perf_counter();cpu0=resource.getrusage(resource.RUSAGE_CHILDREN)
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--helper',choices=['success','incomplete','hang']);p.add_argument('--parent-only',action='store_true')
    for key in ('root','code','card','inputs','package'):p.add_argument('--'+key,type=Path)
    a=p.parse_args()
    if a.helper:helper(a.helper)
    else:main(a)
