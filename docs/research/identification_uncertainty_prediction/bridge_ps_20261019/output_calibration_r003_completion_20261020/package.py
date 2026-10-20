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
def validate_authority(a,cfg,digest,config_sha256):
 required={'authority_kind','authority_source_thread_id','human_approved','authority_basis','approval_text','source_commit','package_sha256','config_sha256','run_id','run_root','budget','category_caps','scope','allow_scientific_admission','allow_old_input_native_target_read','allow_456_solves_once','max_attempts'}
 if not required<=set(a):raise PermissionError('incomplete exact execution authority')
 if not(a['authority_kind']=='hq_exact_admission_and_run' and a['authority_source_thread_id']=='01a10e77-8832-7371-b4cc-e5cbdadceced'
        and type(a['human_approved']) is bool and a['authority_basis']==('DIRECT_HUMAN' if a['human_approved'] else 'HQ_DELEGATED')
        and isinstance(a['approval_text'],str) and 0<len(a['approval_text'])<=8192
        and re.fullmatch('[a-f0-9]{40}',a['source_commit']) and a['package_sha256']==digest and a['config_sha256']==config_sha256
        and a['scope']=='FOUR_GROUP_COMPLETION_OF_R002' and a['run_id']==cfg['run_id'] and a['run_root']==cfg['run_root']
        and a.get('outer_groups')==cfg['outer_groups'] and a.get('prefix_binding_sha256')==sha(Path(__file__).with_name('prefix_binding.json'))
        and a['budget']==cfg['approved_budget'] and a['category_caps']==cfg['category_caps']
        and all(a[k] is True for k in ('allow_scientific_admission','allow_old_input_native_target_read','allow_456_solves_once')) and type(a['max_attempts']) is int and a['max_attempts']==1):
  raise PermissionError('execution authority does not bind exact new comparison')
 return a

def approval(code,cfg,path):
 digest=check(code,cfg)
 if cfg.get('enabled') is not True or cfg.get('approved_budget')!=cfg.get('proposed_budget'):raise PermissionError('candidate resource configuration not admitted')
 if path is None:raise PermissionError('Exact execution authority absent: launch candidate preparation only')
 if Path(path).resolve()!=Path(cfg['run_root'])/'execution_authority.json':raise PermissionError('authority must be the unique budget-counted run-root receipt')
 try:a=read(path)
 except FileNotFoundError:raise PermissionError('Exact execution authority absent: launch candidate preparation only') from None
 return digest,validate_authority(a,cfg,digest,sha(Path(code)/'config.json'))

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
