"""D013 source/approval and parent-enforced phase limits. No scientific imports."""
from datetime import datetime, timezone
from importlib import metadata
import socket
import numpy as np
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from s04_e024_field_budget import (CONTRACT_SHA, PLAN_SHA, InvalidEvidence,
    ResourceStop, safe_json)

CAPS=dict(nontraining=300.,numeric=1800.,replay=900.,render=120.)
RSS_CAP=3*1024**3
STORAGE_CAP=1024**3
SOURCE=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(safe_json(value),indent=2,allow_nan=False)+'\n'
    tmp=path.with_name(path.name+'.tmp');tmp.write_text(data);tmp.replace(path)

def runtime_provenance():
    versions={}
    for name in ('numpy','scipy','torch','psutil','threadpoolctl'):
        try:versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError:versions[name]=None
    return dict(utc=datetime.now(timezone.utc).isoformat(),host=socket.gethostname(),
        platform=platform.platform(),python=sys.version,executable=sys.executable,pid=os.getpid(),
        versions=versions,cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'))


def persist_event(folder,event):
    """Persist full solver transform separately; never expand 568x568 into JSON."""
    from s04_e024_field_budget import digest_array
    folder=Path(folder);event=dict(event)
    if event['kind']=='solver':
        info=dict(event['info']);t=info.pop('preconditioner_transform',None)
        if t is not None:
            path=folder/f"outer_{event['outer']}_preconditioner.npy"
            with path.open('xb') as f:np.save(f,t,allow_pickle=False)
            info['preconditioner_transform_file']=dict(path=path.name,sha256=sha(path),array_sha256=digest_array(t))
        event['info']=info
    return safe_json(event)


def code_tree_sha(source=SOURCE):
    files=subprocess.check_output(['git','-C',str(source),'ls-files','SENS_tensile','scripts','tests'],text=True).splitlines()
    files=[p for p in files if p.endswith('.py')]
    files+=['docs/research/S04/S04-E024/physical_field_budget_plan.md',
            'docs/research/S04/S04-E024/physical_field_budget_contract.json']
    return hashlib.sha256(json.dumps({p:sha(source/p) for p in sorted(files)},sort_keys=True).encode()).hexdigest()


def validate_source(expected,source=SOURCE,clean=True):
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if head!=expected:raise InvalidEvidence('execution source commit mismatch')
    if clean and subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True):
        raise InvalidEvidence('execution requires clean source checkout')
    d=source/'docs/research/S04/S04-E024'
    if sha(d/'physical_field_budget_plan.md')!=PLAN_SHA or sha(d/'physical_field_budget_contract.json')!=CONTRACT_SHA:
        raise InvalidEvidence('reviewed design byte identity')


def validate_approval(path,expected,source=SOURCE):
    """Only an explicitly approved future final package may enter scientific paths."""
    a=json.loads(Path(path).read_text())
    if a.get('user_approved_final_execution') is not True or a.get('scope')!='E024-D013-physical-field-budget-12-profiles':
        raise InvalidEvidence('explicit final user-approved execution receipt required')
    if a.get('execution_commit')!=expected or a.get('contract_sha256')!=CONTRACT_SHA:
        raise InvalidEvidence('approval does not bind exact source/design')
    validate_source(expected,source)
    tree=code_tree_sha(source)
    for key,verdict in [('code_ready','CODE_READY_PASS'),('nontraining','NONTRAINING_CHECKS_PASS')]:
        item=a[key];p=Path(item['path'])
        if not p.is_absolute() or sha(p)!=item['sha256']:raise InvalidEvidence(key+' receipt hash')
        r=json.loads(p.read_text())
        if r.get('verdict')!=verdict or r.get('code_tree_sha256')!=tree:
            raise InvalidEvidence(key+' verdict/code tree')
        if key=='nontraining':
            if r.get('real_model_or_FEM_forward_count')!=0 or r.get('NN_optimizer_steps')!=0:
                raise InvalidEvidence('nontraining scope')
            used=float(r['wall_seconds'])
    if not 0<=used<=CAPS['nontraining']:raise ResourceStop('nontraining phase already exhausted')
    return a,used


def peak_rss():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024))


