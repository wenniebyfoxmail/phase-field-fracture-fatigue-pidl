import copy,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('rescore',ROOT/'scripts/pavetrack_rescore_cv/run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
CFG=m.read(ROOT/'docs/research/S01/S01-E008/run_config.json')
def fixture():
 old=dict(image_id='a',reid='24',parent_id=0,candidate_id='o:0',kind='original',box_xyxy=[0,0,4,10],score=.2,E003_score=.2,probability=.05,proposer_confidence=.81)
 other=dict(old,image_id='b',parent_id=1,candidate_id='o:1',box_xyxy=[0,0,10,10],score=.8,E003_score=.8,probability=.8)
 new=dict(old,candidate_id='c:0',kind='correction',box_xyxy=[0,0,10,10],original_box_xyxy=old['box_xyxy'])
 return [old,other],[old,new]
def test_addition_promotes_new_hit_without_editing_originals():
 originals,pairs=fixture();saved=copy.deepcopy(originals);rows,choice=m.added_bank(originals,pairs,[.81],CFG,1.)
 assert rows[:2]==saved and originals==saved;assert rows[2]['score']==pytest.approx(.81);assert rows[2]['probability']==.81;assert choice['accepted_corrections']==1
 records=[dict(image_id=im,reid='24',crack_boxes_xyxy=[[0,0,10,10]]) for im in ['a','b']]
 e=m.evaluate({'original_rows':originals,'bank':pairs},records,[.81],CFG,1.)
 assert e['retention']==1.;assert e['net_targets']==1;assert e['new_detected_targets']==1;assert e['protected_primary_pass'] is True

def test_ratio_equality_abstains_and_invalid_scores_fail():
 original,pairs=fixture();prob=original[0]['score']**2/original[0]['proposer_confidence']
 assert m.added_bank(original,pairs,[prob],CFG,1.)[1]['accepted_corrections']==0
 for bad in [float('nan'),float('inf'),-1,1.1]:
  with pytest.raises(ValueError):m.added_bank(original,pairs,[bad],CFG,1.)
 with pytest.raises(ValueError):m.added_bank(original,pairs,[.9],CFG,1.1)
def test_near_duplicate_cannot_replace_original_even_high_score():
 original,pairs=fixture();pairs[1]['box_xyxy']=original[0]['box_xyxy']
 rows,c=m.added_bank(original,pairs,[1.],CFG,1.)
 assert rows==original;assert c['original_duplicate_rejected']==1

def test_correction_nms_keeps_original_and_higher_scored_alternative():
 original,pairs=fixture();second=dict(original[0],parent_id=2,candidate_id='o:2',box_xyxy=[20,0,24,10]);original.append(second);correction=dict(second,kind='correction',candidate_id='c:2',box_xyxy=[0,0,10,10],original_box_xyxy=second['box_xyxy']);pairs.extend([second,correction])
 rows,c=m.added_bank(original,pairs,[.81,.9],CFG,1.)
 assert rows[:3]==original;assert c['correction_duplicate_rejected']==1;assert rows[-1]['parent_id']==2

def test_missing_baseline_hits_blocks_qualification():
 original,pairs=fixture();original=original[:1];records=[dict(image_id='a',reid='24',crack_boxes_xyxy=[[0,0,10,10]])];e=m.evaluate({'original_rows':original,'bank':pairs},records,[.81],CFG,1.)
 assert e['retention'] is None and e['qualified'] is False
 decision=m.decision_fields({},[e],CFG,'sha');assert decision['status']=='inconclusive_qualification_metric'

def test_selection_ties_choose_larger_ratio_and_entire_receipt_binds_fresh():
 row=dict(qualified=True,delta=.1,retention=1.,net_targets=2,choice={'accepted_corrections':3},score_ratio=1.)
 second=copy.deepcopy(row);second['score_ratio']=2.;d=m.decision_fields({'protocol':'S01-E008-v1'},[row,second],CFG,'sha');assert d['selected_score_ratio']==2.
 assert d['fresh_access'] is False;assert dict(d,fresh_access=True)!=m.decision_fields({'protocol':'S01-E008-v1'},[row,second],CFG,'sha')

def test_parent_mutation_rejected():
 original,pairs=fixture();pairs[0]=dict(pairs[0],score=.25)
 with pytest.raises(ValueError):m.added_bank(original,pairs,[.9],CFG,1.)

def test_actual_config_and_lock_bound_to_frozen_manifest(tmp_path):
 config=ROOT/'docs/research/S01/S01-E008/run_config.json';lock=ROOT/'docs/research/S01/S01-E008/data_lock.json'
 c=tmp_path/'config.json';l=tmp_path/'lock.json';c.write_bytes(config.read_bytes());l.write_bytes(lock.read_bytes());m.check_contract_paths(c,l)
 for key,value in [('primary_delta',0),('minimum_retention',0),('crop_padding',.2),('score_ratio_limits',[1.]),('maximum_qualification_corrections',99999)]:
  changed=m.read(config);changed[key]=value;c.write_text(json.dumps(changed))
  with pytest.raises(ValueError):m.check_contract_paths(c,l)
 c.write_bytes(config.read_bytes());l.write_text(json.dumps(dict(m.read(lock),protocol='changed')))
 with pytest.raises(ValueError):m.check_contract_paths(c,l)
