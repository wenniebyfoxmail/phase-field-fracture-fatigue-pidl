"""Append+fsync starts BEFORE work; an external kill leaves an unmatched start."""
from time import perf_counter,time
from hybrid_producer_common import append_event

class EvidenceWriteError(Exception):
    pass

class PersistentWorkTrace:
    def __init__(self,path,phase,step):
        self.path=path;self.phase=phase;self.step=step;self.sequence=0
    def emit(self,event):
        try:append_event(self.path,dict(phase=self.phase,step=self.step,epoch=time(),monotonic=perf_counter(),**event))
        except Exception as exc:raise EvidenceWriteError('durable work trace write failed') from exc
    def call(self,kind,fn):
        n=self.sequence;self.sequence+=1;t=perf_counter();self.emit(dict(event='start',block_id=n,kind=kind))
        try:
            value=fn()
        except BaseException as exc:
            self.emit(dict(event='end',block_id=n,kind=kind,status='failed',error=type(exc).__name__,wall_seconds=perf_counter()-t));raise
        self.emit(dict(event='end',block_id=n,kind=kind,status='returned',wall_seconds=perf_counter()-t));return value
