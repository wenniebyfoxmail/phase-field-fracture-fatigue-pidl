"""One local two-mode child fixture, no SSH/data/model."""
import json,os,resource,subprocess,sys,time
from pathlib import Path
from local_owned_rss_guard import OwnedGuard,GuardStop
resource.setrlimit(resource.RLIMIT_CPU,(5,5));start=time.monotonic();rows=[];root=Path.cwd().resolve()
for mode in ['RSS','timeout']:
 code="import resource,time;resource.setrlimit(resource.RLIMIT_CPU,(1,1));"+("buf=bytearray(64*1024**2);time.sleep(5)" if mode=='RSS' else 'time.sleep(5)')
 cap=512*1024**2 if mode=='timeout' else __import__('psutil').Process().memory_info().rss+40*1024**2
 g=OwnedGuard(.6 if mode=='timeout' else 3,rss_bytes=cap).start();p=None;error=None
 try:
  cmd=[sys.executable,'-B','-c',code];p=subprocess.Popen(cmd,cwd=root,start_new_session=True);g.bind(p,[cmd],root);p.wait(timeout=4)
 except GuardStop as e:error=str(e)
 finally:
  g.terminate_owned()
  if p is not None:p.wait(timeout=1)
  g.close()
 assert error is not None and ('RSS' in error if mode=='RSS' else ('timeout' in error or 'timer' in error)),(mode,error)
 assert p.poll() is not None
 rows.append(dict(mode=mode,error=error,child_exit=p.returncode,own_child_gone=True,monitor=g.report()))
result=dict(status='PASS_one_two_mode_owned_child_fixture',cases=rows,wall_seconds=time.monotonic()-start,total_CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,fixture_CPU_hard_allocation_seconds=7,new_SSH_arrays_science=0)
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
