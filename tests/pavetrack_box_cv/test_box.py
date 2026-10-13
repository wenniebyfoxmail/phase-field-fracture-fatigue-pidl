import importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('box_run',ROOT/'scripts/pavetrack_box_cv/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CFG={'offset_bound':2.,'scale_bounds':[.25,4.],'context_padding_choices':[.5,1.,2.],'minimum_context_containment':.9,'refinement_nms_iou':.5}
REC={'image_id':'im','reid':'1','width':100,'height':100,'crack_boxes_xyxy':[[20,20,40,40]]}

def row(box,score=1.,id=0):return {'image_id':'im','reid':'1','box_xyxy':box,'score':score,'candidate_id':id}

def test_association_tie_and_minimum():
 assert m.associate([0,0,10,10],[[0,0,10,10],[0,0,10,10]])==0
 assert m.associate([0,0,1,1],[[10,10,20,20]]) is None

def test_encode_decode_exact_and_clamped():
 b=[20,20,30,30];target=[10,15,40,35];d,clipped=m.encode(b,target,CFG);out,flags=m.decode(b,d,REC,CFG)
 assert out==pytest.approx(target);assert not clipped;assert not flags['fallback']
 d,clipped=m.encode([0,0,1,1],[0,0,100,100],CFG);assert clipped;assert d[0]==2.;assert d[2]==pytest.approx(np.log(4))

def test_decode_clip_fallback_and_nonfinite():
 out,flags=m.decode([0,0,1,1],[-100,-100,-100,-100],REC,CFG);assert out==[0,0,1,1];assert flags['fallback'] and flags['bounded']
 with pytest.raises(ValueError):m.decode([0,0,1,1],[float('nan'),0,0,0],REC,CFG)

def test_context_target_balanced_not_candidate_dominated():
 rec=dict(REC,crack_boxes_xyxy=[[20,20,40,40],[60,60,90,90]])
 train={'rows':[row([20,20,40,40]) for _ in range(100)]+[row([60,60,65,65])]}
 # second candidate IoU below .05; use 10x10 to associate but not contain at p=.5
 train['rows'][-1]['box_xyxy']=[60,60,70,70]
 a=m.audit_payload(train,[rec],dict(CFG,minimum_context_containment=.9))
 assert a['context_rates'][0]['fraction']>.9
 assert a['context_rates'][0]['target_balanced_fraction']==pytest.approx(.5)
 assert a['selected_padding']==2. and a['represented_gt']==2

def test_context_can_stop_before_fit():
 a=m.audit_payload({'rows':[row([20,20,30,30])]},[REC],dict(CFG,context_padding_choices=[0.],minimum_context_containment=1.))
 assert a['selected_padding'] is None and a['status']=='stop_input_unobservable'


def test_nms_score_ties_and_original_order():
 rows=[row([0,0,10,10],.5,1),row([1,1,11,11],.5,0)]
 assert [r['candidate_id'] for r in m.suppress(rows,.5)]==[1]
 rows=[row([0,0,10,10],.5,1),row([20,20,30,30],1.,0)]
 assert m.suppress(rows,.5)==rows

def test_identity_model_preserves_score_and_boxes():
 rows=[dict(row([20,20,40,40]),proposer_confidence=.25,probability=1.)]
 X=np.zeros((1,len(m.FEATURES)),dtype=np.float32);X[0,-6:]=m.features(rows[0],REC)
 model={'means':[0.]*len(m.FEATURES),'stds':[1.]*len(m.FEATURES),'coefficients':[[0.]*4 for _ in m.FEATURES],'intercepts':[0.]*4}
 e=m.evaluate_rows(rows,[REC],model,X,CFG)
 assert e['delta']==0 and e['rows'][0]['score']==.5 and e['rows'][0]['box_xyxy']==rows[0]['box_xyxy']
 assert e['candidate']==e['baseline']


def test_changed_original_nms_is_inadmissible():
 rows=[dict(row([20,20,40,40],id=i),proposer_confidence=.25,probability=1.) for i in range(2)]
 X=np.zeros((2,len(m.FEATURES)),dtype=np.float32)
 for i,r in enumerate(rows):X[i,-6:]=m.features(r,REC)
 model={'means':[0.]*len(m.FEATURES),'stds':[1.]*len(m.FEATURES),'coefficients':[[0.]*4 for _ in m.FEATURES],'intercepts':[0.]*4}
 with pytest.raises(ValueError,match='baseline additional'):m.evaluate_rows(rows,[REC],model,X,CFG)


def test_download_firewall_rejects_location_drift():
 with pytest.raises(ValueError):m.validate_download_payload({'url':'url','remote_size':1,'requested_locations':['fresh','train']},{'archive_bytes':1,'confirmatory_test_locations':['fresh']},'url')
