"""Reuse psutil aggregate supervision and external managed parent hard-stop."""
import collections,json,os,threading,time
from pathlib import Path
import e029_support as c
class Guard:
    def __init__(self,cfg,out,start=None):
        self.cfg=cfg;self.out=Path(out);self.start=time.monotonic() if start is None else start;self.counts=collections.Counter();self.peak=0;self.allocated=0;self.reserved=0;self.gpu=lambda:(0,0)
    def check(self):
        import psutil
        p=psutil.Process();rss=0
        for proc in [p,*p.children(recursive=True)]:
            try:rss+=getattr(proc.memory_info(),'peak_wset',proc.memory_info().rss)
            except psutil.NoSuchProcess:continue
        self.peak=max(self.peak,rss);a,r=self.gpu();self.allocated=max(self.allocated,a);self.reserved=max(self.reserved,r);b=self.cfg['budget']
        if time.monotonic()-self.start>b['wall_seconds']:raise TimeoutError('E029 global wall cap')
        if self.peak>b['RSS_bytes'] or self.allocated>b['GPU_allocated_bytes'] or self.reserved>b['GPU_reserved_bytes']:raise MemoryError('E029 memory cap')
        if sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file())>b['output_bytes']:raise RuntimeError('E029 output cap')
    def take(self,k,n=1):
        self.counts[k]+=n
        if k not in self.cfg['counts'] or self.counts[k]>self.cfg['counts'][k]:raise RuntimeError('count cap '+k)
        self.check()
    def receipt(self):
        return dict(elapsed_seconds=time.monotonic()-self.start,peak_RSS_bytes=self.peak,peak_GPU_allocated_bytes=self.allocated,peak_GPU_reserved_bytes=self.reserved,counts=dict(self.counts))
    def watch(self):
        stop=threading.Event()
        def tick():
            while not stop.wait(.25):
                try:self.check()
                except BaseException as ex:
                    try:
                        c.write(getattr(self,'note',self.out)/'watchdog_stop.json',dict(reason=repr(ex),resource=self.receipt()))
                        if hasattr(self,'on_fatal'):self.on_fatal()
                    finally:os._exit(124)
        threading.Thread(target=tick,daemon=True).start();return stop
