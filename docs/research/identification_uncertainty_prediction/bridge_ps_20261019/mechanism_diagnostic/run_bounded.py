"""Local derivative arithmetic only; own-child limits, no producer/network operations."""
from pathlib import Path
import os,sys,subprocess,time,json,signal
BASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003')
out=BASE/'mechanism_diagnostic_20261019';out.mkdir(exist_ok=False)
start=time.monotonic();peak=0;reason=None
with (out/'intent.json').open('x') as f:json.dump({'scope':'SAVED_DERIVATIVES_ARITHMETIC_ONLY','wall_seconds':600,'rss_gib':2,'max_output_mib':100,'threads':1,'gpu':0},f)
env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',MPLCONFIGDIR=str(out/'mplcache'))
with (out/'stdout.log').open('wb') as log,(out/'stderr.log').open('wb') as err:
 p=subprocess.Popen(['/Users/wenxiaofang/miniconda3/bin/python3',str(Path(__file__).with_name('analyse.py')),'--output',str(out)],env=env,stdout=log,stderr=err,start_new_session=True)
 while True:
  rc=p.poll()
  if rc is None:
   q=subprocess.run(['/bin/ps','-p',str(p.pid),'-o','rss='],capture_output=True,text=True,timeout=2)
   if q.stdout.strip():peak=max(peak,int(q.stdout.strip())*1024)
  size=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
  if time.monotonic()-start>600:reason='wall_budget'
  elif peak>2*2**30:reason='rss_budget'
  elif size>100*2**20:reason='output_budget'
  elif (out/'stderr.log').stat().st_size:reason='stderr_or_warning'
  elif rc is not None and rc!=0:reason='arithmetic_failed'
  if reason or rc is not None:break
  time.sleep(.25)
 if reason and p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
rc=p.wait();size=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
if not reason and rc!=0:reason='arithmetic_failed'
if not reason and (out/'stderr.log').stat().st_size:reason='stderr_or_warning'
receipt={'status':'STOPPED_NO_ALTERNATE_DATA' if reason else 'COMPLETE_DERIVATIVE_ARITHMETIC','reason':reason,'pid':p.pid,'exit_code':rc,'wall_seconds':time.monotonic()-start,'peak_rss_bytes':peak,'new_output_bytes':size,'threads':1,'gpu':0,'scientific_fit_or_forward':False,'ssh':False,'raw_native_inputs':False}
with (out/'bounded_receipt.json').open('w') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt));raise SystemExit(bool(reason))
