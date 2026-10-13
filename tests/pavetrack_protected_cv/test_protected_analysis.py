import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('protected_analysis',ROOT/'scripts/pavetrack_protected_cv/analyze.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
CFG={'parent_cap':40,'refinement_nms_iou':.5,'primary_delta':.05,'minimum_retention':.95,'seed':20261013}
def evidence(targets):
 o={'parent_id':0,'candidate_id':'o:0','kind':'original','image_id':'im','reid':'1','box_xyxy':[0,0,5,5],'score':.5,'E003_score':.5,'probability':1.,'proposer_confidence':.25};c=dict(o,candidate_id='c:0',kind='correction',original_box_xyxy=o['box_xyxy'],box_xyxy=[10,0,15,5]);rows,choice=a.m.coordinate_choice([o],[o,c],[.5,.5],CFG);bm=a.m.metrics([o],targets,{'im':'1'},'score');cm=a.m.metrics(rows,targets,{'im':'1'},'score');hits=a.m.admitted_targets([o],targets,bm);ret=1. if hits else None;delta=None if bm['macro_location_recall'] is None else 0.
 return {'baseline_rows':[o],'rows':rows,'pair_rows':[o,c],'pair_probabilities':[.5,.5],'choice':choice,'targets':targets,'image_locations':{'im':'1'},'baseline':bm,'candidate':cm,'delta':delta,'retention':ret,'retained_old_targets':len(hits),'lost_old_targets':0,'new_detected_targets':0,'protected_primary_pass':None if ret is None or delta is None else False,'baseline_oracle':a.m.oracle_coverage([o],targets,{'im':'1'}),'oracle':a.m.oracle_coverage(rows,targets,{'im':'1'})}
def test_no_targets_inconclusive():
 e=evidence({'im':[]});s,t,old,new=a.replay(e,CFG);assert s['retention'] is None and s['protected_primary_pass'] is None

def test_old_target_is_exactly_retained_but_no_gain():
 e=evidence({'im':[[0,0,5,5]]});s,t,old,new=a.replay(e,CFG);assert s['retention']==1. and s['protected_primary_pass'] is False and t[0]['retained_old']==1

def test_retention_tamper_rejected():
 e=evidence({'im':[[0,0,5,5]]});e['retention']=.95
 with pytest.raises(ValueError,match='protected criterion'):a.replay(e,CFG)

def test_score_mutation_rejected():
 e=evidence({'im':[[0,0,5,5]]});e['rows'][0]['score']=.6
 with pytest.raises(ValueError,match='protected score'):a.replay(e,CFG)

def test_fp_decomposition_duplicate_and_partial():
 rows=[{'image_id':'im','reid':'1','box_xyxy':b,'score':s} for b,s in [([0,0,5,5],.9),([0,0,5,5],.8),([2,0,7,5],.7),([10,0,15,5],.6)]];targets={'im':[[0,0,5,5]]};metric=a.m.metrics(rows,targets,{'im':'1'},'score');counts=a.fp_types(rows,targets,metric);assert counts=={'duplicate':1,'partial':0,'no_small_overlap':0}

def test_fp_decomposition_atomic_tie_rejected():
 rows=[{'image_id':'im','reid':'1','box_xyxy':b,'score':.5} for b in [[0,0,5,5],[10,0,15,5]]];targets={'im':[]};metric=a.m.metrics(rows,targets,{'im':'1'},'score');assert a.fp_types(rows,targets,metric)=={'duplicate':0,'partial':0,'no_small_overlap':0}
