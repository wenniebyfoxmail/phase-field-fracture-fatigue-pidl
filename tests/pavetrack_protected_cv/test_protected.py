import importlib.util
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('protected_runner',ROOT/'scripts/pavetrack_protected_cv/run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
CFG={'parent_cap':40,'refinement_nms_iou':.5,'primary_delta':.05,'minimum_retention':.95}
def row(box,score=.8):return {'image_id':'im','reid':'1','box_xyxy':box,'proposer_confidence':score**2,'probability':1.}
def banks(rows,boxes):return m.protected_bank(rows,[dict(r,parent_id=i,original_box_xyxy=r['box_xyxy'],box_xyxy=boxes[i]) for i,r in enumerate(rows)],CFG)
def test_top_cap_gt_free_exact_parent_identity():
 rows=[row([i*10,0,i*10+5,5],.5) for i in range(45)];o,p,c=banks(rows,[r['box_xyxy'] for r in rows]);assert len(o)==45 and len(p)==80 and c['paired_parents']==40;assert all(r['parent_id']<40 for r in p)
def test_pair_tie_retains_original_and_score():
 rows=[row([0,0,5,5])];o,p,c=banks(rows,[[10,0,15,5]]);new,flags=m.coordinate_choice(o,p,[.8,.8],CFG);assert new==o and flags['probability_ties_original']==1
 new,flags=m.coordinate_choice(o,p,[.2,.9],CFG);assert new[0]['box_xyxy']==[10,0,15,5] and new[0]['score']==o[0]['score'] and new[0]['parent_id']==0

def test_conflict_nonparent_and_correction_loser_fallback():
 rows=[row([0,0,5,5],.9),row([20,0,25,5],.8)];o,p,c=banks(rows,[[20,0,25,5],[10,0,15,5]]);new,flags=m.coordinate_choice(o,p,[0,1,1,0],CFG);assert new==o and flags['conflict_fallbacks']==1
 o,p,c=banks(rows,[[10,0,15,5],[10,0,15,5]]);new,flags=m.coordinate_choice(o,p,[0,1,0,1],CFG);assert new[0]['box_xyxy']==[10,0,15,5] and new[1]['box_xyxy']==rows[1]['box_xyxy'];assert flags['conflict_fallbacks']==1

def test_fold_partition():
 lock=m.read(ROOT/'docs/research/S01/S01-E006/data_lock.json');folds=m.folds(lock);assert [sorted((k for k,v in folds.items() if v==i),key=int) for i in range(4)]==[['24','514','1577','3662'],['95','728','1638','4494'],['151','1400','2027','5508'],['353','1459','2028','5982']]

def test_weight_class_mass_and_pair_priors():
 import torch
 rows=[{'reid':'1','kind':'original'},{'reid':'1','kind':'correction'},{'reid':'2','kind':'original'},{'reid':'2','kind':'correction'}];y=torch.tensor([1,0,1,0],dtype=torch.float64);w=m.selector_weights(rows,y);assert w[y==1].sum().item()==pytest.approx(.5) and w[y==0].sum().item()==pytest.approx(.5);assert w.sum().item()==pytest.approx(1.)

def test_retention_exact_targets_and_atomic_ties():
 rows=[dict(row([0,0,5,5]),score=.5),dict(row([10,0,15,5]),score=.5)];targets={'im':[[0,0,5,5]]};metric=m.metrics(rows,targets,{'im':'1'},'score');hits=m.admitted_targets(rows,targets,metric);assert hits=={('im',0)}
 targets={'im':[]};metric=m.metrics(rows,targets,{'im':'1'},'score');assert m.admitted_targets(rows,targets,metric)==set() and metric['detections_used']==0

def test_evaluate_pair_identity_and_inconclusive_retention():
 rows=[row([0,0,5,5])];o,p,c=banks(rows,[[10,0,15,5]]);rec={'image_id':'im','reid':'1','width':20,'height':20,'crack_boxes_xyxy':[]};X=np.zeros((len(p),len(m.FEATURES)),np.float32)
 for i,r in enumerate(p):X[i,-8:]=m.geom(r,rec)
 model={'means':[0.]*len(m.FEATURES),'stds':[1.]*len(m.FEATURES),'coefficients':[0.]*len(m.FEATURES),'intercept':0.};e=m.evaluate_bank({'original_rows':o,'bank':p},[rec],model,X,CFG);assert e['retention'] is None and e['protected_primary_pass'] is None and e['delta'] is None

def test_no_review_cannot_access_fresh(monkeypatch,tmp_path):
 from types import SimpleNamespace
 a=SimpleNamespace(run=tmp_path,independent_review=None,review_sha256=None)
 monkeypatch.setattr(m,'verify_validation',lambda *args:{'protected_primary_pass':True})
 with pytest.raises(ValueError,match='independent development review'):m.reviewed_pass(a,{},None,None)
 assert not (tmp_path/'test_authorization.json').exists()

def test_validity_labels_are_not_duplicate_negatives():
 rows=[dict(row([0,0,5,5]),kind='original'),dict(row([0,0,5,5]),kind='correction')];records=[{'image_id':'im','crack_boxes_xyxy':[[0,0,5,5]]}];assert m.labels(rows,records)==[1,1]

def test_pending_missing_and_tampered_blocks_authorize(monkeypatch,tmp_path):
 from types import SimpleNamespace
 a=SimpleNamespace(run=tmp_path,independent_review=tmp_path/'review.json',review_sha256='fake')
 e={'protected_primary_pass':True,'delta':.1,'retention':1.}
 monkeypatch.setattr(m,'verify_validation',lambda *args:e);monkeypatch.setattr(m,'pending_fields',lambda *args:{'expected':True})
 for payload in [None,{'expected':False}]:
  if payload is not None:m.write(tmp_path/'pending_confirmatory_review.json',payload)
  with pytest.raises(ValueError,match='exact pending'):m.reviewed_pass(a,{},None,None)
 assert not (tmp_path/'test_authorization.json').exists()

def test_frozen_score_probability_and_score_tamper_rejected(monkeypatch):
 monkeypatch.setattr(m,'frozen_score_probabilities',lambda *args:[.25]);r=dict(row([0,0,5,5]),probability=.25,score=.4,E003_score=.4);X=np.zeros((1,576),np.float32)
 m.verify_train_scores([r],X,None)
 for key in ['probability','score','E003_score']:
  bad=dict(r);bad[key]+=.01
  with pytest.raises(ValueError,match='train score replay'):m.verify_train_scores([bad],X,None)
