import copy,importlib.util,json,random
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e015_tests',ROOT/'scripts/pavetrack_locality_selector/run.py');r=a.r;c=a.c;l=a.locality
old=module('e015_fixture_only',ROOT/'tests/pavetrack_geometry_selector/test_geometry.py');CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard():return r.Guard(CFG,memory=lambda:100)
def fixture():
    d,t=old.fixture()
    for row in d['manifest']:
        if row['location'] in {'514','1577','728','4494','2027'}:
            row['corrected_box_xyxy']=[5,0,15,10];t[row['image_id']][1]=[5,0,15,10]
    d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],CFG)
    return d,t

def test_config_changes_only_gate_and_private_ancestors_unchanged():
    cfg=copy.deepcopy(CFG);before=copy.deepcopy(old.CFG)
    assert old.c.PROTOCOL=='S01-E014-v1' and old.c.policy is not c.policy
    for v in [cfg,before]:v.pop('protocol');v.pop('proposed_run_id');v['policy'].pop('eligibility')
    cfg.pop('locality');cfg.pop('locality_audit');assert cfg==before
    assert r.BOOT_START==a.BOOT_START

@pytest.mark.parametrize('new,expected',[
    ([1,0,2,1],False),([1,1,2,2],False),([1.1,0,2,1],False),
    ([.9999999999999999,0,2,1],True),([.2,.2,.8,.8],True),([-1,0,.1,1],True)])
def test_strict_positive_overlap_not_edges_corners_or_epsilon(new,expected):
    assert l.positive_intersection(dict(original_box_xyxy=[0,0,1,1],box_xyxy=new)) is expected

@pytest.mark.parametrize('new',[[0,0,0,1],[0,0,float('nan'),1],[0,0,1]])
def test_invalid_box_rejected(new):
    with pytest.raises(ValueError):l.positive_intersection(dict(original_box_xyxy=[0,0,1,1],box_xyxy=new))

def test_tiny_positive_area_not_replaced_by_area_product_or_d_less_than_one():
    row=dict(original_box_xyxy=[0,0,1e-200,1e-200],box_xyxy=[0,0,2e-200,2e-200],score=.9,parent_id=1,image_id='tiny',reid='24')
    assert 1e-200*1e-200==0 and l.positive_intersection(row)
    d=old.g.geometry_change(row,c);assert d==1
    candidate=dict(row=row,parent_id=1,location='24',image_id='tiny',x=1.,eligible=True,geometry_change=d,positive_intersection=True)
    assert c.policy([candidate],0.,['24'],CFG)==[row]

def test_base_eligibility_and_scores_preserved_and_GT_poison_ignored():
    d,t=fixture();prior=old.c.features(d['originals'],d['manifest'],d['probabilities'],old.CFG);saved=copy.deepcopy(d['originals']);poison=copy.deepcopy(d['manifest'])
    for row in poison:row.update(GT=[999],U=999,positive_intersection=False)
    assert c.features(d['originals'],poison,d['probabilities'],CFG)==d['candidates']
    for new,before in zip(d['candidates'],prior,strict=True):
        trimmed=dict(new);trimmed.pop('positive_intersection');assert trimmed==before
    added=c.policy(d['candidates'],0.,CFG['locations'],CFG);assert d['originals']==saved
    for row in added:assert row==next(x['row'] for x in d['candidates'] if x['parent_id']==row['parent_id'])

def test_filter_precedes_capacity_and_actual_joint_gain_in_constructed_scene():
    d,t=fixture();before=old.c.policy(d['candidates'],0.,CFG['locations'],old.CFG);added=c.policy(d['candidates'],0.,CFG['locations'],CFG)
    assert len(added)==6 and all(l.positive_intersection(x) for x in added)
    assert any(not l.positive_intersection(x) for x in before)
    own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],CFG['locations']);comparison=c.compare(own,added,c.baseline(own))
    assert comparison['retention']==1 and comparison['net_GT']==comparison['new_GT']==6
    assert len({x['image_id'] for x in added})==6
    assert all(sum(c.group_of(x['reid'],CFG)==k for x in added)<=3 for k in range(3))

