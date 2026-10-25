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
import traceback


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


def remaining_task_wall(start, total_seconds, now, *, cleanup_seconds=0, hard_end=None):
    """One task start across continuations; wall is not CPU/GPU consumption."""
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
           for v in (total_seconds, cleanup_seconds)):
        raise ValueError('finite nonnegative task wall/cleanup limits required')
    if any(t.tzinfo is None for t in (start, now)) or now < start:
        raise ValueError('aware, monotone task timestamps required')
    remaining = total_seconds-(now-start).total_seconds()-cleanup_seconds
    if hard_end is not None:
        if hard_end.tzinfo is None:
            raise ValueError('aware hard end required')
        remaining = min(remaining, (hard_end-now).total_seconds()-cleanup_seconds)
    return max(0., remaining)


def execution_wall_allowance(authority, now):
    """Apply only an owner-declared task clock; never invent or reset one.

    Legacy E036 has no cumulative ceiling by explicit user instruction.
    This optional elapsed-wall clock requires explicit waiting inclusion.
    """
    wall = authority['wall_seconds']
    clock = authority.get('task_clock')
    if clock is None:
        return wall
    if clock.get('waiting_included') is not True:
        raise ValueError('elapsed task clock requires explicit waiting inclusion')
    start = dt.datetime.fromisoformat(clock['start_utc'].replace('Z', '+00:00'))
    hard = clock.get('hard_end_utc')
    hard = None if hard is None else dt.datetime.fromisoformat(hard.replace('Z', '+00:00'))
    return min(wall, remaining_task_wall(start, clock['total_wall_seconds'], now,
        cleanup_seconds=clock.get('cleanup_seconds', 0), hard_end=hard))


def run_captured(command, cwd, logs, label, attempt, *, env=None,
                 wall_seconds=None, on_started=None, settle=None,
                 popen=subprocess.Popen):
    """Shared real child/log/receipt path; authority and admission stay in main.

    Spawn exception is conservatively unknown: it cannot prove no child exists.
    Exit code stays null until observed. Cleanup must verify task ownership or
    retain the reservation. This function grants no producer/compute authority.
    """
    if Path(label).name != label or not label:
        raise ValueError('plain task label required')
    if wall_seconds is not None and (not math.isfinite(wall_seconds) or wall_seconds < 0):
        raise ValueError('invalid remaining wall allowance')
    logs = Path(logs); cwd = Path(cwd).resolve(); attempt = Path(attempt)
    start = time.monotonic(); proc = None; exitcode = None
    error = None; raw_error = None; cleanup_error = None; identity = {}
    state = 'unknown'; reason = 'startup_failure'
    if wall_seconds == 0:
        state = 'not_started_deadline'; reason = 'remaining task wall time exhausted'
    else:
        try:
            with (logs/(label+'_stdout.log')).open('xb') as out, (logs/(label+'_stderr.log')).open('xb') as err:
                proc = popen(command, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True)
                # Capture PID before observers/callbacks that can themselves fail.
                new_json(logs/(label+'_started.json'), dict(pid=proc.pid, pgid=proc.pid,
                    started_utc=utc(), command=list(command), cwd=str(cwd),
                    attempt_sha256=digest(attempt)))
                if on_started is not None:
                    identity = on_started(proc) or {}
                remaining = None if wall_seconds is None else max(0., wall_seconds-(time.monotonic()-start))
                exitcode = proc.wait(timeout=remaining)
                state = 'completed' if exitcode == 0 else 'worker_failure'
                reason = 'completed' if exitcode == 0 else 'worker_or_timeout_failure'
        except BaseException as exc:
            error = f'{type(exc).__name__}: {exc}'
            raw_error = traceback.format_exc()
            state = 'unknown' if proc is None else 'wrapper_failure'
            reason = error
        finally:
            if proc is not None:
                try:
                    if settle is not None:
                        settle(proc, identity)
                    elif proc.poll() is None:
                        raise RuntimeError('live child; ownership-aware cleanup required')
                    exitcode = proc.wait(timeout=1)
                except BaseException as exc:
                    cleanup_error = f'{type(exc).__name__}: {exc}'
                    if raw_error is None:
                        raw_error = traceback.format_exc()
                    state = 'unknown'; reason = cleanup_error
    elapsed = time.monotonic()-start
    result = dict(ended_utc=utc(), attempt_sha256=digest(attempt),
        execution_state=state, pid=None if proc is None else proc.pid,
        exit_code=exitcode, reason=reason, wrapper_error=error,
        wrapper_traceback=raw_error, cleanup_error=cleanup_error,
        cwd=str(cwd), command=list(command), identity=identity,
        elapsed_wall_seconds=elapsed,
        # Legacy reservation field retained for compatibility; not GPU work.
        charged_gpu_seconds=elapsed if state != 'unknown' else None,
        resource_measurement={'cpu_seconds': None, 'gpu_seconds': None},
        accounting_basis='elapsed supervisor wall reservation; not measured GPU utilisation',
        anti_hang_seconds=wall_seconds,
        within_anti_hang_interval=None if wall_seconds is None else elapsed <= wall_seconds,
        reservation_released=state != 'unknown', cumulative_ceiling=None)
    if raw_error is not None:
        with (logs/(label+'_wrapper_error.log')).open('x') as f:
            f.write(raw_error)
    suffix = '_unknown.json' if state == 'unknown' else '_finished.json'
    new_json(logs/(label+suffix), result)
    return result


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
    wall=execution_wall_allowance(auth,dt.datetime.now(dt.timezone.utc))
    if wall<=15:
        raise RuntimeError('remaining task wall time does not cover execution and cleanup; no dispatch')
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
        command=['timeout','--signal=TERM','--kill-after=10s',str(wall-15)+'s',*args]
        not_before_ticks=int(float(Path('/proc/uptime').read_text().split()[0])*os.sysconf('SC_CLK_TCK'))
        def observed(proc):
            leader=None
            try:
                stat=Path(f'/proc/{proc.pid}/stat').read_text()
                leader=int(stat[stat.rfind(')')+2:].split()[19])
            except FileNotFoundError:
                pass
            return dict(not_before_ticks=not_before_ticks,leader_start_ticks=leader)
        def settled(proc,identity):
            settle_owned_group(proc.pid,root,expected_entry=args[1],
                not_before_ticks=not_before_ticks,
                leader_start_ticks=identity.get('leader_start_ticks'),
                observations=ownership_observations)
        result=run_captured(command,cwd,logs,label,attempt,env=env,
                            wall_seconds=wall,on_started=observed,settle=settled)
        if result['execution_state']=='unknown':
            raise RuntimeError('unknown live state; reservation retained; inspect before dispatch')
        if result['wrapper_error'] or result['execution_state']=='not_started_deadline':
            raise RuntimeError(result['reason'])
        exitcode=result['exit_code']
        if exitcode!=0:raise SystemExit(exitcode if 0<exitcode<256 else 1)
if __name__=='__main__':main()
