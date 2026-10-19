"""Future native input adapter. load() is called ONLY after disabled/authority checks.
No import-time metadata or scientific access. Training-target and evaluation routes disjoint.
"""
from pathlib import Path
import hashlib,json,os
import numpy as np
import r002_base as base
import legacy_state as state
from engine import finite

class BoundedLoader(base.Loader):
 def get(self,row):
  value=super().get(row)
  while len(self.fields)>256:self.fields.popitem(last=False)
  while len(self.cache)>2:self.cache.popitem(last=False)
  if value.dtype!=np.float32:raise ValueError('native dtype')
  return value

class ProductionData:
 coarse_side=16;native_side=128;half_height=16
 def __init__(self,cases,frames,states,loader,identity):
  self.cases=cases;self.frames=frames;self.states=states;self.loader=loader;self.identity=identity
  self.groups=[c['group'] for c in cases];self.centers=[c['center_row'] for c in cases];self.features={};self.raw_targets={}
 def observations(self,ids,horizon):
  if horizon not in self.features:self.features[horizon]=state.features(self.states,self.cases,horizon)
  x,h=self.features[horizon];return x['C_RAW'][list(ids)],h[list(ids)]
 def current(self,i):
  c=self.cases[i];return self.loader.get(self.frames[(c['group'],c['origin_stage'])])
 def field(self,i,h):
  c=self.cases[i];return self.loader.get(self.frames[(c['group'],c['origin_stage']+h)])
 def training_targets(self,ids,fold):
  fold.validate(self.groups)
  if tuple(ids)!=fold.train:raise ValueError('training target access outside train side')
  # Deterministic raw-derived data cache only; no fitted state/normalizer/prediction is shared.
  out=[];amps=[]
  for i in ids:
   k=(i,fold.horizon)
   if k not in self.raw_targets:
    delta=self.field(i,fold.horizon)-self.current(i) # float32 subtraction, preserved.
    self.raw_targets[k]=(finite(base.pool(delta,16).ravel(),'pooled native target'),np.abs(delta).mean((1,2)))
   y,a=self.raw_targets[k];out.append(y);amps.append(a)
  return np.asarray(out),np.asarray(amps),ids
 def evaluation_target(self,i,fold):
  fold.validate(self.groups)
  if i not in fold.query:raise ValueError('evaluation target identity')
  return self.field(i,fold.horizon)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(code,audit):
 """Not used by fixtures. Exact old identity verification belongs to a later launch."""
 code=Path(code);cfg=json.loads((code/'legacy_config.json').read_text());audit.enter('old_input_identity')
 root=Path(cfg['data_root']);source=Path(cfg['source_run_root'])
 if os.stat(root).st_dev!=os.stat('/mnt/data2').st_dev:raise ValueError('producer mount identity')
 files=json.loads((code/'input_manifest.json').read_text())
 for row in files:
  rel=Path(row['relative_path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe old input identity')
  audit.enter('old_input_identity',relative_path=str(rel))
  p=root/rel
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('old input hash')
 if hashlib.sha256((source/'code/runner.py').read_bytes()+(source/'code/config.producer.json').read_bytes()).hexdigest()!=cfg['source_package_sha256']:raise ValueError('origin source package identity')
 frozen=json.loads((code/'frozen_cohort.json').read_text());manifest,frames,_=base.build_manifest(cfg)
 if manifest['cases']!=frozen['cases'] or manifest['exclusions']!=frozen['exclusions']:raise ValueError('frozen cohort mismatch')
 p=source/'outputs/origin_feature_evidence.npz'
 if sha(p)!=cfg['origin_feature_sha256']:raise ValueError('origin feature identity')
 with np.load(p,allow_pickle=False) as z:
  states=z['states'].copy();origins=z['origin_stage'].copy()
 if states.shape!=(1144,3,138) or list(origins)!=[c['origin_stage'] for c in frozen['cases']]:raise ValueError('origin state identity')
 finite(states,'origin states')
 return ProductionData(frozen['cases'],frames,states,BoundedLoader(root),{'input_manifest':sha(code/'input_manifest.json'),'cohort':sha(code/'frozen_cohort.json'),'origin_features':cfg['origin_feature_sha256']})
