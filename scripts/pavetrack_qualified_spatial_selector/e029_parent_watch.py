"""Independent stage lifeline: parent death terminates its fresh session only."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path

def parent_alive(pid,birth,ps):
    if os.getppid()!=pid:return False
    try:return ps.Process(pid).create_time()==birth
    except ps.NoSuchProcess:return False

def stop_group(note,reason,group=None):
    group=os.getpid() if group is None else group
    if group!=os.getpid() or os.getpgid(0)!=group or os.getsid(0)!=group:raise PermissionError('lifeline must own fresh session/group')
    try:
        try:Path(note).write_text(json.dumps(dict(first_stop=reason,pid=os.getpid(),group=group,time=time.time(),no_retry=True))+'\n')
        except BaseException:
            try:os.write(2,b'lifeline first stop; receipt failed\n')
            except BaseException:pass
    finally:
        # This group belongs only to this retained session. No UID/name/global signal.
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        try:os.killpg(group,signal.SIGTERM);time.sleep(.5)
        finally:os.killpg(group,signal.SIGKILL)

def main():
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import e029_system_proc as psutil
    p=argparse.ArgumentParser();p.add_argument('--parent',type=int,required=True);p.add_argument('--birth',type=float,required=True);p.add_argument('--note',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();cmd=a.command
    if cmd and cmd[0]=='--':cmd=cmd[1:]
    if os.getpid()!=os.getsid(0) or os.getpid()!=os.getpgid(0):raise PermissionError('own retained session only')
    stopping=[]
    def requested(sig,frame):stopping.append('signal '+str(sig))
    for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,requested)
    if not parent_alive(a.parent,a.birth,psutil):stop_group(a.note,'parent gone before stage')
    env=dict(os.environ,E029_PARENT_PID=str(os.getpid()),E029_PARENT_BIRTH=str(psutil.Process().create_time()))
    child=subprocess.Popen(cmd,env=env,start_new_session=False)
    while child.poll() is None:
        if stopping or not parent_alive(a.parent,a.birth,psutil):stop_group(a.note,stopping[0] if stopping else 'wrapper parent disappeared')
        time.sleep(.1)
    if stopping or not parent_alive(a.parent,a.birth,psutil):stop_group(a.note,'parent disappeared at stage exit')
    raise SystemExit(child.returncode)
if __name__=='__main__':main()
