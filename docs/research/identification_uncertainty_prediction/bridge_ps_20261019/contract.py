"""Text/metadata checks and approval boundary. No scientific loader here."""
from pathlib import Path
import hashlib,json
COHORT_SHA='19a75f76d68d63294744031b9369864185bb3da313f520699242132a5b7ae553'
BASE_SHA='262b8ddb79f81896e6dcb6717e4722f479a6bca65a3dc84e33a322097e555d1a'
RUN='IU-BRIDGE-PS-20261019-R003'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):
 p=Path(path);t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(obj,indent=2,ensure_ascii=False));t.replace(p)

def check(code,cfg):
 code=Path(code);m=read(code/'frozen_cohort.json');files=read(code/'input_manifest.json')
 if sha(code/'frozen_cohort.json')!=COHORT_SHA or sha(code/'r002_base.py')!=BASE_SHA:raise ValueError('source identity changed')
 if cfg['protocol']!='BRIDGE-PS-v1.0' or cfg['run_id']!=RUN:raise ValueError('protocol/run identity')
 from state import ARMS
 if cfg['arms']!=list(ARMS) or cfg['history_stage_offsets']!=[-20,-10,0] or cfg['horizon_stage_steps']!=[10,40]:raise ValueError('arms/history changed')
 if cfg['ridge_alphas']!=[.1,10.,1000.] or cfg['input_residualizer_alpha']!=10. or cfg['tolerance']!=1e-11:raise ValueError('estimator/tolerance changed')
 if cfg['baseline_tie_order']!=['P','S','C_REL','C_RAW']:raise ValueError('selector changed')
 if cfg['threads']!=1 or cfg['wall_seconds']!=1800 or cfg['memory_gib']!=8 or cfg['max_output_gib']!=4 or cfg['max_archive_gib']!=4:raise ValueError('budget changed')
 if cfg['resampling']!={'draws':10000,'seed':20261019}:raise ValueError('sensitivity design changed')
 if cfg['pool_input_side']!=8 or cfg['pool_output_side']!=16 or cfg['local_band_half_height']!=16:raise ValueError('spatial support changed')
 if len(m['cases'])!=1144 or len({c['group'] for c in m['cases']})!=19 or len(files)!=180:raise ValueError('cohort/input counts')
 if sum(x['bytes'] for x in files)!=2309814734:raise ValueError('input byte identity')
 if cfg['expected']!={'groups':19,'origins':1144,'horizon_cases':2288,'predictor_fits':912,'input_fits':76,'scores':20592,'selector_scores':2288,'prediction_archives':228,'equivalence_archives':38}:raise ValueError('work accounting')
 for c in m['cases']:
  n=c['origin_stage']
  if c['history_stages']!=[n-20,n-10,n] or c['targets']!={'10':n+10,'40':n+40}:raise ValueError('origin information contract')
 if cfg['data_root']!='/mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/inputs/mendeley' or cfg['source_run_root']!='/mnt/data2/drtao/wennie/IU-RESPONSE-STATE-20261019-R002':raise ValueError('read-only source store changed')
 if cfg['run_root']!='/mnt/data2/drtao/wennie/'+RUN:raise ValueError('run root changed')
 return m,files

def load_config(code,path):
 code=Path(code).resolve();path=Path(path).resolve()
 if path!=code/'config.producer.json':raise ValueError('configuration is outside the sealed package')
 return read(path)

def package_id(code):
 code=Path(code);lock=read(code/'package_lock.json')
 for name,h in lock['files'].items():
  p=Path(name)
  if p.is_absolute() or '..' in p.parts or sha(code/p)!=h:raise ValueError('runtime/package identity changed: '+name)
 return hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def approval(code,cfg,path):
 # Mechanical identity guard only: a flag/file never grants authority by itself.
 digest=package_id(code)
 if path is None:raise PermissionError('NO EXECUTION AUTHORITY: approval receipt absent')
 a=read(path)
 if not(a.get('human_approved') is True and a.get('package_sha256')==digest and a.get('run_id')==cfg['run_id'] and a.get('authority_source') and a.get('approval_text') and a.get('implementation_commit')):raise PermissionError('exact human/run/package approval missing')
 return digest,a

def budget_reason(elapsed,rss_bytes,output_bytes,archive_bytes,returncode=None):
 if elapsed>1800:return 'wall_budget'
 if rss_bytes>8*2**30:return 'rss_budget'
 if output_bytes>4*2**30:return 'output_budget'
 if archive_bytes>4*2**30:return 'archive_budget'
 if returncode is not None and returncode!=0:return 'worker_failed'
 return None
