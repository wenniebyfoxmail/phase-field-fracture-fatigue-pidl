#!/usr/bin/env python3
"""Single-GPU task isolation, per-job anti-hang timer and immutable accounting.

Only executes the exact argv/cwd/hash bound in a human-approved task record.
The current explicit authority removes the cumulative resource ceiling.
An unfinished attempt still blocks subsequent dispatch; it is never retried.
GNU timeout remains alive if this supervisor disappears. A separate new
session contains only this task's timeout/worker descendants.
"""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import time


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def new_json(p,v):
    with Path(p).open('x') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def available_seconds(directory, cap):
    used=0.
    for attempt in Path(directory).glob('*_attempt.json'):
        a=read(attempt);done=attempt.with_name(attempt.name.replace('_attempt.json','_finished.json'))
        if not done.is_file():raise RuntimeError(f'unfinished attempt; inspect before any dispatch: {attempt}')
        end=read(done)
        if end.get('attempt_sha256')!=digest(attempt):raise ValueError('budget receipt identity mismatch')
        elapsed=end['charged_gpu_seconds']
        if not isinstance(elapsed,(float,int)) or not math.isfinite(elapsed) or elapsed<0:
            raise ValueError('invalid elapsed accounting')
        used+=elapsed
    return None if cap is None else max(0.,cap-used)


