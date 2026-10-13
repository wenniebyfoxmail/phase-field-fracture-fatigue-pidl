import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('box_analysis',ROOT/'scripts/pavetrack_box_cv/analyze.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def evidence(targets,rows):
 old=[dict(r) for r in rows];new=[dict(r,original_box_xyxy=r['box_xyxy'],correction_flags={'bounded':False,'image_clipped':False,'fallback':False}) for r in rows];loc={'im':'1'};bm=a.metrics(old,targets,loc,'score');cm=a.metrics(new,targets,loc,'score')
 return {'baseline_rows':old,'rows':new,'all_corrected_rows':new,'baseline':bm,'candidate':cm,'delta':None if bm['macro_location_recall'] is None else 0.,'targets':targets,'image_locations':loc,'baseline_oracle':a.oracle_coverage(old,targets,loc),'oracle':a.oracle_coverage(new,targets,loc),'suppressed_count':0,'primary_pass':None}
CFG={'refinement_nms_iou':.5,'seed':20261013,'primary_delta':.05,'development_delta_to_access_test':.05}
def row(i=0,x=0):return {'image_id':'im','reid':'1','candidate_id':i,'score':.5,'box_xyxy':[x,0,x+5,5]}
def test_unidentifiable_primary():
 s,*_=a.summarize(evidence({'im':[]},[row()]),CFG);assert s['delta'] is None and s['descriptive_location_bootstrap_95_interval'] is None
def test_atomic_tie_over_budget():
 e=evidence({'im':[]},[row(),row(1,10)]);assert e['candidate']['detections_used']==0;assert a.outcomes(e['rows'],e['targets'],e['candidate'])==[]
def test_zero_oracle_and_empty_candidates():
 s,*_=a.summarize(evidence({'im':[[0,0,5,5]]},[]),CFG);assert s['delta']==0 and s['candidate_oracle']==0

def test_score_tamper_rejected():
 e=evidence({'im':[[0,0,5,5]]},[row()]);e['all_corrected_rows'][0]['score']=.9
 with pytest.raises(ValueError):a.summarize(e,CFG)

def test_counts_tamper_rejected():
 e=evidence({'im':[]},[row()]);e['candidate']['false_positives']=0
 with pytest.raises(ValueError):a.summarize(e,CFG)
