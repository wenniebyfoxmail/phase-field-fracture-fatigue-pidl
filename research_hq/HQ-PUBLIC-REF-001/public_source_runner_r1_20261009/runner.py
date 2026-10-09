"""Producer-only entry point. No execution authorized by this repository."""
import argparse,json,os,platform,socket,sys,time,hashlib
from pathlib import Path
import numpy as np,torch,PIL
from core import sha,fit,final_evaluate,BudgetExpired
from data_lock import validate
HERE=Path(__file__).resolve().parent

def snapshot():
 return hashlib.sha256(json.dumps({p.name:sha(p) for p in sorted(HERE.glob('*.py'))},sort_keys=True).encode()).hexdigest()

def environment():
 import matplotlib
 return {'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'pillow':PIL.__version__,'matplotlib':matplotlib.__version__,'cuda':torch.version.cuda}

def gate(approval,lock_path):
 if platform.system()!='Linux' or not torch.cuda.is_available():raise RuntimeError('Producer Linux CUDA only; no Mac/CPU training')
 if not os.environ.get('CUDA_VISIBLE_DEVICES') or os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise RuntimeError('Explicit CUDA isolation and deterministic workspace required')
 if approval.get('execute') is not True or approval.get('producer_alias')!='taobo' or not approval.get('experiment_id') or not approval.get('user_authorization_reference'):raise RuntimeError('Missing execution authorization record')
 if approval.get('hostname')!=socket.gethostname():raise RuntimeError('Wrong producer')
 if approval.get('code_snapshot')!=snapshot() or approval.get('data_lock_sha256')!=sha(lock_path):raise RuntimeError('Unreviewed snapshot/lock')
 if approval.get('environment')!=environment():raise RuntimeError('Environment not frozen for approved run')

def main():
 p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--lock',required=True);p.add_argument('--roots',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 approved=json.loads(Path(a.approval).read_text());gate(approved,a.lock)
 out=Path(a.output).resolve();base=Path('/mnt/data2/drtao/wennie')
 if base not in out.parents:raise RuntimeError('Output outside approved data mount')
 out.mkdir(parents=True,exist_ok=False)
 receipt={'status':'prepared','code_snapshot':snapshot(),'environment':environment(),'pid':os.getpid(),'hostname':socket.gethostname(),'gpu':os.environ['CUDA_VISIBLE_DEVICES'],'approval':approved,'data_lock_sha256':sha(a.lock),'started_unix':time.time(),'output':str(out),'command':sys.argv}
 try:
  roots=json.loads(Path(a.roots).read_text());rows=validate(json.loads(Path(a.lock).read_text()),roots)
  torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
  receipt['status']='running';(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
  checkpoint=fit(rows,roots,out,torch.device('cuda:0'));receipt['checkpoint_sha256']=sha(checkpoint)
  final_evaluate(checkpoint,rows,roots,out,torch.device('cuda:0'));receipt['status']='succeeded'
 except BudgetExpired as e:receipt['status']='inconclusive_budget';receipt['error']=str(e)
 except BaseException as e:receipt['status']='failed';receipt['error']=repr(e);raise
 finally:
  receipt['ended_unix']=time.time();(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