def owned_group_members(pgid, root, proc_root=Path('/proc'), *, expected_entry=None,
                        not_before_ticks=None, leader_start_ticks=None, observations=None):
    """Inspect our new session even after its timeout leader has exited."""
    members=[]
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():continue
        try:
            raw=(entry/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
        except FileNotFoundError:
            continue
        if int(fields[2])!=pgid or fields[0]=='Z':continue
        try:
            own_cwd=(entry/'cwd').resolve(strict=True).is_relative_to(root)
        except OSError as error:
            # A deleted cwd is not proof that the process has exited. Preserve
            # the reservation when ownership cannot be read, including races.
            raise RuntimeError('process-group ownership cannot be verified; preserve reservation') from error
        if int(fields[3])!=pgid or not own_cwd:
            raise RuntimeError('process-group ownership cannot be verified; preserve reservation')
        # Shared account: cwd/session alone are not sufficient ownership proof.
        # Read each live command and elapsed time, with a stable birth identity.
        try:
            start_ticks=int(fields[19])
            command=(entry/'cmdline').read_bytes().split(b'\0')
            command=[part.decode('utf-8',errors='strict') for part in command if part]
            again=(entry/'stat').read_text();after=again[again.rfind(')')+2:].split()
            if after[0]=='Z':continue
            hz=os.sysconf('SC_CLK_TCK')
            uptime=float((proc_root/'uptime').read_text().split()[0])
            elapsed=uptime-start_ticks/hz
        except FileNotFoundError:
            # Disappearance is not an authorization to signal another process.
            continue
        except (OSError,ValueError,IndexError,UnicodeError) as error:
            raise RuntimeError('process command or elapsed time is unknown; preserve reservation') from error
        if (expected_entry is None or not_before_ticks is None
                or expected_entry not in command or start_ticks < not_before_ticks
                or int(after[19])!=start_ticks or int(after[2])!=pgid or int(after[3])!=pgid
                or not math.isfinite(elapsed) or elapsed < 0
                or (int(entry.name)==pgid and leader_start_ticks is not None and start_ticks!=leader_start_ticks)):
            raise RuntimeError('process command/birth/elapsed ownership mismatch; preserve reservation')
        if observations is not None:
            observations.append(dict(pid=int(entry.name),pgid=pgid,start_ticks=start_ticks,
                                     elapsed_seconds=elapsed,cmdline=command,cwd=str((entry/'cwd').resolve()),
                                     inspected_utc=utc()))
        members.append(int(entry.name))
    return members


def settle_owned_group(pgid, root, **identity):
    # Never infer that descendants stopped just because timeout exited.
    for sig,seconds in ((signal.SIGTERM,10),(signal.SIGKILL,5)):
        if not owned_group_members(pgid,root,**identity):return
        try:os.killpg(pgid,sig)
        except ProcessLookupError:pass
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if not owned_group_members(pgid,root,**identity):return
            time.sleep(.1)
    if owned_group_members(pgid,root,**identity):
        raise RuntimeError('owned descendants remain alive; reservation not released')


def validate(a,path):
    if a.get('schema')!='s04_e036_gpu_supervisor_v2' or a.get('approved') is not True or not a.get('approval_reference'):
        raise ValueError('actual task approval required')
    if platform.system()!='Linux' or platform.node()!=a['hostname']:raise ValueError('approved Linux producer required')
    if a['hostname']!='GPUServer8' or 'total_gpu_seconds' not in a or a['total_gpu_seconds'] is not None:
        raise ValueError('current authority requires GPUServer8 and explicit null cumulative ceiling')
    if a.get('cumulative_ceiling_removed_by_user') is not True:
        raise ValueError('explicit current user instruction removing cumulative ceiling is required')
    visible=str(a['gpu']);
    if not visible.isdigit() or os.environ.get('CUDA_VISIBLE_DEVICES')!=visible:raise ValueError('explicit single GPU mismatch')
    root=Path(a['root']).resolve();code=Path(a['cwd']).resolve()
    if not str(root).startswith('/mnt/data2/drtao/wennie/pf_s04e036_') or not code.is_relative_to(root):raise ValueError('task-owned large-disk roots required')
    if a['label'] not in ('paired_main','optimization_probe','expression_probe','mechanism_probe','scoring'):raise ValueError('unknown task phase')
    wall=a['wall_seconds']
    if type(wall) is not int or wall<30:raise ValueError('explicit finite per-job anti-hang time required')
    if not isinstance(a.get('anti_hang_rationale'),str) or not a['anti_hang_rationale'].strip():
        raise ValueError('per-job anti-hang rationale required; not a renewed cumulative cap')
    args=a['argv']
    if not isinstance(args,list) or len(args)<2 or not all(isinstance(x,str) for x in args):raise ValueError('explicit argv required')
    executable=Path(args[0]).resolve();entry=Path(args[1]).resolve()
    if not executable.is_file() or not entry.is_relative_to(code) or digest(entry)!=a['entry_sha256']:raise ValueError('entry identity mismatch')
    if not shutil.which('timeout'):raise RuntimeError('GNU timeout unavailable')
    if shutil.disk_usage(root).free<20*1024**3:raise RuntimeError('20 GiB free storage required')
    return root,code,args,wall


def main():
    p=argparse.ArgumentParser();p.add_argument('--authority',type=Path,required=True);a=p.parse_args()
    auth=read(a.authority);root,cwd,args,wall=validate(auth,a.authority)
    logs=root/'supervisor';logs.mkdir(exist_ok=True)
    with (logs/'dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        remaining=available_seconds(logs,auth['total_gpu_seconds'])
        if remaining is not None and wall>remaining:raise RuntimeError('phase reservation exceeds remaining approved GPU hours')
        label=auth['label'];attempt=logs/(label+'_attempt.json');finished=logs/(label+'_finished.json')
        if attempt.exists() or finished.exists():raise FileExistsError('one attempt per phase; no automatic retry')
        # Recheck availability immediately before the only dispatch.
        info=subprocess.check_output(['nvidia-smi','-i',str(auth['gpu']),
            '--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
        mem,util=[int(v.strip()) for v in info.split(',')]
        if mem>100 or util>0:raise RuntimeError(f'GPU is occupied: {info}; no task dispatched')
        start=time.monotonic();proc=None;reason='startup_failure';exitcode=None
        ownership_observations=[];not_before_ticks=None;leader_start_ticks=None
        new_json(attempt,dict(schema='s04_e036_gpu_attempt_v2',started_utc=utc(),
            host=platform.node(),supervisor_pid=os.getpid(),authority_sha256=digest(a.authority),
            anti_hang_seconds=wall,total_gpu_seconds=None,
            gpu_count=1,gpu=auth['gpu'],argv=args,cwd=str(cwd)))
        def interrupted(signum,frame):raise InterruptedError(f'supervisor signal {signum}')
        for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
        env=os.environ.copy()
        for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='1'
        env['MPLBACKEND']='Agg'
        for name,sub in [('TMPDIR','tmp'),('XDG_CACHE_HOME','cache'),('TORCH_EXTENSIONS_DIR','jitcache')]:
            loc=root/sub;loc.mkdir(exist_ok=True);env[name]=str(loc)
        try:
            with (logs/(label+'_stdout.log')).open('xb') as out,(logs/(label+'_stderr.log')).open('xb') as err:
                command=['timeout','--signal=TERM','--kill-after=10s',str(wall-15)+'s',*args]
                not_before_ticks=int(float(Path('/proc/uptime').read_text().split()[0])*os.sysconf('SC_CLK_TCK'))
                proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
                try:
                    stat=Path(f'/proc/{proc.pid}/stat').read_text()
                    leader_start_ticks=int(stat[stat.rfind(')')+2:].split()[19])
                except FileNotFoundError:
                    # A very short worker may already have exited. Any remaining
                    # group members must still satisfy the pre-spawn birth bound.
                    pass
                new_json(logs/(label+'_started.json'),dict(pid=proc.pid,pgid=proc.pid,
                    started_utc=utc(),command=command,attempt_sha256=digest(attempt),
                    not_before_ticks=not_before_ticks,leader_start_ticks=leader_start_ticks))
                exitcode=proc.wait();reason='completed' if exitcode==0 else 'worker_or_timeout_failure'
        except BaseException as error:
            reason=f'{type(error).__name__}: {error}'
            raise
        finally:
            if proc is None:
                # Popen may have created a child before an asynchronous signal
                # interrupted assignment. Do not turn uncertainty into free
                # budget or permission for another dispatch.
                new_json(logs/(label+'_unknown.json'),dict(ended_utc=utc(),reason=reason,
                    attempt_sha256=digest(attempt),reservation_released=False))
            else:
                try:
                    settle_owned_group(proc.pid,root,expected_entry=args[1],not_before_ticks=not_before_ticks,
                                       leader_start_ticks=leader_start_ticks,observations=ownership_observations)
                    proc.wait(timeout=1)
                    exitcode=proc.returncode
                except BaseException as error:
                    new_json(logs/(label+'_unknown.json'),dict(ended_utc=utc(),reason=str(error),
                        attempt_sha256=digest(attempt),reservation_released=False,
                        cleanup_ownership_observations=ownership_observations))
                    raise
                elapsed=time.monotonic()-start
                new_json(finished,dict(ended_utc=utc(),attempt_sha256=digest(attempt),
                    exit_code=exitcode,reason=reason,charged_gpu_seconds=elapsed,
                    anti_hang_seconds=wall,within_anti_hang_interval=elapsed<=wall,
                    cumulative_ceiling=None,cleanup_ownership_observations=ownership_observations))
        if exitcode!=0:raise SystemExit(exitcode if 0<exitcode<256 else 1)
if __name__=='__main__':main()
