"""Future-only saved-derivative arithmetic controller; import has no side effects."""
from pathlib import Path
import argparse,os,sys,subprocess,time,json,signal,stat
import diagnostic_contract as contract

def output_size(out):
 total=0
 for path in out.rglob('*'):
  try:info=path.stat()
  except FileNotFoundError:continue # Atomic publication may rename a temporary file after enumeration.
  if stat.S_ISREG(info.st_mode):total+=info.st_size
 return total

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--authority-receipt',type=Path);args=p.parse_args(argv)
 out=args.output.resolve();folder=Path(__file__).parent;digest=contract.package_id(folder)
 permission=contract.authority(args.authority_receipt,digest,out) # Must precede mkdir, subprocess and data access.
 out.mkdir(exist_ok=False)
 contract.persist(out/'intent.json',{'scope':'SAVED_DERIVATIVES_ARITHMETIC_ONLY','budget':contract.BUDGET,'authority':permission})
 contract.persist(out/'controller_claim.json',{'parent_pid':os.getpid(),'package_sha256':digest})
 start=time.monotonic();peak=0;reason=None;rc=None;pchild=None
 env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',MPLCONFIGDIR=str(out/'mplcache'))
 try:
  with (out/'stdout.log').open('xb') as log,(out/'stderr.log').open('xb') as err:
   pchild=subprocess.Popen([sys.executable,str(folder/'analyse.py'),'--output',str(out),'--authority-receipt',str(args.authority_receipt.resolve())],env=env,stdout=log,stderr=err,start_new_session=True)
   while True:
    rc=pchild.poll()
    if rc is None:
     q=subprocess.run(['/bin/ps','-p',str(pchild.pid),'-o','rss='],capture_output=True,text=True,timeout=2)
     if q.stdout.strip():peak=max(peak,int(q.stdout.strip())*1024)
    size=output_size(out)
    if time.monotonic()-start>600:reason='wall_budget'
    elif peak>2*2**30:reason='rss_budget'
    elif size>100*2**20:reason='output_budget'
    elif (out/'stderr.log').stat().st_size:reason='stderr_or_warning'
    elif rc is not None and rc!=0:reason='arithmetic_failed'
    if reason or rc is not None:break
    time.sleep(.25)
 except BaseException as exc:
  reason='controller_exception:'+type(exc).__name__+':'+str(exc)[:256]
 finally:
  if pchild is not None:
   if pchild.poll() is None:
    os.killpg(pchild.pid,signal.SIGTERM)
    try:pchild.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(pchild.pid,signal.SIGKILL);pchild.wait()
   rc=pchild.wait()
 if not reason and time.monotonic()-start>600:reason='wall_budget'
 if not reason and rc!=0:reason='arithmetic_failed'
 if not reason and (out/'stderr.log').stat().st_size:reason='stderr_or_warning'
 size=output_size(out)
 if not reason and size>100*2**20:reason='output_budget'
 if not reason and not (out/'arithmetic_receipt.json').is_file():reason='missing_arithmetic_receipt'
 receipt={'status':'STOPPED_NO_ALTERNATE_DATA' if reason else 'COMPLETE_DERIVATIVE_ARITHMETIC','reason':reason,'pid':None if pchild is None else pchild.pid,'exit_code':rc,'wall_seconds':time.monotonic()-start,'peak_rss_bytes':peak,'new_output_bytes':size,'budget':contract.BUDGET,'source_commit':permission['source_commit'],'package_sha256':digest,'last_check':'last_check.json','failure':'failure.json if raised by analyser','scientific_fit_or_forward':False,'ssh':False,'raw_native_inputs':False}
 contract.persist(out/'bounded_receipt.json',receipt);print(json.dumps(receipt));return int(bool(reason))

if __name__=='__main__':raise SystemExit(main())
