"""Mac owned-tree user-space RSS/time guard. No AS claim; no science imports."""
import os,signal,threading,time,resource
import psutil
class GuardStop(RuntimeError):pass
class OwnedGuard:
 def __init__(self,seconds,rss_bytes=512*1024**2,interval=.1):
  assert 0<interval<=.2
  self.root=psutil.Process();self.root_id=(self.root.pid,self.root.create_time());self.begin=time.monotonic();self.end=self.begin+seconds;self.cap=rss_bytes;self.interval=interval;self.known={};self.direct={};self.ready=threading.Event();self.done=threading.Event();self.failure=None;self.peak_RSS=0;self.peak_VM=0;self.max_gap=0.;self.samples=0;self.delay_over_interval=0.;self.peak_CPU=0.;self.bindings=[];self.identity_refusals=[];self.path_limits=[];self.tree_limit=None;self.peak_output_bytes=0
 def handler(self,sig,frame):raise GuardStop(self.failure or 'owned wall timer')
 def start(self):
  signal.signal(signal.SIGTERM,self.handler);signal.signal(signal.SIGALRM,self.handler);signal.setitimer(signal.ITIMER_REAL,max(.01,self.end-time.monotonic()))
  self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
  if not self.ready.wait(1) or self.failure:raise GuardStop(self.failure or 'guardian not armed')
  return self
 def bind(self,p,commands,cwd):
  try:
   q=psutil.Process(p.pid);assert q.ppid()==self.root.pid and q.create_time()>=self.root.create_time()
   key=(q.pid,q.create_time());command=q.cmdline();current_cwd=q.cwd();self.known[q.pid]=dict(key=key,command=command,cwd=current_cwd)
   assert command in commands and current_cwd==str(cwd)
   self.direct[q.pid]=(key,commands,str(cwd));self.bindings.append(dict(pid=q.pid,created=q.create_time(),command=command,cwd=q.cwd(),elapsed=time.time()-q.create_time()))
  except psutil.NoSuchProcess:
   if p.poll() is None:raise GuardStop('unbound child alive/unknown')
 def matching(self,q,info):
  if q.create_time()!=info['key'][1]:return False
  if q.pid in self.direct:
   _,allowed,cwd=self.direct[q.pid];return q.cmdline() in allowed and q.cwd()==cwd
  return q.cmdline()==info['command'] and q.cwd()==info['cwd']
 def terminate_owned(self):
  try:self._terminate_owned()
  except BaseException as e:self.identity_refusals.append(dict(reason='owned stop could not verify/complete',error=type(e).__name__+': '+str(e)))
 def _terminate_owned(self):
  targets=[]
  for pid,info in list(self.known.items()):
   try:
    q=psutil.Process(pid)
    if not self.matching(q,info):self.identity_refusals.append(dict(pid=pid,reason='PID/time/command/cwd no longer matches'));continue
    targets.append(q)
   except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
  for q in reversed(targets):
   try:q.terminate()
   except psutil.NoSuchProcess:pass
  _,alive=psutil.wait_procs(targets,timeout=.5)
  for q in alive:
   try:
    if self.matching(q,self.known[q.pid]):q.kill()
    else:self.identity_refusals.append(dict(pid=q.pid,reason='KILL identity no longer matches'))
   except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
  psutil.wait_procs(alive,timeout=.5)
 def run(self):
  last=None
  try:
   while not self.done.is_set():
    now=time.monotonic()
    if last is not None:self.max_gap=max(self.max_gap,now-last);self.delay_over_interval=max(self.delay_over_interval,now-last-self.interval)
    last=now;rows=[self.root]+self.root.children(recursive=True);rss=vm=cpu=0
    for q in rows:
     try:
      key=(q.pid,q.create_time())
      if q.pid!=self.root.pid and q.pid not in self.known:self.known[q.pid]=dict(key=key,command=q.cmdline(),cwd=q.cwd())
      with q.oneshot():m=q.memory_info();c=q.cpu_times();rss+=m.rss;vm+=m.vms;cpu+=c.user+c.system
     except (psutil.NoSuchProcess,psutil.ZombieProcess):continue
    self.peak_RSS=max(self.peak_RSS,rss);self.peak_VM=max(self.peak_VM,vm);self.peak_CPU=max(self.peak_CPU,cpu);self.samples+=1;self.ready.set()
    if rss>self.cap:raise GuardStop('owned RSS sampling limit')
    for path,limit in self.path_limits:
     if path.exists() and path.stat().st_size>limit:raise GuardStop('sampled return stream size limit')
    if self.tree_limit is not None:
     path,limit=self.tree_limit;size=sum(p.stat().st_size for p in path.rglob('*') if p.is_file());self.peak_output_bytes=max(self.peak_output_bytes,size)
     if size>limit:raise GuardStop('sampled owned output size limit')
    if now>=self.end:raise GuardStop('owned wall timeout')
    self.done.wait(self.interval)
  except BaseException as e:
   self.failure=str(e);self.ready.set()
   try:self.terminate_owned()
   finally:os.kill(self.root.pid,signal.SIGTERM)
 def close(self):
  self.done.set();self.thread.join(timeout=2);signal.setitimer(signal.ITIMER_REAL,0)
  if self.thread.is_alive():raise GuardStop('guardian did not close')
 def report(self):return dict(failure=self.failure,samples=self.samples,interval_seconds=self.interval,max_sample_gap_seconds=self.max_gap,max_delay_above_interval_seconds=max(0,self.delay_over_interval),peak_owned_RSS_bytes=self.peak_RSS,peak_owned_VM_bytes=self.peak_VM,peak_sampled_owned_CPU_seconds=self.peak_CPU,child_bindings=self.bindings,identity_refusals=self.identity_refusals,peak_owned_output_bytes=self.peak_output_bytes,Mac_AS_limit_required=False,RSS_monitor_kind='user-space sampled, not kernel hard RSS guarantee')
