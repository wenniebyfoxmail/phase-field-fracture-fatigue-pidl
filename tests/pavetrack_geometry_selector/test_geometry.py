import copy,importlib.util,json,random
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
a=module('e014_tests',ROOT/'scripts/pavetrack_geometry_selector/run.py');r=a.r;c=a.c;g=a.geometry
old=module('e014_fixture_only',ROOT/'tests/pavetrack_protected_selector/test_selector.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard():return r.Guard(CFG,memory=lambda:100)
def fixture(geometry_case=False):
    d,t=old.fixture()
    if geometry_case:
        d['originals']=[x for x in d['originals'] if x['score']!=.9]
        for i,row in enumerate(d['manifest']):
            if row['location'] not in {'514','1577','728','4494','2027'}:
                row['corrected_box_xyxy']=[2,0,12,10];d['probabilities'][i]=.95**2
        for payload in d['labels']:
            for row in payload['rows']:
                if row['U']<0:row.update(U=0,FP=0)
    d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],CFG)
    return d,t

def emit_for(path):return old.recording_emitter(path)

def test_only_ranking_config_changes_and_private_import_isolation():
    cfg=copy.deepcopy(CFG);before=copy.deepcopy(old.CFG)
    assert old.c.CONTRACT=='docs/research/S01/S01-E013/' and c.CONTRACT=='docs/research/S01/S01-E014/'
    assert old.c.policy is not c.policy and old.c.features is not c.features
    for obj in [cfg,before]:obj.pop('protocol');obj.pop('proposed_run_id');obj['policy'].pop('correction_order')
    cfg.pop('ranking');cfg.pop('capacity_audit');assert cfg==before
    assert r.BOOT_START==a.BOOT_START

def test_geometry_GT_free_feature_scope_and_scores_originals_unchanged():
    d,t=fixture(True);original=copy.deepcopy(d['originals']);mf=copy.deepcopy(d['manifest']);base=copy.deepcopy(d['candidates'])
    for row in mf:row.update(GT=[999],U=999,oracle=True,geometry_change=-99)
    assert c.features(d['originals'],mf,d['probabilities'],CFG)==base
    assert all(x['geometry_change']==1-c.e8.box_iou(x['row']['original_box_xyxy'],x['row']['box_xyxy']) for x in base)
    for new in c.policy(base,0.,CFG['locations'],CFG):assert new==next(x['row'] for x in base if x['parent_id']==new['parent_id'])
    assert d['originals']==original

@pytest.mark.parametrize('box',[[0,0,0,10],[0,0,10,float('nan')],[0,0,10],[10,0,0,10]])
def test_invalid_geometry_denied(box):
    with pytest.raises(ValueError):g.geometry_change(dict(original_box_xyxy=[0,0,10,10],box_xyxy=box),c)

def test_geometry_order_admits_lower_classifier_score_and_actual_joint_gain():
    d,t=fixture(True);baseline=old.c.policy(d['candidates'],0.,CFG['locations'],old.CFG);added=c.policy(d['candidates'],0.,CFG['locations'],CFG)
    positives={x['parent_id'] for x in d['candidates'] if x['location'] in {'514','1577','728','4494','2027'}}
    assert len({x['parent_id'] for x in added}&positives)==6
    assert len({x['parent_id'] for x in baseline}&positives)<6
    own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],CFG['locations']);ref=c.baseline(own);out=c.compare(own,added,ref)
    assert out['retention']==1 and out['new_GT']==out['net_GT']==6
    assert len(added)<=9 and len({x['image_id'] for x in added})==len(added)
    assert all(sum(c.group_of(x['reid'],CFG)==k for x in added)<=3 for k in range(3))

@pytest.mark.parametrize('seed',[0,19,98])
def test_d_equals_one_ties_exactly_reuse_s0_lexical_order(seed):
    d,t=fixture();rows=d['candidates'];assert all(x['geometry_change']==1 for x in rows)
    expected=old.c.policy(rows,0.,CFG['locations'],old.CFG);random.Random(seed).shuffle(rows)
    assert c.policy(rows,0.,CFG['locations'],CFG)==expected

