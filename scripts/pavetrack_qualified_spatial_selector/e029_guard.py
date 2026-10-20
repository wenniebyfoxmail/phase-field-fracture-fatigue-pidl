"""Task-scoped aggregate supervision; persistence failure never skips cleanup."""
import collections,os,threading,time
from pathlib import Path
import e029_support as c

class Guard:
    def __init__(self,cfg,out,start=None):
        self.cfg=cfg;self.out=Path(out);self.start=time.monotonic() if start is None else start
        self.counts=collections.Counter();self.peak=0;self.allocated=0;self.reserved=0;self.gpu=lambda:(0,0);self.lock=threading.RLock()
    def check(self):
        import psutil
        with self.lock:
            if hasattr(self,'expected_parent_pid') and os.getppid()!=self.expected_parent_pid:raise RuntimeError('owned controller disappeared')
            p=getattr(self,'process',None) or psutil.Process();rss=0
            for proc in ([p] if getattr(self,'self_only',False) else [p,*p.children(recursive=True)]):
                try:info=proc.memory_info()
                except psutil.NoSuchProcess:
                    if proc.pid==p.pid:raise
                    continue
                rss+=getattr(info,'peak_wset',info.rss)
            self.peak=max(self.peak,rss);a,r=self.gpu();self.allocated=max(self.allocated,a);self.reserved=max(self.reserved,r);b=self.cfg['budget']
            if b['wall_seconds'] is not None and time.monotonic()-self.start>b['wall_seconds']:raise TimeoutError('E029 global wall cap')
            if self.peak>b['RSS_bytes'] or self.allocated>b['GPU_allocated_bytes'] or self.reserved>b['GPU_reserved_bytes']:raise MemoryError('E029 memory cap')
            size=0
            for f in self.out.rglob('*'):
                try:
                    if f.is_file():size+=f.stat().st_size
                except FileNotFoundError:continue  # owned atomic .tmp rename/unlink; final inventory checks required files
            if size>b['output_bytes']:raise RuntimeError('E029 output cap')
    def take(self,k,n=1):
        with self.lock:
            if type(n) is not int or n<0 or k not in self.cfg['counts'] or self.counts[k]+n>self.cfg['counts'][k]:raise RuntimeError('count cap '+k)
            self.counts[k]+=n;self.check()
    def receipt(self):
        with self.lock:return dict(elapsed_seconds=time.monotonic()-self.start,peak_RSS_bytes=self.peak,peak_GPU_allocated_bytes=self.allocated,peak_GPU_reserved_bytes=self.reserved,counts=dict(self.counts))
    def fatal(self,ex,die=None):
        die=os._exit if die is None else die
        try:
            try:c.write(getattr(self,'note',self.out)/'watchdog_stop.json',dict(reason=repr(ex),resource=self.receipt()))
            except BaseException:
                try:os.write(2,('E029 first stop; persistence failed: '+repr(ex)+'\n').encode()[:4096])
                except BaseException:pass
        finally:
            try:
                if hasattr(self,'on_fatal'):self.on_fatal()
            finally:die(124)
    def watch(self):
        stop=threading.Event()
        def tick():
            while not stop.wait(.25):
                try:self.check()
                except BaseException as ex:self.fatal(ex)
        threading.Thread(target=tick,daemon=True).start();return stop
