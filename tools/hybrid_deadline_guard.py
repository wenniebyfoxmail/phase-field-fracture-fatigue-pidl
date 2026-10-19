"""Linux deadline controller, separate from resource scans and receipt IO.

Only stdlib imports before control. Linux pidfds bind worker and supervisor
identities. Deadlines arrive over an inherited datagram FD, never a filesystem
read. Kill/reap signalling precedes any potentially blocking report write.
"""
import argparse,json,math,os,select,signal,socket,sys,tempfile,time
from pathlib import Path


def guard_loop(worker,supervisor,fd,phase_deadline,step_seconds,report,ready_fd=None):
    if not sys.platform.startswith('linux') or not hasattr(os,'pidfd_open'):
        raise RuntimeError('Linux pidfd deadline guardian required')
    wf=os.pidfd_open(worker);sf=os.pidfd_open(supervisor);sock=socket.socket(fileno=fd);sock.setblocking(False)
    active=None;last_step=0;reason=None;started=time.monotonic();status='worker_exited'
    def drain():
        nonlocal active,last_step,reason
        for _ in range(4096):
            try:m=json.loads(sock.recv(4096))
            except BlockingIOError:break
            except Exception:reason='invalid deadline message';break
            if m.get('event')=='step_start':
                if active or m['step']!=last_step+1:reason='invalid step sequence';break
                t=float(m['started'])
                if not math.isfinite(t) or t>time.monotonic()+.01:reason='invalid step time';break
                last_step=m['step'];active=dict(step=last_step,started=t,deadline=t+step_seconds)
            elif m.get('event')=='step_done':
                if not active or m['step']!=active['step']:reason='invalid step completion';break
                t=float(m['finished'])
                if not math.isfinite(t) or t<active['started'] or t>time.monotonic()+.01:reason='invalid finish time';break
                if t>=active['deadline']:reason='late step completion';break
                active=None
            elif m.get('event')=='shutdown':
                if wf not in ready:reason='shutdown while worker alive';break
            else:reason='unknown deadline event';break
        else:reason='deadline IPC flood'
    try:
        if ready_fd is not None:os.write(ready_fd,b'1');os.close(ready_fd)
        while True:
            now=time.monotonic()
            ready,_,_=select.select([wf,sf,sock],[],[],.05)
            if sf in ready:reason='supervisor exited';break
            drain()
            if reason:break
            # Consume queued completion timestamps BEFORE judging active time.
            # A timely done must not be rejected merely because this process
            # resumed a few ms after the old deadline. Late done still fails.
            now=time.monotonic()
            if now>=phase_deadline:reason='phase/global/shared/GPU reserved deadline';break
            if active and now>=active['deadline']:
                # Close the drain-to-clock scheduling gap: a timely completion
                # may have queued while this process was descheduled there.
                drain()
                if reason:break
                now=time.monotonic()
                if active and now>=active['deadline']:reason='physical-substep120s deadline';break
            if wf in ready:
                # Final deadline audit after exit; a worker cannot hide a late
                # success behind a resource monitor blocked in os.walk/fsync.
                now=time.monotonic()
                if now>=phase_deadline or active and now>=active['deadline']:reason='late worker exit'
                break
    except BaseException as exc:
        reason='controller exception: '+type(exc).__name__
    finally:
        try:
            if reason:
                status='deadline_or_control_stop'
                if not select.select([wf],[],[],0)[0]:
                    try:
                        signal.pidfd_send_signal(wf,signal.SIGTERM)
                        if not select.select([wf],[],[],10)[0]:signal.pidfd_send_signal(wf,signal.SIGKILL)
                    except ProcessLookupError:pass
        finally:
            os.close(wf);os.close(sf);sock.close()
    payload=dict(status=status,reason=reason,active=active,last_step=last_step,
                 started=started,finished=time.monotonic(),worker_pid=worker)
    p=Path(report);p.parent.mkdir(parents=True,exist_ok=True)
    f,tmp=tempfile.mkstemp(dir=p.parent,prefix='.guard-')
    with os.fdopen(f,'w') as h:json.dump(payload,h);h.flush();os.fsync(h.fileno())
    os.replace(tmp,p)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',type=int,required=True);p.add_argument('--supervisor',type=int,required=True)
    p.add_argument('--fd',type=int,required=True);p.add_argument('--deadline',type=float,required=True)
    p.add_argument('--step-seconds',type=float,required=True);p.add_argument('--report',required=True);p.add_argument('--ready-fd',type=int,required=True)
    a=p.parse_args();guard_loop(a.worker,a.supervisor,a.fd,a.deadline,a.step_seconds,a.report,a.ready_fd)
