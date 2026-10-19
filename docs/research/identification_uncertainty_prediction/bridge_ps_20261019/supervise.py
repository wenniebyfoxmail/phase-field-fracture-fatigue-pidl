"""Future Linux-only controller. Never called in preparation; entire worker is bounded."""
from pathlib import Path
import argparse,json,os,signal,subprocess,sys,time,resource
import contract

def size(p):
 p=Path(p)
 if p.is_file():return p.stat().st_size
 total=0
 if not p.exists():return 0
 for x in p.rglob('*'):
  try:
   if x.is_file():total+=x.stat().st_size
  except FileNotFoundError:pass  # Owned atomic-write temp file was renamed during the scan.
 return total

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.producer.json'));p.add_argument('--approval-receipt',type=Path);args=p.parse_args(argv)
 code=Path(__file__).resolve().parent;cfg=contract.load_config(code,args.config);contract.check(code,cfg);digest,auth=contract.approval(code,cfg,args.approval_receipt)
 # Nothing above opens scientific files, creates outputs or checks producer resources.
 if sys.platform!='linux':raise RuntimeError('producer must be Linux; no machine fallback')
 r=Path(cfg['run_root'])
 if code!=(r/'code').resolve():raise ValueError('run must use its sealed code snapshot')
 r.mkdir(parents=True,exist_ok=True)
 with (r/'run_claim.json').open('x') as f:json.dump({'package_sha256':digest,'authority':auth,'controller_pid':os.getpid(),'source_code':str(code),'command':sys.argv},f)
 started=time.monotonic();child=None;peak=0;reason=None
 try:
  for name in ('outputs','results.tar.gz','results.tar.gz.partial'):
   if (r/name).exists():raise FileExistsError('fresh run required; no retry')
  for name in ('tmp','cache','logs'):(r/name).mkdir(exist_ok=True)
  env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(r/'tmp'),XDG_CACHE_HOME=str(r/'cache'),MPLCONFIGDIR=str(r/'cache/matplotlib'))
  def limits():resource.setrlimit(resource.RLIMIT_AS,(8*2**30,8*2**30))
  with (r/'logs/worker.log').open('wb') as log:
   child=subprocess.Popen([sys.executable,str(code/'worker.py'),'--run','--config',str(args.config.resolve()),'--approval-receipt',str(args.approval_receipt.resolve())],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
   while True:
    rc=child.poll();status=Path(f'/proc/{child.pid}/status');rss=0
    try:status_text=status.read_text()
    except (FileNotFoundError,ProcessLookupError):status_text=''
    if status_text:
     for line in status_text.splitlines():
      if line.startswith(('VmRSS:','VmHWM:')):rss=max(rss,int(line.split()[1])*1024)
    peak=max(peak,rss);reason=contract.budget_reason(time.monotonic()-started,peak,sum(size(r/n) for n in ('outputs','tmp','cache','logs')),max(size(r/'results.tar.gz'),size(r/'results.tar.gz.partial')),rc)
    if reason or rc is not None:break
    time.sleep(.25)
  if reason:raise RuntimeError(reason)
  if contract.read(r/'outputs/receipt.json')['status']!='COMPLETE':raise RuntimeError('worker lacked complete receipt')
  if not(r/'results.tar.gz').exists():raise RuntimeError('archive missing')
  contract.write(r/'controller_receipt.json',{'status':'COMPLETE','package_sha256':digest,'wall_seconds':time.monotonic()-started,'peak_rss_bytes':peak,'worker_pid':child.pid,'exit_code':0})
 except BaseException as exc:
  if child is not None and child.poll() is None:
   # Only the new child process group owned by this controller; never a shared-user kill.
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  contract.write(r/'controller_receipt.json',{'status':'STOPPED_NO_RETRY','reason':str(exc),'wall_seconds':time.monotonic()-started,'peak_rss_bytes':peak,'worker_pid':None if child is None else child.pid})
  raise
if __name__=='__main__':main()
