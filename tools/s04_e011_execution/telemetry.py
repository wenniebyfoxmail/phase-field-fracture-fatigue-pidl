"""Worker-owned peak telemetry; never imported into the non-CUDA watcher."""
import math,resource,sys,threading,time
from control import bytes_under,write_json


class Reporter:
    def __init__(self,path,roots,limits,*,rss=None,clock=time.monotonic):
        self.path=path;self.roots=roots;self.limits=limits;self.clock=clock;self.cuda=None
        self.rss=rss or (lambda:int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform=='darwin' else 1024))
        self.peaks=dict(peak_rss_bytes=0,peak_task_bytes=0,peak_cuda_allocated=None,peak_cuda_reserved=None)
        self.lock=threading.Lock();self.end=threading.Event();self.thread=None;self.error=None
    def sample(self):
        with self.lock:
            try:
                rss=self.rss()
                if not isinstance(rss,(int,float)) or not math.isfinite(rss) or rss<0:raise RuntimeError('invalid RSS reading')
                self.peaks['peak_rss_bytes']=max(self.peaks['peak_rss_bytes'],rss)
                self.peaks['peak_task_bytes']=max(self.peaks['peak_task_bytes'],sum(bytes_under(p) for p in self.roots))
                state='boot'
                if self.cuda is not None:
                    allocated,reserved=self.cuda();state='active'
                    if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in [allocated,reserved]):raise RuntimeError('invalid CUDA peak reading')
                    self.peaks['peak_cuda_allocated']=max(self.peaks['peak_cuda_allocated'] or 0,allocated)
                    self.peaks['peak_cuda_reserved']=max(self.peaks['peak_cuda_reserved'] or 0,reserved)
                row=dict(monotonic=self.clock(),cuda_state=state,**self.peaks,error=self.error)
            except BaseException as exc:
                self.error=type(exc).__name__+': '+str(exc)
                row=dict(monotonic=self.clock(),cuda_state='failed',**self.peaks,error=self.error)
            write_json(self.path,row);return row
    def ratio(self):
        from control import validate_telemetry
        row=self.sample();validate_telemetry(row,self.clock(),self.limits,allow_boot=self.cuda is None)
        values=[row['peak_rss_bytes']/self.limits['host_RSS'],row['peak_task_bytes']/self.limits['fresh_root_outputs']]
        if self.cuda is not None:values +=[row['peak_cuda_allocated']/self.limits['GPU_allocated'],row['peak_cuda_reserved']/self.limits['GPU_reserved']]
        return max(values)
    def _loop(self):
        while not self.end.is_set():self.sample();self.end.wait(.5)
    def start(self):
        self.sample();self.thread=threading.Thread(target=self._loop,daemon=True);self.thread.start()
    def close(self):
        self.end.set()
        if self.thread is not None:self.thread.join(timeout=1)
        if self.thread is not None and self.thread.is_alive():raise RuntimeError('telemetry publisher did not exit')
        self.sample()
