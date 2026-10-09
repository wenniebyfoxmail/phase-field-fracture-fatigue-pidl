"""Synthetic geometry checks and split invariants only; no image/model training."""
import csv,json
from pathlib import Path
import numpy as np
from reconstruction_reference import reconstruct,starts
rng=np.random.default_rng(7)
for h,w in [(1,1),(200,310),(448,448),(449,451),(673,897),(1200,700)]:
 a=rng.random((h,w,3),dtype=np.float32)
 p=reconstruct(a,lambda x:x[:,:,0]);assert np.allclose(p,a[:,:,0],atol=1e-12,rtol=0)
 assert np.allclose(reconstruct(a,lambda x:np.full((448,448),.37)),.37)
for bad in [np.full((448,448),np.nan),np.full((448,448),1.01),np.zeros((447,448))]:
 try:reconstruct(np.zeros((20,30,3)),lambda x:bad)
 except ValueError:pass
 else:raise AssertionError('Invalid predictor accepted')
p=Path(__file__).parent;r=list(csv.DictReader((p/'metu_group_split_r1.csv').open()))
assert len(r)==458 and len({x['stem'] for x in r})==458
for g in {x['candidate_group'] for x in r}:assert len({x['split'] for x in r if x['candidate_group']==g})==1
m={x['stem']:x['split'] for x in r}
for x in csv.DictReader((p.parent/'METU_GROUP_CONSTRAINTS_2026-10-09.csv').open()):assert m[x['image_a']]==m[x['image_b']]
print(json.dumps({'synthetic_shapes_checked':6,'invalid_probability_cases_rejected':3,'split_rows':458,'known_visual_pair_constraints_preserved':7,'training_executed':False}))