def storage_bytes(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


class LocalGuard:
    def __init__(self,root,deadline,rss_cap=RSS_CAP,storage_cap=STORAGE_CAP):
        self.root=Path(root);self.deadline=deadline;self.rss_cap=rss_cap;self.storage_cap=storage_cap
    def __call__(self):
        if time.monotonic()>=self.deadline:raise ResourceStop('absolute phase deadline')
        if peak_rss()>self.rss_cap:raise ResourceStop('observed peak RSS cap')
        if storage_bytes(self.root)>self.storage_cap:raise ResourceStop('archive storage cap')


class PhaseLedger:
    def __init__(self,nontraining_used=0.):
        if not 0<=nontraining_used<=CAPS['nontraining']:raise ResourceStop('nontraining time cap')
        self.used=dict(nontraining=float(nontraining_used),numeric=0.,replay=0.,render=0.);self.stopped=False
    def remaining(self,phase):
        if self.stopped:raise ResourceStop('latched resource stop; no later state/phase')
        rem=min(CAPS[phase]-self.used[phase],3120.-sum(self.used.values()))
        if rem<=0:
            self.stopped=True;raise ResourceStop('phase/cumulative budget exhausted')
        return rem
    def charge(self,phase,seconds):
        if self.stopped:raise ResourceStop('latched resource stop')
        if not math.isfinite(seconds) or seconds<0:raise InvalidEvidence('invalid elapsed wall time')
        self.used[phase]+=seconds
        if self.used[phase]>CAPS[phase] or sum(self.used.values())>3120.:
            self.stopped=True;raise ResourceStop('phase/cumulative cap; no next state')


def supervise(command,cwd,out_root,log_dir,seconds,rss_cap=RSS_CAP,storage_cap=STORAGE_CAP):
    """Observe only this owned child; enforce limits while SciPy is running."""
    import psutil
    if not math.isfinite(seconds) or seconds<=0 or storage_bytes(out_root)>storage_cap:raise ResourceStop('pre-spawn phase/storage cap')
    log_dir=Path(log_dir);log_dir.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();deadline=start+seconds;record=dict(command=command,timeout_seconds=seconds,provenance=runtime_provenance())
    write_json(log_dir/'command.json',record)
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2',NUMEXPR_NUM_THREADS='2')
    if storage_bytes(out_root)>storage_cap:raise ResourceStop('pre-spawn archive cap after metadata')
    observed=0;stop=None
    with (log_dir/'stdout.log').open('w') as stdout,(log_dir/'stderr.log').open('w') as stderr:
        child=subprocess.Popen(command,cwd=cwd,stdout=stdout,stderr=stderr,env=env)
        try:
            while child.poll() is None:
                if time.monotonic()>=deadline:stop='parent phase deadline'
                try: observed=max(observed,psutil.Process(child.pid).memory_info().rss)
                except psutil.NoSuchProcess:pass
                if observed>rss_cap:stop='parent child RSS cap'
                if storage_bytes(out_root)>storage_cap:stop='parent archive cap'
                if stop:raise ResourceStop(stop)
                time.sleep(min(.05,max(.001,deadline-time.monotonic())))
            if child.returncode:raise ResourceStop('owned child exit '+str(child.returncode))
            if time.monotonic()>=deadline:raise ResourceStop('child completed after phase deadline')
            if storage_bytes(out_root)>storage_cap:raise ResourceStop('archive cap at child completion')
        except BaseException as e:
            stop=str(e)
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            raise
        finally:
            record.update(pid=child.pid,exit_code=child.poll(),stop=stop,
                          wall_seconds=time.monotonic()-start,observed_child_rss_bytes=observed)
            write_json(log_dir/'exit.json',record)
    return record


def worker_context(root,state,phase,approval,expected):
    root=Path(root);context=json.loads((root/'execution_context.json').read_text())
    if os.getppid()!=context['parent_pid'] or phase not in ('numeric','replay','render'):
        raise InvalidEvidence('worker must be a supervised direct child')
    if state!=context['active_state'] or phase!=context['active_phase']:
        raise InvalidEvidence('worker state/phase order mismatch')
    if context['approval_sha256']!=sha(approval):raise InvalidEvidence('worker approval identity')
    validate_approval(approval,expected)
    return LocalGuard(root,float(context['phase_deadline']))
