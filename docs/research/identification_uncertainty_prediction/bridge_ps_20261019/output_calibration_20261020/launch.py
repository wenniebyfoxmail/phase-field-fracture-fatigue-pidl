"""Only future production entry: independent watchdog covers complete controller lifetime.
No receipt exists in preparation. Main arms POSIX deadline before metadata/source admission.
"""
from pathlib import Path
import argparse,os,sys,time,json,signal,subprocess,resource,atexit
import warnings
warnings.simplefilter('error')
import package
from watchdog import arm_deadline,watch_process,verify_controller_exit,stop_group,atomic,first_stop
from runtime_guard import install,durable_write

def main(argv=None):
 started=time.monotonic();arm_deadline(1200)
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json'));p.add_argument('--approval-receipt',type=Path);a=p.parse_args(argv)
 code=Path(__file__).resolve().parent;cfg=package.load_config(code,a.config)
 # No run/resource/scientific access until the real later authority is provided.
 digest,auth=package.approval(code,cfg,a.approval_receipt)
 if sys.platform!='linux':raise PermissionError('GPUServer8 Linux CPU producer only')
 root=Path(cfg['run_root'])
 if code!=(root/'code').resolve():raise PermissionError('sealed producer code path')
 for name in ('watchdog_claim.json','run_claim.json','outputs','logs','cache','tmp','results.tar','results.tar.partial'):
  if (root/name).exists():raise FileExistsError('fresh new comparison only; no retry: '+name)
 root.mkdir(parents=True,exist_ok=True)
 for name in ('logs','cache','tmp'):(root/name).mkdir()
 atomic(root/'watchdog_claim.json',{'watchdog_pid':os.getpid(),'package_sha256':digest,'source_commit':auth['source_commit'],'started_monotonic':started,'deadline_monotonic':started+1200,'authority_scope':auth['scope'],'human_approved':auth['human_approved']})
 context={'child':None}
 def fatal(event,_killpg=os.killpg,_kill=signal.SIGKILL,_write=durable_write,_root=str(root),_context=context):
  c=_context['child']
  if c is not None and c.poll() is None:
   try:_killpg(c.pid,_kill)
   except ProcessLookupError:pass
  _write(_root+'/watchdog_receipt.json',{'status':'STOPPED_NO_RETRY','reason':'watchdog_lifetime_fatal','event':event})
 flag=install(root,on_fatal=fatal,event_name='watchdog_fatal.jsonl',seal_name='watchdog_exit.json')
 child=None;outcome={};reason=None
 try:
  allowed=os.sched_getaffinity(0)
  if not allowed:raise RuntimeError('no allowed CPU')
  chosen=min(allowed);os.sched_setaffinity(0,{chosen}) # Children inherit ONE logical CPU, including monitors.
  resource.setrlimit(resource.RLIMIT_AS,(8*2**30,8*2**30)) # Per-process virtual backstop, NOT combined RSS guarantee.
  atomic(root/'cpu_affinity.json',{'chosen_cpu':chosen,'policy':'minimum permitted logical CPU; not an exclusive reservation','allowed_before':sorted(allowed)})
  env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),MPLCONFIGDIR=str(root/'cache/matplotlib'),TORCH_HOME=str(root/'cache/torch'),PYTHONPYCACHEPREFIX=str(root/'cache/pycache'),PYTHONWARNINGS='error')
  with (root/'logs/controller.stdout').open('xb') as stdout,(root/'logs/controller.stderr').open('xb') as stderr:
   child=subprocess.Popen([sys.executable,str(code/'supervise.py'),'--config',str(a.config.resolve()),'--approval-receipt',str(a.approval_receipt.resolve())],cwd=code,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
   context['child']=child
   outcome=watch_process(child,root,started)
  reason=outcome['reason']
  if reason:raise RuntimeError(reason)
  controller=verify_controller_exit(root,child.pid)
  # Includes controller final hashing/manifest/receipt AND its actual process exit.
  if time.monotonic()-started>=1200:raise TimeoutError('whole lifecycle deadline before final receipt')
  completion={'status':'COMPLETE_CONTROLLER_EXIT_VERIFIED','watchdog_pid':os.getpid(),'controller_pid':child.pid,'package_sha256':digest,'source_commit':auth['source_commit'],'human_approved':auth['human_approved'],'scope':auth['scope'],'wall_seconds':time.monotonic()-started,'resources':outcome,'memory_semantics':'sampled conservative sum of process HWMs in controller session/group plus watchdog; not hard2GiB RSS cap','controller_receipt_status':controller['status']}
  atomic(root/'watchdog_completion_candidate.json',completion)
  atomic(root/'watchdog_receipt.json',completion)
  flag[0]=True # Guard/seal and alarm remain active through watchdog shutdown.
  return 0
 except BaseException as exc:
  reason=reason or type(exc).__name__+': '+str(exc);cleanup_error=None
  try:
   if child is not None:stop_group(child,outcome.get('members',()))
  except BaseException as cleanup:
   cleanup_error=type(cleanup).__name__+': '+str(cleanup)
  first_stop(root,reason,{'elapsed':time.monotonic()-started,'controller_pid':None if child is None else child.pid,'package_sha256':digest,'cleanup_error':cleanup_error,'last_case_context':'last_context.json; last observed context only, not a numerical cause'})
  atomic(root/'watchdog_receipt.json',{'status':'STOPPED_NO_RETRY','reason':reason,'cleanup_error':cleanup_error,'resources':outcome,'wall_seconds':time.monotonic()-started,'controller_pid':None if child is None else child.pid,'package_sha256':digest,'scope':auth['scope']})
  return 1

if __name__=='__main__':raise SystemExit(main())
