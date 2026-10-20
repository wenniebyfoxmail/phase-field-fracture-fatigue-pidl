"""Owned Linux sessions only. Shared UID never grants kill authority."""
import os,signal,time
from pathlib import Path

def identity(process):
    return dict(pid=process.pid,birth=process.create_time(),uid=process.uids().real,cmd=process.cmdline(),cwd=process.cwd())
def matches(process,saved):
    return process.create_time()==saved['birth'] and process.uids().real==saved['uid'] and process.cmdline()==saved['cmd'] and process.cwd()==saved['cwd']
def capture(process,run,controller_pid):
    if controller_pid not in [p.pid for p in process.parents()] or str(run) not in ' '.join(process.cmdline()) or process.uids().real!=os.getuid():raise PermissionError('unowned Linux child')
    if os.getpgid(process.pid)!=os.getpgid(controller_pid) or os.getsid(process.pid)!=os.getsid(controller_pid):raise PermissionError('worker outside controller owned session')
    children=process.children(recursive=True);records=[]
    for p in [process,*children]:
        rec=identity(p)
        if rec['uid']!=os.getuid() or not (str(Path(run).parent) in ' '.join(rec['cmd']) or Path(rec['cwd']).is_relative_to(Path(run).parent)):raise PermissionError('descendant identity outside task')
        records.append(rec)
    return records

def terminate_child(child,run,controller_pid,ps=None):
    import psutil
    ps=psutil if ps is None else ps
    try:root=ps.Process(child.pid)
    except ps.NoSuchProcess:return
    records=capture(root,run,controller_pid)
    # Signal exact captured birth identities, descendants before root. No pkill/UID kill.
    errors=[]
    for sig in [signal.SIGTERM,signal.SIGKILL]:
        for rec in reversed(records):
            try:
                live=ps.Process(rec['pid'])
                if live.status()==ps.STATUS_ZOMBIE:continue
                if not matches(live,rec):raise PermissionError('PID reuse or command/cwd change; no signal')
                live.send_signal(sig)
            except ps.NoSuchProcess:pass
            except BaseException as e:errors.append(repr(e))
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            alive=[]
            for rec in records:
                try:
                    p=ps.Process(rec['pid'])
                    if p.create_time()==rec['birth'] and p.status()!=ps.STATUS_ZOMBIE:alive.append(p)
                except ps.NoSuchProcess:pass
            if not alive:break
            time.sleep(.05)
    child.wait(timeout=2)
    for rec in records:
        try:
            p=ps.Process(rec['pid'])
            if p.create_time()==rec['birth'] and p.status()!=ps.STATUS_ZOMBIE:errors.append('owned PID survives '+str(rec['pid']))
        except ps.NoSuchProcess:pass
    if errors:raise RuntimeError('cleanup_uncertain '+repr(errors))
