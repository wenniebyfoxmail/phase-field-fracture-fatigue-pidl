import importlib.util,json,copy,hashlib
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualification_analysis',ROOT/'scripts/pavetrack_paired_cv/qualification_analysis.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q);m=q.m
CFG=m.read(ROOT/'docs/research/S01/S01-E007/run_config.json');LOCK=ROOT/'docs/research/S01/S01-E007/data_lock.json';CONFIG=ROOT/'docs/research/S01/S01-E007/run_config.json'
def save(p,j):p.write_text(json.dumps(j)+'\n')
def fixture(run,policy):
 lock=m.read(LOCK);old=dict(image_id='a',reid='353',parent_id=0,candidate_id='o:0',kind='original',box_xyxy=[0,0,10,10],score=.8,E003_score=.8,proposer_confidence=.8,probability=.8);new=dict(old,candidate_id='c:0',kind='correction',box_xyxy=[20,0,30,10],original_box_xyxy=old['box_xyxy']);records=[dict(image_id='a',reid='353',crack_boxes_xyxy=[[0,0,10,10]])]
 binding=dict(protocol=CFG['protocol'],source_manifest_sha256='source',config_sha256=m.sha256_file(CONFIG),lock_sha256=m.sha256_file(LOCK),parent_feature_receipt_sha256='receipt',parent_run_id='S01-E006-R002',inherited_lineage={})
 data=dict(binding,original_rows=[old],bank=[old,new],labels=[m.labels(old['box_xyxy'],new['box_xyxy'],records[0]['crack_boxes_xyxy'])],targets={'a':records[0]['crack_boxes_xyxy']},image_locations={'a':'353'})
 save(run/'train_bank.json',data);save(run/'label_audit.json',dict(binding,**m.label_audit(data,lock,CFG)));save(run/'feature_receipt.json',dict(binding,files={n:m.sha256_file(run/n) for n in ['train_bank.json','label_audit.json']}))
 if policy:
  head={'means':[0.]*1745,'stds':[1.]*1745,'coefficients':np.zeros((1745,2)).tolist(),'intercepts':[-10.,10.]};policies=[]
  for limit in CFG['harm_score_limits']:
   e=m.evaluate(data,records,head,np.zeros((1,1745)),CFG,limit);e.update(harm_limit=limit,protected_exposures=1,harm_count=1,harm_rate=1.,qualified=False);policies.append(e)
  save(run/'qualification_evaluation.json',dict(binding,policies=policies));save(run/'qualification_decision.json',m.decision_fields(binding,policies,CFG,m.sha256_file(run/'qualification_evaluation.json')))
 else:save(run/'qualification_decision.json',dict(binding,status='inconclusive_qualification_classes',fresh_access=False))
 return binding

def test_all_negative_policies_and_harm_are_replayed(tmp_path):
 fixture(tmp_path,True);summary,cases,targets,policies=q.validated(tmp_path,CFG,CONFIG,LOCK)
 assert len(policies)==4;assert all(x['harm_rate']==1. for x in summary['policies']);assert summary['status']=='inconclusive_qualification_exposure';assert cases
 e=m.read(tmp_path/'qualification_evaluation.json');e['policies'][1]['delta']=.123;save(tmp_path/'qualification_evaluation.json',e);d=m.read(tmp_path/'qualification_decision.json');d['qualification_evaluation_sha256']=m.sha256_file(tmp_path/'qualification_evaluation.json');save(tmp_path/'qualification_decision.json',d)
 with pytest.raises(ValueError):q.validated(tmp_path,CFG,CONFIG,LOCK)
def test_class_stop_has_exact_counts_and_fixed_geometry_cases(tmp_path):
 fixture(tmp_path,False);summary,cases,targets,policies=q.validated(tmp_path,CFG,CONFIG,LOCK)
 assert not policies;assert summary['label_counts'][0]['pairs']==0;assert summary['label_counts'][1]['pairs']==1;assert summary['label_counts'][1]['harm_1']==1;assert cases[0]['kind']=='label_harm_only'
 d=m.read(tmp_path/'qualification_decision.json');d['status']='qualified';save(tmp_path/'qualification_decision.json',d)
 with pytest.raises((ValueError,FileNotFoundError)):q.validated(tmp_path,CFG,CONFIG,LOCK)
def test_nonpass_status_and_fresh_tamper_rejected(tmp_path):
 fixture(tmp_path,True);d=m.read(tmp_path/'qualification_decision.json');d['status']='arbitrary';save(tmp_path/'qualification_decision.json',d)
 with pytest.raises(ValueError,match='selection'):q.validated(tmp_path,CFG,CONFIG,LOCK)
 fixture(tmp_path,True);d=m.read(tmp_path/'qualification_decision.json');d['fresh_access']=True;save(tmp_path/'qualification_decision.json',d)
 with pytest.raises(ValueError,match='selection'):q.validated(tmp_path,CFG,CONFIG,LOCK)

@pytest.mark.parametrize('policy',[False,True])
def test_render_stop_tables_and_decision_figure(tmp_path,monkeypatch,policy):
 fixture(tmp_path,policy);out=tmp_path/'plots'
 monkeypatch.setattr('sys.argv',['qualification_analysis','--run',str(tmp_path),'--output',str(out),'--config',str(CONFIG),'--lock',str(LOCK)])
 q.main();assert (out/'F00_training_qualification.png').stat().st_size>1000;assert (out/'label_counts.csv').is_file();assert (out/'montage_cases.json').is_file()
 if policy:assert 'harm_rate' in (out/'qualification_metrics.csv').read_text()
