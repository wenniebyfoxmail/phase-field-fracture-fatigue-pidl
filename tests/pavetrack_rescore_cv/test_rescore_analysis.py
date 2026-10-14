import copy,importlib.util,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('rescore_analysis',ROOT/'scripts/pavetrack_rescore_cv/analyze.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
s2=importlib.util.spec_from_file_location('rescore_test',Path(__file__).with_name('test_rescore.py'));t=importlib.util.module_from_spec(s2);s2.loader.exec_module(t);m=a.m;CFG=t.CFG

def evaluation():
 originals,pairs=t.fixture();records=[dict(image_id=im,reid='24',crack_boxes_xyxy=[[0,0,10,10]]) for im in ['a','b']]
 return m.evaluate({'original_rows':originals,'bank':pairs},records,[.81],CFG,1.)
def test_exact_metric_replay_and_admitted_case_selection():
 e=evaluation();summary,table,before,after=a.replay(e,CFG,True);cases=a.cases(e,before,after)
 assert summary['net_targets']==1;assert any(c['kind']=='new_detected_target' and c['emitted']['rescored_correction'] for c in cases)
 e['net_targets']=0
 with pytest.raises(ValueError):a.replay(e,CFG,True)
def test_removed_original_or_changed_score_invalidates_replay():
 e=evaluation();e['rows'][0]['score']=.5
 with pytest.raises(ValueError):a.replay(e,CFG,True)
