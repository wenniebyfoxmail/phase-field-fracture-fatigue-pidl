"""Small Linux /proc supervisor for the system-stdlib entry; no site packages."""
import os,shutil,time
from pathlib import Path
from types import SimpleNamespace
STATUS_ZOMBIE='zombie'
class NoSuchProcess(OSError):pass
class AccessDenied(PermissionError):pass

def stat(pid):
    try:
        raw=Path('/proc',str(pid),'stat').read_text();v=raw[raw.rfind(')')+2:].split()
        return dict(state=v[0],ppid=int(v[1]),group=int(v[2]),session=int(v[3]),birth=int(v[19]),rss=int(v[21])*os.sysconf('SC_PAGE_SIZE'))
    except FileNotFoundError as e:raise NoSuchProcess(pid) from e
    except PermissionError as e:raise AccessDenied(pid) from e
class Process:
    def __init__(self,pid=None):self.pid=os.getpid() if pid is None else pid;self.birth=stat(self.pid)['birth']
    def _stat(self):
        value=stat(self.pid)
        if value['birth']!=self.birth:raise NoSuchProcess('PID reused')
        return value
    def create_time(self):return self._stat()['birth']  # Linux starttime ticks, not wall-clock seconds
    def ppid(self):return self._stat()['ppid']
    def uids(self):
        self._stat()
        try:return SimpleNamespace(real=Path('/proc',str(self.pid)).stat().st_uid)
        except FileNotFoundError as e:raise NoSuchProcess(self.pid) from e
    def cmdline(self):
        self._stat()
        try:return [v.decode(errors='replace') for v in Path('/proc',str(self.pid),'cmdline').read_bytes().split(b'\0') if v]
        except FileNotFoundError as e:raise NoSuchProcess(self.pid) from e
        except PermissionError as e:raise AccessDenied(self.pid) from e
    def cwd(self):
        self._stat()
        try:return os.readlink('/proc/'+str(self.pid)+'/cwd')
        except FileNotFoundError as e:raise NoSuchProcess(self.pid) from e
        except PermissionError as e:raise AccessDenied(self.pid) from e
    def memory_info(self):return SimpleNamespace(rss=self._stat()['rss'])
    def status(self):return STATUS_ZOMBIE if self._stat()['state']=='Z' else 'running'
    def send_signal(self,sig):
        self._stat();os.kill(self.pid,sig)
    def children(self,recursive=False):
        allp=list(process_iter());out=[];ids={self.pid}
        while True:
            added=[]
            for p in allp:
                try:
                    if p.pid not in ids and p.ppid() in ids:added.append(p)
                except NoSuchProcess:pass
            if not added:break
            out+=added;ids.update(p.pid for p in added)
            if not recursive:break
        return out

def process_iter():
    for name in os.listdir('/proc'):
        if name.isdigit():
            try:yield Process(int(name))
            except (NoSuchProcess,AccessDenied):pass

def disk_usage(path):return shutil.disk_usage(path)
def virtual_memory():
    values=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    return SimpleNamespace(available=int(values['MemAvailable'].split()[0])*1024)
def cpu_percent(interval=1):
    def sample():
        v=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
        return sum(v),v[3]+v[4]
    total,idle=sample();time.sleep(interval);n_total,n_idle=sample();delta=n_total-total
    return 0. if delta<=0 else 100.*(delta-(n_idle-idle))/delta


def approved_chain(claim,parent_pid,parent_birth,module=None):
    ps=module if module is not None else __import__(__name__)
    if os.getppid()!=parent_pid or parent_pid==claim['pid']:raise PermissionError('independent lifeline parent required')
    parent=ps.Process(parent_pid)
    if parent.create_time()!=parent_birth or parent.ppid()!=claim['pid'] or ps.Process(claim['pid']).create_time()!=claim['wrapper_birth']:raise PermissionError('approved wrapper/lifeline birth chain')