def test_corrupt_ranking_value_denied_and_abstain_and_threshold_frozen():
    d,t=fixture();d['candidates'][0]['geometry_change']=.123
    with pytest.raises(ValueError,match='representation'):c.policy(d['candidates'],0.,CFG['locations'],CFG)
    assert c.policy(d['candidates'],'abstain',CFG['locations'],CFG)==[]
    with pytest.raises(ValueError,match='threshold'):c.policy(d['candidates'],3.2,CFG['locations'],CFG)

def test_rejected_duplicate_never_consumes_source_cap():
    d,t=fixture();rows=copy.deepcopy(d['candidates']);duplicate=copy.deepcopy(rows[0]);duplicate['parent_id']=9999;duplicate['row']['parent_id']=9999;duplicate['row']['score']-=.0001;rows.insert(1,duplicate)
    assert c.policy(rows,0.,CFG['locations'],CFG)==c.policy(d['candidates'],0.,CFG['locations'],CFG)

def fitted(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture(True);expected,emit=emit_for(tmp_path);models,support,added=r.fit_and_freeze(d,t,tmp_path,CFG,guard(),emit);return d,t,models,support,added,expected

def test_main_freeze_counts_membership_and_held_GT_poison(tmp_path,monkeypatch):
    d,t,models,support,added,ex=fitted(tmp_path,monkeypatch);audit=ex['capacity_audit.json']
    assert [s['positive_GT_count'] for s in support]==[3,5,6]
    assert [x['available_positive_GT'] for x in audit['folds']]==[3,5,6]
    assert all(x['chosen_policy']['selected_positive_GT']>0 for x in audit['folds'])
    assert len(ex['jackknife.json']['fits'])==10 and len(models)==3 and len(added)==9
    assert not audit['used_to_choose_main'] and audit['new_policy_comparisons']==audit['new_U']==0
    before=copy.deepcopy(ex['OOF_predictions.json']);poison=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in CFG['held_groups'][0]:poison[im]=[]
    other=tmp_path/'poison';other.mkdir();ex2,emit=emit_for(other);mods,_,_=r.fit_and_freeze(d,poison,other,CFG,guard(),emit)
    assert mods[0]==models[0] and ex2['OOF_predictions.json']['folds'][0]==before['folds'][0]
    for name,h in ex['prediction_freeze_receipt.json']['files'].items():assert c.sha(tmp_path/name)==h

def test_audit_output_cannot_feedback_main_thresholds_or_frozen_predictions(tmp_path,monkeypatch):
    d,t,models,_,_,ex=fitted(tmp_path,monkeypatch);other=tmp_path/'other';other.mkdir();ex2,emit=emit_for(other)
    monkeypatch.setattr(g,'capacity_audit',lambda *args:dict(arbitrary_GT_count=999,used_to_choose_main=False))
    mod2,_,_=r.fit_and_freeze(d,t,other,CFG,guard(),emit)
    assert mod2==models and ex2['OOF_predictions.json']==ex['OOF_predictions.json']

def test_audit_accidental_main_mutation_fails_before_evaluation(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture(True);ex,emit=emit_for(tmp_path)
    def mutate(data,models,cfg):models[0]['threshold']='abstain';return {}
    monkeypatch.setattr(g,'capacity_audit',mutate)
    with pytest.raises(ValueError,match='mutated'):r.fit_and_freeze(d,t,tmp_path,CFG,guard(),emit)
    assert 'OOF_predictions.json' in ex and 'evaluation.json' not in ex

def audit_fixture():
    d,t=fixture();models=[]
    for k,labels in enumerate(d['labels']):
        pos=[r for r in labels['rows'] if r['U']>0];pos[1]['new_identities']=copy.deepcopy(pos[0]['new_identities']);keys=[r['parent_id'] for r in pos[:2]]
        table=[dict(threshold=tau,source_keys=[] if tau=='abstain' else keys,comparison=dict(new_GT=0,net_GT=0)) for tau in CFG['feature']['thresholds']]
        models.append(dict(locations=labels['locations'],threshold='abstain',policies=table))
    return d,models

def test_membership_deduplicates_GT_and_does_not_rescue_abstention():
    d,models=audit_fixture();before=copy.deepcopy([d,models]);audit=g.capacity_audit(d,models,CFG)
    for row in audit['folds']:
        assert row['policies'][0]['selected_positive_candidates']==2 and row['policies'][0]['selected_positive_GT']==1
        assert row['max_policy_positive_GT']==1 and row['chosen_policy']['selected_positive_GT']==0 and row['chosen_policy']['joint_net_GT']==0
    assert [d,models]==before

@pytest.mark.parametrize('kind',['scope','GT','selected','duplicate','inventory'])
def test_capacity_audit_denies_foreign_GT_policy_keys_and_inventory(kind):
    d,models=audit_fixture()
    if kind=='scope':d['labels'][0]['locations']=CFG['held_groups'][0]
    elif kind=='GT':d['labels'][0]['rows'][0]['new_identities']=[[next(im for im,loc in d['image_locations'].items() if loc in CFG['held_groups'][0]),0]]
    elif kind=='selected':models[0]['policies'][0]['source_keys']=[-1]
    elif kind=='duplicate':models[0]['policies'][0]['source_keys']*=2
    else:models[0]['policies'].pop()
    with pytest.raises(ValueError):g.capacity_audit(d,models,CFG)

def test_synthetic_pipeline_with_plots_semantic_tamper_and_exact_phase_budget(tmp_path,monkeypatch):
    d,t=fixture(True);cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);run=tmp_path/'run';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'qualification.json',dict(status='synthetic',joint=dict(retained_old=14,net_targets=7),held_support=[]));d['snapshot']=snap
    lock=dict(original_rows_digest=c.digest(d['originals']),source_B12_hits=14,source_zip_sha256='synthetic',source_files={'qualification.json':c.sha(snap/'qualification.json')})
    monkeypatch.setattr(r.inputs,'load',lambda *args:d);monkeypatch.setattr(r.inputs,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None);monkeypatch.setattr(r.sys,'addaudithook',lambda hook:None)
    args=SimpleNamespace(source=tmp_path/'source.zip',metadata=tmp_path/'meta.json',run=run);launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard();result=r.execute(args,cfg,lock,watch,launch)
    assert result['primary_pass'] and result['comparison']['retention']==1 and result['comparison']['net_GT']==6
    assert watch.counts==dict(threshold_fits=13,fit_baseline_metrics=13,calibration_policy_comparisons=91,final_OOF_comparisons=1,held_group_comparisons=3)
    assert len(list((run/'analysis').glob('*.png')))==3
    readme=(run/'analysis/README_analysis.md').read_text();assert 'Single changed ranking' in readme and 'E013 conditional' not in readme and 'Budget-admitted FP decomposition' in readme
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')}
    bad=c.read(run/'capacity_audit.json');bad['folds'][0]['chosen_policy']['selected_positive_GT']=999;c.write(run/'capacity_audit.json',bad);receipt['files']['capacity_audit.json']=c.sha(run/'capacity_audit.json')
    with pytest.raises(ValueError,match='semantic'):r.verify(run,expected,receipt,lock['source_files'])

def test_producer_gate_still_precedes_real_calibration(monkeypatch):
    monkeypatch.setattr(c,'baseline',lambda *args:pytest.fail('must not enter actual metrics on Mac'))
    with pytest.raises(PermissionError):c.calibrate({},CFG,guard())


def test_locked_synthetic_importer_adds_only_geometry_representation(tmp_path):
    data,t,cfg,lock,run,source=old.zip_fixture(tmp_path);cfg['protocol']=CFG['protocol']
    loaded=r.inputs.load(source,run,cfg,lock,guard(),c)
    assert loaded['originals']==data['originals'] and loaded['labels']==data['labels']
    for new,prior in zip(loaded['candidates'],data['candidates'],strict=True):
        trimmed=dict(new);value=trimmed.pop('geometry_change')
        assert trimmed==prior and value==g.geometry_change(new['row'],c)
