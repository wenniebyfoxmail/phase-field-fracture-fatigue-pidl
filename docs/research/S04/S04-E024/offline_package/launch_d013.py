#!/usr/bin/env python3
"""D013 v1: approval-bound, one-shot local offline launcher. Default cannot run."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import resource
import signal
import shutil
import subprocess
import sys
import tarfile
import time

SCIENCE='18d0e7cb1153dc969c1ee0c21c77ada1297b2d89'
TREE='14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23'
SCOPE='E024-D013-physical-field-budget-12-profiles'
PACK='D013-offline-20261020-v1'
PROJECT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
BASE=PROJECT/'local_archive/experiments/S04-E024'
CONTROL=BASE/'physical_field_budget_launch_20261020_v1'
OUTPUT=BASE/'physical_field_budget_execution_20261020_v1'
PYTHON=Path('/Users/wenxiaofang/miniconda3/bin/python3')
PACKAGE_ROOT=BASE/'physical_field_budget_package_20261020_v1'
PRIOR_CHECKS=BASE/'physical_field_budget_code_ready_v1'
HANDOFF_SECONDS=5.
THREAD_ENV={name:'2' for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')}
THREAD_ENV.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONOPTIMIZE='0',PYTHONNOUSERSITE='1')

class PackageError(ValueError):pass


def read(path):
    def invalid(s):raise PackageError('nonfinite JSON literal: '+s)
    return json.loads(Path(path).read_text(),parse_constant=invalid)


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def sha(path,check=lambda:None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while data:=f.read(1024*1024):check();h.update(data)
    return h.hexdigest()


def files_under(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def validate_package(package,check=lambda:None):
    package=Path(package);m=read(package/'package_manifest.json')
    if m['package_id']!=PACK or m['science_commit']!=SCIENCE or m['science_tree_sha256']!=TREE:
        raise PackageError('package/science identity')
    actual={str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p!=package/'package_manifest.json'}
    if actual!=set(m['files']):raise PackageError('package file set changed')
    for name,identity in m['files'].items():
        p=package/name
        if not p.resolve().is_relative_to(package.resolve()) or p.is_symlink():raise PackageError('unsafe package path')
        if p.stat().st_size!=identity['bytes'] or sha(p,check)!=identity['sha256']:raise PackageError('package hash: '+name)
    return m


def validate_authorization(auth,manifest_sha):
    if auth.get('user_approved_final_execution') is not True or auth.get('scope')!=SCOPE:
        raise PackageError('explicit user approval required')
    if auth.get('package_id')!=PACK or auth.get('package_manifest_sha256')!=manifest_sha:
        raise PackageError('approval is for a different package/version')
    if auth.get('execution_commit')!=SCIENCE or auth.get('run_output')!=str(OUTPUT) or auth.get('control_root')!=str(CONTROL):
        raise PackageError('approval source/paths mismatch')
    if not isinstance(auth.get('user_approval_quote'),str) or not auth['user_approval_quote'].strip():
        raise PackageError('human approval evidence absent')
    if auth.get('training_authorized') is not False or auth.get('remote_actions_authorized') is not False:
        raise PackageError('scope exceeded')


def safe_extract(archive,target,check=lambda:None):
    """Only regular files/directories; no links or paths outside fresh source."""
    target=Path(target)
    with tarfile.open(archive,'r:gz') as tf:
        total=0
        for member in tf:
            check();parts=Path(member.name).parts
            if not parts or parts[0]!='source' or Path(member.name).is_absolute() or '..' in parts:
                raise PackageError('unsafe source member')
            if not (member.isfile() or member.isdir()):raise PackageError('source links/devices forbidden')
            total+=member.size
            if total>512*1024**2:raise PackageError('unpacked source exceeds512MiB')
            dest=target/member.name
            if member.isdir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as src,dest.open('xb') as out:
                    while data:=src.read(1024*1024):check();out.write(data)
                dest.chmod(member.mode & 0o777)


def code_tree(source,check=lambda:None):
    check();files=subprocess.check_output(['git','-C',str(source),'ls-files','SENS_tensile','scripts','tests'],text=True,timeout=getattr(check,'timeout',lambda:15.)()).splitlines()
    files=[p for p in files if p.endswith('.py')]+[
        'docs/research/S04/S04-E024/physical_field_budget_plan.md',
        'docs/research/S04/S04-E024/physical_field_budget_contract.json']
    return hashlib.sha256(json.dumps({p:sha(source/p,check) for p in sorted(files)},sort_keys=True).encode()).hexdigest()


def source_admission(source,check=lambda:None):
    check();head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,timeout=getattr(check,'timeout',lambda:15.)()).strip()
    check();dirty=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True,timeout=getattr(check,'timeout',lambda:15.)())
    check()
    if head!=SCIENCE or dirty or code_tree(source,check)!=TREE:raise PackageError('source HEAD/clean/tree mismatch')


def environment_admission(expected):
    actual=dict(python=sys.version,executable=str(Path(sys.executable).resolve()),system=platform.system(),machine=platform.machine(),
        user=getpass.getuser(),versions={name:metadata.version(name) for name in expected['versions']})
    if actual!=expected:raise PackageError('environment changed; no installation or silent replacement')
    return actual


def input_admission(project,manifest,check=lambda:None):
    count=total=0
    for row in manifest['files']:
        check();p=project/row['path']
        if not p.resolve().is_relative_to(project.resolve()) or not row['path'].startswith('local_archive/experiments/'):
            raise PackageError('input outside declared archives')
        if p.stat().st_size!=row['bytes'] or sha(p,check)!=row['sha256']:raise PackageError('input changed: '+row['path'])
        count+=1;total+=row['bytes']
    return dict(files=count,bytes=total,manifest_only=True,real_model_FEM_forward_count=0)


def combined_storage(roots):return sum(files_under(root) for root in roots)


def supervise_child(child,roots,deadline,cap=1024**3,poll=.1):
    """Watch only our new session/group; combine package/control/output archive."""
    import psutil
    observed=0;peak_archive=0;begin=time.monotonic();stop=None
    try:
        while child.poll() is None:
            if time.monotonic()>=deadline:raise PackageError('global3120s cumulative deadline')
            size=combined_storage(roots);peak_archive=max(peak_archive,size)
            if size>cap:raise PackageError('combined1GiB archive cap')
            try:
                process=psutil.Process(child.pid)
                for proc in [process]+process.children(recursive=True):
                    try:observed=max(observed,proc.memory_info().rss)
                    except psutil.NoSuchProcess:pass
            except psutil.NoSuchProcess:pass
            if observed>3*1024**3:raise PackageError('owned process RSS cap')
            time.sleep(min(poll,max(.001,deadline-time.monotonic())))
        size=combined_storage(roots);peak_archive=max(peak_archive,size)
        if size>cap or time.monotonic()>=deadline:raise PackageError('combined archive/global cap at completion')
        if child.returncode:raise PackageError('scientific parent exit '+str(child.returncode))
    except BaseException as e:
        stop=str(e)
        # child.pid is the fresh group/session created by our Popen only.
        try:os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait(timeout=2)
        raise
    finally:
        # Kept by caller even on failure; parent science files remain untouched.
        child.d013_supervision=dict(stop=stop,wall_seconds=time.monotonic()-begin,
            observed_max_process_rss_bytes=observed,observed_combined_archive_bytes=peak_archive,
            exit_code=child.poll(),pid=child.pid)
    return child.d013_supervision


def main():
    start=time.monotonic() # before authorization parsing/hash/environment/any byte work
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization',type=Path)
    a=parser.parse_args()
    if a.authorization is None:parser.error('preparation only; no scientific start without approval of this package')
    package=Path(__file__).resolve().parent
    auth=read(a.authorization)
    if auth.get('user_approved_final_execution') is not True:raise PackageError('explicit user approval required')
    base_check=read(package/'receipts/nontraining.json');used=base_check['wall_seconds']
    if not isinstance(used,(int,float)) or not math.isfinite(used) or not 0<=used<300:raise PackageError('nontraining balance')
    deadline=start+300-used;last_storage=[-math.inf]
    roots=(PACKAGE_ROOT,PRIOR_CHECKS,CONTROL,OUTPUT)
    def guard():
        now=time.monotonic()
        if now>=deadline:raise PackageError('nontraining/prelaunch time exhausted')
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if rss*(1 if platform.system()=='Darwin' else 1024)>3*1024**3:raise PackageError('launcher RSS cap')
        if now-last_storage[0]>=.1:
            last_storage[0]=now
            if combined_storage(roots)>1024**3:raise PackageError('combined1GiB archive cap')
        if time.monotonic()>=deadline:raise PackageError('nontraining/prelaunch time exhausted')
    guard.timeout=lambda:min(15.,max(.001,deadline-time.monotonic()))
    guard();validate_authorization(auth,sha(package/'package_manifest.json',guard))
    validate_package(package,guard);guard()
    if Path(sys.executable).resolve()!=PYTHON.resolve() or __debug__ is not True:raise PackageError('bound Python without -O required')
    expected=read(package/'execution_plan.json');guard();environment_admission(expected['environment']);guard()
    if package!=PACKAGE_ROOT/'D013-offline-20261020-v1':raise PackageError('exact approved package location required')
    if CONTROL.exists() or OUTPUT.exists():raise PackageError('one-shot root already exists; no retry/reuse')
    CONTROL.mkdir() # atomic claim; any later failure consumes this launch
    spawned=False;spawn_attempted=False;child=None
    try:
        guard()
        if shutil.disk_usage(BASE).free<2*1024**3:raise PackageError('less than2GiB free for fixed source/output caps')
        inputs=input_admission(PROJECT,read(package/'inputs_manifest.json'),guard)
        safe_extract(package/'D013_source_18d0e7cb.tar.gz',CONTROL,guard)
        source=CONTROL/'source';source_admission(source,guard)
        code=read(package/'receipts/code_ready.json');guard()
        if code['verdict']!='CODE_READY_PASS' or code['source_commit']!=SCIENCE or code['code_tree_sha256']!=TREE:
            raise PackageError('Code Ready receipt')
        if base_check['verdict']!='NONTRAINING_CHECKS_PASS' or base_check['code_tree_sha256']!=TREE or any(base_check[k]!=0 for k in ('real_model_or_FEM_forward_count','NN_optimizer_steps')):
            raise PackageError('nontraining receipt')
        guard();handoff_start=time.monotonic();elapsed=handoff_start-start
        if used+elapsed+HANDOFF_SECONDS>=300:raise PackageError('no bounded handoff balance')
        # Charge a conservative5s allowance BEFORE receipt/claim/spawn work; not
        # a measured wall-time claim. No new budget; unused allowance not reclaimed.
        runtime_check=dict(base_check,wall_seconds=used+elapsed+HANDOFF_SECONDS,
            recorded_prelaunch_before_handoff_seconds=elapsed,handoff_reserved_seconds=HANDOFF_SECONDS,
            wall_seconds_is_conservative_budget_charge=True,prelaunch_identity=inputs,
            package_manifest_sha256=sha(package/'package_manifest.json',guard))
        check_path=CONTROL/'nontraining_runtime.json';write(check_path,runtime_check)
        runtime_approval=dict(auth,contract_sha256=expected['contract_sha256'],
            code_ready=dict(path=str(package/'receipts/code_ready.json'),sha256=sha(package/'receipts/code_ready.json',guard)),
            nontraining=dict(path=str(check_path),sha256=sha(check_path,guard)))
        approval_path=CONTROL/'execution_approval.json';write(approval_path,runtime_approval)
        command=[str(PYTHON),str(source/'SENS_tensile/run_s04_e024_field_budget.py'),'--execute-scientific',
            '--project',str(PROJECT),'--out',str(OUTPUT),'--expected-commit',SCIENCE,'--approval',str(approval_path)]
        env=os.environ.copy();env.update(THREAD_ENV)
        for key in ('PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        write(CONTROL/'LAUNCH_CLAIM.json',dict(status='SPAWN_PENDING_DO_NOT_RETRY',command=command,
            human_authorization_sha256=sha(a.authorization,guard),prelaunch=inputs,package_manifest_sha256=sha(package/'package_manifest.json',guard)))
        guard()
        if time.monotonic()-handoff_start>=HANDOFF_SECONDS:raise PackageError('bounded handoff exhausted before spawn')
        with (CONTROL/'stdout.log').open('x') as out,(CONTROL/'stderr.log').open('x') as err:
            spawn_attempted=True
            child=subprocess.Popen(command,cwd=source,env=env,stdout=out,stderr=err,start_new_session=True);spawned=True
            write(CONTROL/'launched.json',dict(status='DISPATCHED_NOT_COMPLETED',pid=child.pid,command=command,
                host=platform.node(),utc=datetime.now(timezone.utc).isoformat(),source_commit=SCIENCE,
                package_manifest_sha256=sha(package/'package_manifest.json',guard),output=str(OUTPUT),
                no_retry=True,NN_training=False,GPU_hours=0))
        guard()
        if time.monotonic()-handoff_start>=HANDOFF_SECONDS:raise PackageError('bounded handoff exhausted')
        supervision=supervise_child(child,roots,start+3120-used)
        write(CONTROL/'supervision_exit.json',dict(**supervision,execution_complete=True,scientific_success_not_inferred=True,
            prelaunch_handoff_seconds=time.monotonic()-handoff_start-supervision['wall_seconds']))
    except BaseException as e:
        if child is not None and child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=2)
        write(CONTROL/'launch_failure.json',dict(error=type(e).__name__+': '+str(e),
            spawned=spawned,spawned_or_ambiguous=spawn_attempted,no_retry=True,wall_seconds=time.monotonic()-start,
            supervision=None if child is None else getattr(child,'d013_supervision',None)))
        raise


if __name__=='__main__':main()
