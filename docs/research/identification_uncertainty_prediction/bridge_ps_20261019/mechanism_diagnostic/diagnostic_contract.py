"""Precision provenance, bounded pre-check evidence and future-only authority. Stdlib only."""
from pathlib import Path
import hashlib,json,math,os,re
BUDGET={'wall_seconds':600,'rss_bytes':2*2**30,'new_output_bytes':100*2**20,'threads':1,'gpu':0}
SOURCE='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003/retrieved/outputs'
SEMANTICS={
 'E_native':'saved native score: prediction64 minus target32 promoted at subtraction, per-channel saved scale then full/band averaging',
 'G_S_increment':'saved diagnostic: target32-current32 rounded before float64 cast; prediction-current computed separately, then float64 mean/centering and saved scale',
 'coarse_change':'arithmetic difference of saved coarse predictions, normalized by their shared saved scales; not reconstructed native residual',
 'cross_representation_rule':'No inequality, additive share, guaranteed bound, or bitwise identity is asserted across these three representations'}
class DiagnosticStop(ValueError):pass

def bounded(x,depth=0):
 if depth>4:return '<bounded depth>'
 if x is None or isinstance(x,(bool,int)):return x
 if isinstance(x,float):return x if math.isfinite(x) else 'nonfinite:'+str(x)
 if isinstance(x,str):return x[:512]
 if isinstance(x,dict):return {str(k)[:80]:bounded(v,depth+1) for k,v in list(x.items())[:40]}
 if isinstance(x,(list,tuple)):return [bounded(v,depth+1) for v in x[:16]]
 return str(x)[:128]

def persist(path,payload,*,exclusive=False):
 data=(json.dumps(payload,sort_keys=True,allow_nan=False)+'\n').encode()
 if len(data)>8192:raise ValueError('bounded check evidence exceeds8192 bytes')
 path=Path(path);temp=path.with_suffix(path.suffix+'.partial')
 # A single owned process writes these fixed-size snapshots; failure never overwrites first failure.
 with temp.open('xb' if exclusive else 'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 if exclusive:
  try:os.link(temp,path)
  finally:temp.unlink(missing_ok=True)
 else:temp.replace(path)

class Audit:
 def __init__(self,out,*,source_version="ARTIFICIAL_OR_UNSPECIFIED",package_sha256=None):
  self.out=Path(out);self.source_version=source_version;self.package_sha256=package_sha256;self.context={};self.failed=False;self.enter('startup',missing_reason='no data row or arrays read')
 def enter(self,stage,**context):
  self.context={'stage':stage,'identity':None,'E_native':None,'G_increment':None,'S_increment':None,'margin':None,'missing_reason':'metric or case not applicable to this stage','margin_reason':'no cross-representation numerical bound is defined','scale':None,'scale_missing_reason':'not supplied for this check',**bounded(context)}
  self.checkpoint('enter_stage')
 def checkpoint(self,check,**detail):
  payload={'status':'BEFORE_CHECK','check':check,'code_source_version':self.source_version,'package_sha256':self.package_sha256,'data_source_version':'R003/source0faf16f8; original warning-stop breach retained','semantics':SEMANTICS,'context':self.context,'detail':bounded(detail)}
  persist(self.out/'last_check.json',payload)
  return payload
 def require(self,condition,message,**detail):
  payload=self.checkpoint(message,**detail)
  if not condition:self.fail(message,payload=payload)
 def fail(self,message,*,payload=None):
  if self.failed:raise DiagnosticStop(message)
  self.failed=True
  if payload is None:payload=self.checkpoint('exception_before_raise',exception=message)
  payload={**payload,'status':'FAILED_BEFORE_RAISE','error':str(message)[:512]}
  persist(self.out/'failure.json',payload,exclusive=True)
  raise DiagnosticStop(message)

def package_id(folder):
 p=Path(folder);lock=json.loads((p/'candidate_lock.json').read_text())
 for name,h in lock['files'].items():
  if Path(name).name!=name or hashlib.sha256((p/name).read_bytes()).hexdigest()!=h:raise PermissionError('diagnostic package identity mismatch')
 return hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def authority(path,digest,out):
 if path is None:raise PermissionError('Preparation only: no future HQ continuation authority receipt')
 with Path(path).open() as f:a=json.load(f)
 if not(a.get('authority_kind')=='hq_arithmetic_continuation' and a.get('allow_saved_derivative_read') is True
        and a.get('hq_thread_id')=='01a14bb9-6cd1-7ee2-9647-5190d786f7ba'
        and a.get('approval_text') and re.fullmatch('[0-9a-f]{40}',a.get('source_commit',''))
        and a.get('package_sha256')==digest and a.get('source_root')==SOURCE
        and a.get('output_root')==str(Path(out).resolve()) and a.get('budget')==BUDGET):
  raise PermissionError('Exact future continuation/package/scope authority missing')
 # Mechanical binding only. Real HQ source must be verified; a receipt never creates permission.
 return a
