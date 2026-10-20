"""E029 task wiring. Reuses the managed detector, labels, selector and runtime."""
import hashlib,importlib.util,json,os
from pathlib import Path,PureWindowsPath
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DOC=ROOT/'docs/research/S01/S01-E029'
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
core=module('e029_existing_core',ROOT/'scripts/pavetrack_protected_selector/core.py')
legacy=module('e029_existing_inputs',ROOT/'scripts/pavetrack_protected_selector/inputs.py')
roles=module('e029_existing_roles',ROOT/'scripts/pavetrack_role_probe/learning.py')
learning=module('e029_existing_e022_heads',ROOT/'scripts/pavetrack_semantic_selector/learning.py')
locality=module('e029_existing_locality',ROOT/'scripts/pavetrack_locality_selector/locality.py')
audit=module('e029_existing_context',ROOT/'scripts/pavetrack_supervision_feasibility/audit.py')
supervision=module('e029_existing_supervision',ROOT/'scripts/pavetrack_role_probe/inputs.py')
adapter=module('e029_numeric_adapter',HERE/'adapter.py')
write=core.write
read=core.read
digest=core.digest

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def checked(path,h):
    if sha(path)!=h:raise ValueError('byte identity: '+str(path))

def config(profile="windows"):
    if profile not in ("windows","taobo"):raise ValueError("runtime profile")
    c=read(DOC/("taobo_run_config.json" if profile=="taobo" else "run_config.json"));base=read(ROOT/'docs/research/S01/S01-E022/run_config.json')
    # Retain all inherited definitions; no monkey-patched legacy producer main.
    base.update(protocol='S01-E029-v1',proposed_run_id='S01-E029-R001')
    base['feature']['thresholds']=c['gates'];base['fit']['ridge']=c['ridge']
    return c,base

def scoped_bank(bank,locations):
    loc=set(locations);ims={im:l for im,l in bank['image_locations'].items() if l in loc}
    return dict(originals=[v for v in bank['originals'] if v['image_id'] in ims],candidates=[v for v in bank['candidates'] if v['image_id'] in ims],image_locations=ims,locations=list(locations))

def context(scope,guard):
    result=audit.context_features(scope['originals'],scope['candidates'],scope['image_locations'],core,guard)
    by={r['parent_id']:r for r in scope['candidates']};rows=[]
    for r in result['rows']:
        c=by[r['parent_id']];pressure,ties,overlap=r['values']
        vals=[c['row']['probability'],core.e8.box_iou(c['row']['original_box_xyxy'],c['row']['box_xyxy']),1/(1+overlap),1/(1+pressure)]
        rows.append(dict(index=c['index'],parent_id=c['parent_id'],image_id=c['image_id'],location=c['location'],values=vals))
    return result,rows

def features(rows,descriptors,arm):
    out=[]
    for r in rows:
        z=descriptors[r['index']]
        if any(z[k]!=r[k] for k in ['index','parent_id','image_id','location']):raise ValueError('cross-row spatial feature')
        out.append(dict(r,values=adapter.append_columns(r['values'],z[arm])))
    return out

def numeric_model(model):
    # Deliberately drops labels, locations, target identity, FIT policies/losses.
    return dict(heads={name:{key:model['heads'][name][key] for key in ['coefficients','columns','verified']} for name in ['Q','N','A']},threshold=model['threshold'])

def prediction_rows(model,rows,guard,geometry=False):
    pred=(roles if geometry else learning).predict(model,[r['values'] for r in rows],guard)
    return [dict(r,**p) for r,p in zip(rows,pred,strict=True)]

def choose(scope,model,predictions,cfg,threshold):
    scores={r['parent_id']:{k:r[k] for k in ['roles','rank_score']} for r in predictions}
    return roles.select(scope['candidates'],scores,threshold,scope['locations'],cfg,core,locality)


def linux(plan):return plan.get('runtime_profile')=='taobo'
def manifest_path(plan):return DOC/('taobo_source_manifest.json' if linux(plan) else 'source_manifest.json')
def paths_path(plan):return DOC/('taobo_private_paths.json' if linux(plan) else 'private_paths.template.json')
def environment(plan):return module('e029_platform_environment',HERE/'e029_linux_environment.py' if linux(plan) else ROOT/'scripts/pavetrack_target_spatial/environment.py')
def image_path(record,plan):
    if not linux(plan):return Path(record['prepared_image'])
    logical=PureWindowsPath(record['prepared_image']);base=PureWindowsPath(plan['logical_source_image_root'])
    if logical.parent!=base or logical.name!=record['image_id'] or Path(logical.name).name!=logical.name or '\\' in logical.name or logical.name in ('.','..'):raise ValueError('immutable logical image identity')
    return Path(plan['linux_paths']['images'])/logical.name
