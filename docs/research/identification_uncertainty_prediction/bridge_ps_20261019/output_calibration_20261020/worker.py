"""Future disabled worker. Standalone invocation cannot bypass authority/parent claim."""
from pathlib import Path
import argparse,os,json,sys,tarfile
import package

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json'));p.add_argument('--approval-receipt',type=Path);a=p.parse_args(argv)
 code=Path(__file__).resolve().parent;cfg=package.load_config(code,a.config);digest,auth=package.approval(code,cfg,a.approval_receipt)
 if not a.run or sys.platform!='linux':raise PermissionError('future Linux producer only')
 r=Path(cfg['run_root']);claim=package.read(r/'run_claim.json')
 if code!=(r/'code').resolve() or claim.get('controller_pid')!=os.getppid() or claim.get('package_sha256')!=digest or os.getpgid(0)!=claim.get('controller_pid') or os.getsid(0)!=claim.get('controller_pid'):raise PermissionError('bounded parent/code claim')
 package.write(r/'last_context.json',{'stage':'dependency_admission','case':None,'missing_reason':'no scientific row or arrays opened yet'})
 from admission import admit
 admit(code,cfg,r)
 import warnings
 warnings.simplefilter('error')
 import numpy as np
 import torch
 torch.set_num_threads(1);torch.set_num_interop_threads(1)
 if torch.get_num_threads()!=1 or torch.get_num_interop_threads()!=1:raise RuntimeError('torch thread cap')
 np.seterr(all='raise')
 import engine,producer_data,evidence,figures
 for module in (engine,producer_data,evidence,figures,engine.base,producer_data.state):
  if Path(module.__file__).resolve().parent!=code:raise RuntimeError('unsealed transitive module resolution')
 audit=evidence.Audit(r);sink=None
 try:
  audit.enter('verified_authority',source_commit=auth['source_commit'],package_sha256=digest)
  data=producer_data.load(code,audit);sink=evidence.DiskSink(r/'outputs',data)
  counts=engine.run_comparison(data,sink,audit,(10,40),expected_groups=19,expected_cases=1144)
  sink.close();audit.enter('future_new_package_figures_only');figures.render(r/'outputs')
  audit.enter('verify_evidence_and_package')
  # Full hash inventory is inside the scientific evidence archive; no source input copied silently.
  files=[]
  for f in sorted((r/'outputs').rglob('*')):
   if f.is_file():files.append({'path':str(f.relative_to(r/'outputs')),'bytes':f.stat().st_size,'sha256':package.sha(f)})
  evidence.write(r/'outputs/receipt.json',{'status':'CANDIDATE_COMPLETE_REQUIRES_CONTROLLER','counts':counts,'package_sha256':digest,'source_commit':auth['source_commit'],'files_before_receipt':files,'limits':'exposed groups; unknown specimen independence; release steps/current anchor; original R003 contract defect retained; no identifiability or road claim'},True)
  audit.enter('archive')
  # Uncompressed tar: resource plan does not rely on beneficial scientific compression.
  with (r/'results.tar.partial').open('xb') as f:
   with tarfile.open(fileobj=f,mode='w') as tar:
    lock=package.read(code/'package_lock.json')
    for name in sorted(list(lock['files'])+['package_lock.json']):tar.add(code/name,arcname='code/'+name)
    tar.add(r/'outputs',arcname='outputs')
  (r/'results.tar.partial').replace(r/'results.tar')
  package.write(r/'archive_receipt.json',{'format':'uncompressed tar','bytes':(r/'results.tar').stat().st_size,'sha256':package.sha(r/'results.tar')})
 except BaseException as exc:
  audit.fail(exc);raise
 finally:
  if sink is not None:sink.close()

if __name__=='__main__':main()