@pytest.mark.parametrize('seed',[0,12])
def test_when_gate_keeps_all_candidates_E014_order_is_exactly_preserved(seed):
    d,t=fixture()
    for row in d['manifest']:row['corrected_box_xyxy']=[2,0,12,10]
    candidates=c.features(d['originals'],d['manifest'],d['probabilities'],CFG);assert all(x['positive_intersection'] for x in candidates)
    expected=old.c.policy(candidates,0.,CFG['locations'],old.CFG);random.Random(seed).shuffle(candidates)
    assert c.policy(candidates,0.,CFG['locations'],CFG)==expected

def test_gate_cannot_revive_base_ineligible_and_marker_tamper_denied():
    d,t=fixture();first=next(x for x in d['candidates'] if x['positive_intersection']);first['eligible']=False
    assert first['row'] not in c.policy(d['candidates'],0.,CFG['locations'],CFG)
    first['eligible']=True;first['positive_intersection']=False
    with pytest.raises(ValueError,match='representation'):c.policy(d['candidates'],0.,CFG['locations'],CFG)
    assert c.policy(d['candidates'],'abstain',CFG['locations'],CFG)==[]
    with pytest.raises(ValueError,match='threshold'):c.policy(d['candidates'],.123,CFG['locations'],CFG)

def fitted(path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture();ex,emit=old.emit_for(path);watch=guard();models,support,added=r.fit_and_freeze(d,t,path,CFG,watch,emit);return d,t,models,support,added,ex,watch

def test_main_freeze_counts_retention_capacity_and_held_GT_isolation(tmp_path,monkeypatch):
    d,t,models,support,added,ex,watch=fitted(tmp_path,monkeypatch)
    assert len(added)==6 and [s['positive_GT_count'] for s in support]==[3,5,6]
    assert [x['positive_GT_before'] for x in ex['locality_audit.json']['folds']]==[3,5,6]
    assert [x['positive_GT_after'] for x in ex['locality_audit.json']['folds']]==[3,5,6]
    assert ex['locality_audit.json']['all12_pool']==dict(base_eligible=14,retained=7,removed=7)
    assert all(x['chosen_policy']['selected_positive_GT']>0 for x in ex['capacity_audit.json']['folds'])
    assert watch.counts['threshold_fits']==13 and watch.counts['calibration_policy_comparisons']==91
    other=tmp_path/'poison';other.mkdir();poison=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in CFG['held_groups'][0]:poison[im]=[]
    ex2,emit=old.emit_for(other);m2,_,_=r.fit_and_freeze(d,poison,other,CFG,guard(),emit)
    assert m2[0]==models[0] and ex2['OOF_predictions.json']['folds'][0]==ex['OOF_predictions.json']['folds'][0]
    for name,h in ex['prediction_freeze_receipt.json']['files'].items():assert c.sha(tmp_path/name)==h

def test_locality_audit_changes_cannot_feedback_predictions(tmp_path,monkeypatch):
    d,t,models,_,_,ex,_=fitted(tmp_path,monkeypatch);other=tmp_path/'other';other.mkdir();ex2,emit=old.emit_for(other)
    monkeypatch.setattr(l,'retention_audit',lambda *args:dict(arbitrary_after_support=0))
    mod2,_,_=r.fit_and_freeze(d,t,other,CFG,guard(),emit)
    assert mod2==models and ex2['OOF_predictions.json']==ex['OOF_predictions.json']

def test_original_singleton_support_can_drop_to_zero_without_forcing_a_model_choice():
    d,t=fixture()
    for x in d['candidates']:x['positive_intersection']=False
    audit=l.retention_audit(d,CFG);assert [x['positive_GT_after'] for x in audit['folds']]==[0,0,0]
    assert not audit['used_to_choose_main']
    # Scripted joint table isolates the non-additivity contract, not real detection.
    table=[dict(threshold=0.,comparison=dict(retention=1,net_GT=1,macro_delta=.1,added_FP=0,appended=1))]
    before=copy.deepcopy(table);l.retention_audit(d,CFG);assert c.choose(table)==0. and table==before

def test_retained_GT_deduplicates_multiple_supporting_candidates():
    d,t=fixture();payload=d['labels'][0];positive=[x for x in payload['rows'] if x['U']>0];positive[1]['new_identities']=copy.deepcopy(positive[0]['new_identities']);by={x['parent_id']:x for x in d['candidates']};by[positive[0]['parent_id']]['positive_intersection']=False
    row=l.retention_audit(d,CFG)['folds'][0]
    assert row['positive_candidates_removed']==1 and row['positive_GT_removed']==0

@pytest.mark.parametrize('kind',['scope','identity','GT','duplicate'])
def test_locality_audit_rejects_scope_and_identity_tampering(kind):
    d,t=fixture()
    if kind=='scope':d['labels'][0]['locations']=CFG['held_groups'][0]
    elif kind=='identity':d['labels'][0]['rows'][0]['index']=-1
    elif kind=='GT':d['labels'][0]['rows'][0]['new_identities']=[[next(im for im,loc in d['image_locations'].items() if loc in CFG['held_groups'][0]),0]]
    else:d['labels'][0]['rows'].append(d['labels'][0]['rows'][0])
    with pytest.raises(ValueError):l.retention_audit(d,CFG)

def test_complete_synthetic_pipeline_plots_counts_and_semantic_locality_tamper(tmp_path,monkeypatch):
    d,t=fixture();cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);run=tmp_path/'run';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'qualification.json',dict(status='synthetic',joint=dict(retained_old=14,net_targets=7),held_support=[]));d['snapshot']=snap
    lock=dict(original_rows_digest=c.digest(d['originals']),source_B12_hits=14,source_zip_sha256='synthetic',source_files={'qualification.json':c.sha(snap/'qualification.json')})
    monkeypatch.setattr(r.inputs,'load',lambda *args:d);monkeypatch.setattr(r.inputs,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None);monkeypatch.setattr(r.sys,'addaudithook',lambda hook:None)
    args=SimpleNamespace(source=tmp_path/'source.zip',metadata=tmp_path/'meta.json',run=run);launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard();result=r.execute(args,cfg,lock,watch,launch)
    assert result['primary_pass'] and result['comparison']['retention']==1 and result['comparison']['net_GT']==6
    assert watch.counts==dict(threshold_fits=13,fit_baseline_metrics=13,calibration_policy_comparisons=91,final_OOF_comparisons=1,held_group_comparisons=3)
    assert len(list((run/'analysis').glob('*.png')))==3
    readme=(run/'analysis/README_analysis.md').read_text();assert 'Only new decision' in readme and 'Inherited E014' in readme and 'all12 GT-free' in readme
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')}
    bad=c.read(run/'locality_audit.json');bad['all12_pool']['removed']=999;c.write(run/'locality_audit.json',bad);receipt['files']['locality_audit.json']=c.sha(run/'locality_audit.json')
    with pytest.raises(ValueError,match='semantic'):r.verify(run,expected,receipt,lock['source_files'])

def test_producer_gate_denies_actual_calibration_on_Mac(monkeypatch):
    monkeypatch.setattr(c,'baseline',lambda *args:pytest.fail('actual calibration must not start'))
    with pytest.raises(PermissionError):c.calibrate({},CFG,guard())

def test_locked_synthetic_importer_preserves_base_count_even_if_gate_removes_all(tmp_path):
    d,t,cfg,lock,run,source=old.old.zip_fixture(tmp_path);cfg['protocol']=CFG['protocol'];loaded=r.inputs.load(source,run,cfg,lock,guard(),c)
    assert loaded['originals']==d['originals'] and loaded['labels']==d['labels']
    assert sum(x['eligible'] for x in loaded['candidates'])==lock['source_eligible_count']
    assert not any(x['positive_intersection'] for x in loaded['candidates'])
    for new,prior in zip(loaded['candidates'],d['candidates'],strict=True):
        trimmed=dict(new);trimmed.pop('positive_intersection');trimmed.pop('geometry_change');assert trimmed==prior
