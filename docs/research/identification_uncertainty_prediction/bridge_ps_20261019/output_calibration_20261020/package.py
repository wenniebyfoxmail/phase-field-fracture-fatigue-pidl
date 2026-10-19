"""Source-only package binding and default denial. No numpy/data imports."""
from pathlib import Path
import hashlib,json,re,time,importlib.metadata

def read(p):
 with Path(p).open() as f:return json.load(f)
def write(p,obj):
 from runtime_guard import durable_write
 durable_write(str(p),obj)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load_config(code,path):
 if Path(path).resolve()!=Path(code).resolve()/'config.json':raise PermissionError('only sealed local config')
 return read(path)
def check(code,cfg=None):
 code=Path(code);lock=read(code/'package_lock.json')
 for n,h in lock['files'].items():
  if Path(n).name!=n or sha(code/n)!=h:raise ValueError('sealed source mismatch '+n)
 return hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def approval(code,cfg,path):
 digest=check(code,cfg)
 if cfg.get('enabled') is not True or cfg.get('approved_budget')!=cfg.get('proposed_budget'):raise PermissionError('DISABLED: preparation only; resource proposal and scientific execution not approved')
 if not path:raise PermissionError('exact later authority absent')
 a=read(path)
 if not(a.get('package_sha256')==digest and a.get('scope')=='NEW_FIXED_ALPHA_OUTPUT_CALIBRATION' and a.get('source_commit') and re.fullmatch('[a-f0-9]{40}',a['source_commit']) and a.get('budget')==cfg['approved_budget'] and a.get('run_root')==cfg.get('run_root') and a.get('allow_old_inputs_native_targets_and_2166_solves') is True and a.get('approval_text')):raise PermissionError('exact later execution authority missing')
 return digest,a

def verify_dependencies(cfg):
 for package,version in cfg['dependencies'].items():
  if importlib.metadata.version(package)!=version:raise RuntimeError('dependency mismatch '+package)

def budget_reason(elapsed,rss,total_bytes,archive_bytes,returncode):
 # Proposal only. Disabled config prevents this controller from being admitted today.
 if elapsed>1200:return 'wall_budget'
 if rss>2*2**30:return 'rss_budget'
 if total_bytes>1536*2**20:return 'total_storage_budget'
 if archive_bytes>700*2**20:return 'archive_budget'
 if returncode is not None and returncode!=0:return 'worker_failed'
 return None

from resource_contract import storage_reason
