"""Worker deadline notifications use kernel IPC before evidence filesystem IO."""
import json,os,socket
from time import perf_counter


def notify(event,step):
    fd=os.environ.get('HYBRID_GUARD_FD')
    if fd is None:raise RuntimeError('independent deadline IPC absent')
    s=socket.socket(fileno=os.dup(int(fd)))
    s.settimeout(.1)
    try:s.send(json.dumps(dict(event=event,step=step,started=perf_counter(),finished=perf_counter())).encode())
    finally:s.close()
