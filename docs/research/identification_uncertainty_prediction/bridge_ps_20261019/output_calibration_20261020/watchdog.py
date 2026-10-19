"""Independent controller-process-group watchdog, stdlib only.
Includes controller final I/O after worker exit. No scientific imports or data loaders.
RSS is sampled conservative sum of owned process HWMs plus watchdog HWM, NOT an OS RSS limit.
"""
from pathlib import Path
import os,json,time,signal,subprocess,resource,sys
from resource_contract import storage,storage_reason,LIMITS,TOTAL
from runtime_guard import durable_write

class DeadlineExceeded(TimeoutError):
 def __init__(self,message):
  super().__init__(message);self.trigger_monotonic=time.monotonic();self.trigger_unix=time.time()

def arm_deadline(seconds):
 def alarm(signum,frame):raise DeadlineExceeded('whole_lifecycle_wall_deadline')
 signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.001,seconds))

def atomic(path,payload):
 path=Path(path);temp=path.with_suffix(path.suffix+'.partial');durable_write(str(temp),payload);temp.replace(path)

def first_stop(root,reason,context):
 p=Path(root)/'watchdog_first_stop.json'
 # Exclusive first stop: no later error/timeout can erase the initial reason.
 try:
  with p.open('x') as f:json.dump({'reason':reason,**context},f);f.write('\n');f.flush();os.fsync(f.fileno())
 except FileExistsError:pass

def proc_records():
 """Linux process-group/session snapshots. Other users' processes are never signalled."""
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   text=(p/'stat').read_text();right=text.rfind(')');fields=text[right+2:].split()
   pid=int(p.name);pgid=int(fields[2]);sid=int(fields[3]);start_ticks=int(fields[19])
   rss=hwm=0
   for line in (p/'status').read_text().splitlines():
    if line.startswith('VmRSS:'):rss=int(line.split()[1])*1024
    elif line.startswith('VmHWM:'):hwm=int(line.split()[1])*1024
   yield {'pid':pid,'pgid':pgid,'sid':sid,'start_ticks':start_ticks,'state':fields[0],'rss':rss,'hwm':hwm}
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue

def combined_memory(records,controller_pgid,watchdog_pid):
 owned=[r for r in records if r['pid']==watchdog_pid or (r['pgid']==controller_pgid and r['sid']==controller_pgid)]
 return sum(max(r['rss'],r['hwm']) for r in owned),owned

def sample_memory(pgid):
 records=list(proc_records())
 if not any(r['pid']==os.getpid() for r in records):raise RuntimeError('watchdog /proc memory observation missing')
 return combined_memory(records,pgid,os.getpid())

def stop_group(child,owned_members=(),*,records_provider=None,cleanup_timeout=5):
 # Retained PID/start-time/SID identities remain usable if the monitor is interrupted.
 # A reaped controller is NOT evidence that its known worker/helpers stopped.
 provider=records_provider if records_provider is not None else (proc_records if sys.platform=='linux' else None)
 known={(r['pid'],r['start_ticks']) for r in owned_members if r['pgid']==child.pid and r['sid']==child.pid}
 def group_records():return [] if provider is None else [r for r in provider() if r['pgid']==child.pid and r['sid']==child.pid]
 before=group_records();controller_live=child.poll() is None
 verified=any((r['pid'],r['start_ticks']) in known for r in before)
 if controller_live or verified:
  known.update((r['pid'],r['start_ticks']) for r in before)
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  except PermissionError as denied:
   # Teardown race is accepted ONLY if the controller exits and no active owned group remains.
   try:child.wait(timeout=.2)
   except subprocess.TimeoutExpired:raise denied
   if any(r.get('state')!='Z' for r in group_records()):raise denied
 elif any(r.get('state')!='Z' for r in before):
  raise RuntimeError('unverified remaining session members; cleanup not established')
 exit_code=child.wait(timeout=cleanup_timeout)
 if provider is None:
  if known:raise RuntimeError('known descendant verification unavailable')
  return {'controller_exit_code':exit_code,'known_descendants_verified':None,'note':'artificial non-Linux controller-only cleanup; no production claim'}
 deadline=time.monotonic()+cleanup_timeout
 while True:
  remaining=[r for r in provider() if r.get('state')!='Z' and ((r['pgid']==child.pid and r['sid']==child.pid) or (r['pid'],r['start_ticks']) in known)]
  if not remaining:return {'controller_exit_code':exit_code,'known_descendants_verified':True,'verified_identity_count':len(known),'remaining_active_members':[]}
  if time.monotonic()>=deadline:raise RuntimeError('owned descendants still active after KILL: '+str([r['pid'] for r in remaining]))
  time.sleep(.02)

def lifecycle_error(root):
 root=Path(root)
 for name in ('runtime_fatal.jsonl','controller_fatal.jsonl'):
  if (root/'logs'/name).exists():return name
 p=root/'launch.stderr'
 if p.exists() and p.stat().st_size:return 'launch_stderr_nonempty'
 for name in ('worker.stderr','controller.stderr'):
  p=root/'logs'/name
  if p.exists() and p.stat().st_size:return name+'_nonempty'
 return None

def watch_process(child,root,started,*,wall=1200,rss_cap=2*2**30,sampler=sample_memory,interval=.25,state=None):
 """Actual shared outer monitor; artificial subprocess fixtures use short wall limits."""
 root=Path(root);peak=0;last_members=[];state={} if state is None else state
 while True:
  elapsed=time.monotonic()-started
  if elapsed>=wall:return {'reason':'whole_lifecycle_wall_deadline','peak_combined_hwm_bytes':peak,'elapsed':elapsed,'members':last_members}
  rss,members=sampler(child.pid);state['members']=members;peak=max(peak,rss);last_members=members
  state.update(peak_combined_hwm_bytes=peak,last_observation_monotonic=time.monotonic(),last_observation_unix=time.time())
  reason=lifecycle_error(root) or ('combined_process_rss_budget' if rss>rss_cap else None) or storage_reason(root)
  if reason:return {'reason':reason,'peak_combined_hwm_bytes':peak,'elapsed':elapsed,'members':members}
  rc=child.poll()
  if rc is not None:return {'reason':('controller_exited_with_owned_descendants' if any(r['pid'] not in (os.getpid(),child.pid) for r in members) else None) if rc==0 else 'controller_exit_nonzero','exit_code':rc,'peak_combined_hwm_bytes':peak,'elapsed':elapsed,'members':members}
  atomic(root/'watchdog_progress.json',{'elapsed':elapsed,'combined_hwm_bytes':rss,'peak_combined_hwm_bytes':peak,'members':members})
  time.sleep(min(interval,max(.001,wall-elapsed)))

def verify_controller_exit(root,pid):
 root=Path(root)
 with (root/'controller_receipt.json').open() as f:r=json.load(f)
 with (root/'logs/controller_exit.json').open() as f:seal=json.load(f)
 if r.get('status')!='CANDIDATE_COMPLETE_REQUIRES_WATCHDOG' or seal.get('pid')!=pid or seal.get('status')!='RETURNED_AND_EXIT_CALLBACKS_COMPLETE':raise RuntimeError('controller post-exit completion/seal identity')
 if lifecycle_error(root):raise RuntimeError('late controller/worker failure')
 # Reserve room for final watchdog seal/receipt/fatal record, without increasing any cap.
 counts=storage(root);reserve=65536
 if counts['metadata']+reserve>LIMITS['metadata'] or sum(counts.values())+reserve>TOTAL:raise RuntimeError('closure evidence reserve budget')
 return r
