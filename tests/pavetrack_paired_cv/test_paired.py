import importlib.util,json,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('paired',ROOT/'scripts/pavetrack_paired_cv/run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
CFG=p.read(ROOT/'docs/research/S01/S01-E007/run_config.json')
def rows():
 old={'image_id':'a','reid':'24','parent_id':0,'candidate_id':'o:0','kind':'original','box_xyxy':[0,0,10,10],'score':.8,'E003_score':.8,'proposer_confidence':.8,'probability':.8}
 new=dict(old,kind='correction',candidate_id='c:0',original_box_xyxy=old['box_xyxy'],box_xyxy=[2,0,12,10]);return old,new

def test_switch_valid_target_is_still_harmful():
 y=p.labels([0,0,10,10],[20,0,30,10],[[0,0,10,10],[20,0,30,10]])
 assert y=={'harm':1,'gain':1,'protected':True,'original_gt_index':0}
def test_same_target_repaired_without_harm():
 assert p.labels([0,0,10,10],[1,0,11,10],[[0,0,10,10]])['harm']==0
 assert p.labels([0,0,4,10],[0,0,10,10],[[0,0,10,10]])['gain']==1
 assert p.labels([0,0,10,10],[20,0,30,10],[])=={'harm':0,'gain':0,'protected':False,'original_gt_index':None}
def test_target_tie_is_lowest_index():
 assert p.labels([0,0,10,10],[0,0,10,10],[[0,0,10,10],[0,0,10,10]])['original_gt_index']==0

def test_abstention_gain_tie_and_harm_boundary():
 old,new=rows()
 for scores,accepted in [([.05,.5],0),([.05,.50001],1),([.050001,.9],0),([.99,.99],0)]:
  emitted,c=p.coordinate_choice([old],[old,new],{'harm_limit':.05,'scores':[scores]},CFG)
  assert c['accepted_choices']==accepted;assert emitted[0]['score']==old['score'];assert emitted[0]['box_xyxy']==(new if accepted else old)['box_xyxy']
def test_conflicting_correction_abstains():
 old,new=rows();other=dict(old,parent_id=1,candidate_id='o:1',box_xyxy=new['box_xyxy'])
 e,c=p.coordinate_choice([old,other],[old,new],{'harm_limit':.1,'scores':[[0,.9]]},CFG)
 assert c['conflict_fallbacks']==1;assert e[0]['box_xyxy']==old['box_xyxy']
def test_invalid_policy_or_score_rejected():
 old,new=rows()
 with pytest.raises(ValueError):p.coordinate_choice([old],[old,new],{'harm_limit':.3,'scores':[[0,.9]]},CFG)
 with pytest.raises(ValueError):p.coordinate_choice([old],[old,new],{'harm_limit':.05,'scores':[[float('nan'),.9]]},CFG)
def test_no_qualification_leakage_in_inner_heads():
 lock=p.read(ROOT/'docs/research/S01/S01-E007/data_lock.json');fit,qual,groups=p.split_spec(lock,CFG)
 assert len(groups)==4;assert len(fit)==12
 held=[]
 for g in groups[:3]:
  assert len(g['fit_locations'])==8;assert len(g['held_locations'])==4
  assert not set(g['fit_locations'])&set(qual);assert not set(g['fit_locations'])&set(g['held_locations']);held+=g['held_locations']
 assert sorted(held,key=int)==fit;assert groups[3]['fit_locations']==fit;assert groups[3]['held_locations']==qual

def test_pair_feature_geometry_and_order():
 old,new=rows();x=np.zeros((2,872),np.float32);x[0,:864]=1;x[1,:864]=2;x[0,870]=3
 out=p.pair_features([old,new],x)
 assert out.shape==(1,1745);assert np.all(out[0,:864]==1);assert np.all(out[0,864:1728]==2);assert out[0,1740]==pytest.approx(.2);assert out[0,-1]==3
 with pytest.raises(ValueError):p.pair_features([new,old],x)
def test_subset_preserves_gt_labels_and_remaps_parents():
 old,new=rows();other,othernew=rows()
 for r in [other,othernew]:r.update(parent_id=4,reid='95')
 d={'original_rows':[old,other],'bank':[old,new,other,othernew],'labels':[{'harm':0,'gain':1,'protected':False},{'harm':1,'gain':0,'protected':True}]}
 q,x=p.subset(d,np.ones((2,1745)),['95'])
 assert len(q['bank'])==2;assert q['bank'][0]['parent_id']==0;assert q['bank'][1]['parent_id']==0;assert q['labels'][0]['harm']==1
 assert d['original_rows'][1]['parent_id']==4

def test_class_weights_equal_location_prior_then_classes():
 import torch
 old,new=rows();d={'bank':[],'labels':[]}
 for i,(loc,y) in enumerate([('24',[1,0]),('24',[0,1]),('95',[1,1]),('95',[0,0])]):
  o=dict(old,parent_id=i,reid=loc);n=dict(new,parent_id=i,reid=loc);d['bank'] +=[o,n];d['labels'].append(dict(zip(['harm','gain'],y)))
 Z,Y,W,mu,sd=p.tensors(d,np.arange(4*1745).reshape(4,1745),['24','95'])
 for k in range(2):
  assert float(W[Y[:,k]==1,k].sum())==pytest.approx(.5);assert float(W[Y[:,k]==0,k].sum())==pytest.approx(.5)
 d['labels']=[{'harm':0,'gain':1}]*4
 with pytest.raises(ValueError,match='unidentifiable'):p.tensors(d,np.ones((4,1745)),['24','95'])

def test_decision_exact_status_and_fresh_are_binding():
 row=dict(qualified=False,retention=.9,delta=.01,protected_exposures=20,harm_limit=.05,choice={'accepted_choices':20})
 d=p.decision_fields({'protocol':'S01-E007-v1'},[row],CFG,'abc')
 assert d['status']=='stop_qualification_negative';assert d['fresh_access'] is False
 mutated=dict(d,status='arbitrary');assert mutated!=p.decision_fields({'protocol':'S01-E007-v1'},[row],CFG,'abc')
 mutated=dict(d,fresh_access=True);assert mutated!=p.decision_fields({'protocol':'S01-E007-v1'},[row],CFG,'abc')
def test_zero_baseline_hits_is_inconclusive_despite_exposures():
 row=dict(qualified=False,retention=None,delta=0.,protected_exposures=20,harm_limit=.05,choice={'accepted_choices':20})
 assert p.decision_fields({},[row],CFG,'abc')['status']=='inconclusive_qualification_metric'
 row['retention']=1.;row['delta']=None
 assert p.decision_fields({},[row],CFG,'abc')['status']=='inconclusive_qualification_metric'
