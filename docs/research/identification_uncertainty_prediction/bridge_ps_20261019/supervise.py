"""Future Linux-only controller. Never called in preparation; entire worker is bounded."""
from pathlib import Path
import argparse,json,os,signal,subprocess,sys,time,resource
import contract
from runtime_guard import child_failure,install,durable_write

def size(p):
 p=Path(p)
 try:
  if p.is_file():return p.stat().st_size
 except FileNotFoundError:return 0  # The owned archive temp file was atomically renamed.
 total=0
 if not p.exists():return 0
 for x in p.rglob('*'):
  try:
   if x.is_file():total+=x.stat().st_size
  except FileNotFoundError:pass  # Owned atomic-write temp file was renamed during the scan.
 return total


def utc():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def finish_record(status,digest,started_at,elapsed,peak,pid,reason=None,exit_code=None):
 return {'status':status,'package_sha256':digest,'started_at_utc':started_at,'ended_at_utc':utc(),
         'wall_seconds':elapsed,'peak_rss_bytes':peak,'worker_pid':pid,'reason':reason,'exit_code':exit_code}

def monitor_child(child,r,started):
 peak=0
 while True:
  rc=child.poll();status=Path(f'/proc/{child.pid}/status');rss=0
  try:status_text=status.read_text()
  except (FileNotFoundError,ProcessLookupError):status_text=''
  if status_text:
   for line in status_text.splitlines():
    if line.startswith(('VmRSS:','VmHWM:')):rss=max(rss,int(line.split()[1])*1024)
  peak=max(peak,rss);reason=child_failure(r,child.pid,rc,require_clean=rc is not None) or contract.budget_reason(time.monotonic()-started,peak,sum(size(r/n) for n in ('outputs','tmp','cache','logs')),max(size(r/'results.tar.gz'),size(r/'results.tar.gz.partial')),rc)
  if reason or rc is not None:break
  time.sleep(.25)
 return peak,reason


def install_controller_guard(r,digest,started_at,started,context):
 # Keep captured low-level functions available even during controller teardown.
 def reject(event,_r=str(r),_digest=digest,_started_at=started_at,_started=started,
            _context=context,_write=durable_write,_mono=time.monotonic,
            _gmtime=time.gmtime,_strftime=time.strftime,_killpg=os.killpg,
            _term=signal.SIGTERM,_kill=signal.SIGKILL,_timeout=subprocess.TimeoutExpired):
  child=_context.get('child')
  try:
   if child is not None and child.poll() is None:
    _killpg(child.pid,_term)
    try:child.wait(timeout=5)
    except _timeout:_killpg(child.pid,_kill);child.wait()
  finally:
   _write(_r+'/controller_receipt.json',{'status':'STOPPED_NO_RETRY',
      'package_sha256':_digest,'started_at_utc':_started_at,
      'ended_at_utc':_strftime('%Y-%m-%dT%H:%M:%SZ',_gmtime()),
      'wall_seconds':_mono()-_started,'worker_pid':None if child is None else child.pid,
      'reason':'controller_unraisable_or_thread_exception','fatal_event':event})
 install(r,on_fatal=reject,event_name='controller_fatal.jsonl')


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.producer.json'));p.add_argument('--approval-receipt',type=Path);args=p.parse_args(argv)
 code=Path(__file__).resolve().parent;cfg=contract.load_config(code,args.config);contract.check(code,cfg);digest,auth=contract.approval(code,cfg,args.approval_receipt)
 # Nothing above opens scientific files, creates outputs or checks producer resources.
 if sys.platform!='linux':raise RuntimeError('producer must be Linux; no machine fallback')
 r=Path(cfg['run_root'])
 if code!=(r/'code').resolve():raise ValueError('run must use its sealed code snapshot')
 r.mkdir(parents=True,exist_ok=True)
 started=time.monotonic();started_at=utc()
 with (r/'run_claim.json').open('x') as f:json.dump({'package_sha256':digest,'authority':auth,'controller_pid':os.getpid(),'started_at_utc':started_at,'source_code':str(code),'command':sys.argv},f)
 child=None;peak=0;reason=None
 try:
  for name in ('outputs','results.tar.gz','results.tar.gz.partial'):
   if (r/name).exists():raise FileExistsError('fresh run required; no retry')
  for name in ('tmp','cache','logs'):(r/name).mkdir(exist_ok=True)
  context={'child':None};install_controller_guard(r,digest,started_at,started,context)
  env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(r/'tmp'),XDG_CACHE_HOME=str(r/'cache'),MPLCONFIGDIR=str(r/'cache/matplotlib'))
  def limits():resource.setrlimit(resource.RLIMIT_AS,(8*2**30,8*2**30))
  with (r/'logs/worker.log').open('wb') as log, (r/'logs/worker.stderr').open('xb') as error_log:
   child=subprocess.Popen([sys.executable,str(code/'runtime_guard.py'),'--root',str(r),'--target',str(code/'worker.py'),'--','--run','--config',str(args.config.resolve()),'--approval-receipt',str(args.approval_receipt.resolve())],cwd=code,env=env,stdout=log,stderr=error_log,start_new_session=True,preexec_fn=limits)
   context['child']=child
   peak,reason=monitor_child(child,r,started)
  if reason:raise RuntimeError(reason)
  reason=child_failure(r,child.pid,child.returncode,require_clean=True)
  if reason:raise RuntimeError(reason)
  if contract.read(r/'outputs/receipt.json')['status']!='CANDIDATE_COMPLETE_REQUIRES_CONTROLLER':raise RuntimeError('worker lacked complete receipt')
  if not(r/'results.tar.gz').exists():raise RuntimeError('archive missing')
  complete=finish_record('COMPLETE',digest,started_at,time.monotonic()-started,peak,child.pid,exit_code=0)
  complete['worker_exit_evidence']=contract.read(r/'logs/runtime_exit.json')
  complete['worker_stderr_bytes']=(r/'logs/worker.stderr').stat().st_size
  contract.write(r/'controller_receipt.json',complete)
 except BaseException as exc:
  if child is not None and child.poll() is None:
   # Only the new child process group owned by this controller; never a shared-user kill.
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  contract.write(r/'controller_receipt.json',finish_record('STOPPED_NO_RETRY',digest,started_at,time.monotonic()-started,peak,None if child is None else child.pid,reason=str(exc)))
  raise
if __name__=='__main__':main()
