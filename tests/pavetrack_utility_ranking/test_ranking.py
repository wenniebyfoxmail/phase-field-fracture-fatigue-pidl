import copy,importlib.util,json,math,random
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e016_tests',ROOT/'scripts/pavetrack_utility_ranking/run.py');r=a.r;c=a.c;k=a.ranking
old=module('e016_fixture_only',ROOT/'tests/pavetrack_locality_selector/test_locality.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def fixture():
    d,t=old.fixture()
    # Constructed positive case: leave FP budget room while distractors win old ordering.
    d['originals']=[r for r in d['originals'] if r['score']!=.9]
    for i,row in enumerate(d['manifest']):
        if row['location'] not in {'514','1577','728','4494','2027'}:
            row['corrected_box_xyxy']=[9.99,0,19.99,10];d['probabilities'][i]=.99
    d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],CFG)
    return d,t

def emit_for(path):return old.old.emit_for(path)

def test_private_ancestors_and_producer_only_no_legacy_threshold_grid():
    assert old.c.PROTOCOL=='S01-E015-v1' and c.PROTOCOL=='S01-E016-v1' and old.c.policy is not c.policy
    assert CFG['ranking']['mixtures']==[0.,.25,.5,.75,1.,'abstain'] and 'thresholds' not in CFG['feature']
    assert CFG['budget']['ranking_fits']==13 and CFG['budget']['calibration_policy_comparisons']==78
    assert r.BOOT_START==a.BOOT_START
    with pytest.raises(PermissionError):a.calibrate({},CFG,guard())


def test_actual_synthetic_capacity_competition_learns_utility_not_largest_displacement(monkeypatch):
    d,t=fixture();own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],CFG['locations']);ref=c.baseline(own)
    pre=old.c.policy(d['candidates'],0.,CFG['locations'],old.CFG);bad=a.policy(d['candidates'],0.,CFG['locations'],CFG);good=a.policy(d['candidates'],.5,CFG['locations'],CFG)
    assert c.compare(own,pre,ref)['new_GT']==c.compare(own,bad,ref)['new_GT']==2
    comparison=c.compare(own,good,ref);assert comparison['retention']==1 and comparison['new_GT']==comparison['net_GT']==6
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);watch=guard();model=a.calibrate(own,CFG,watch)
    assert model['mixture']==.5 and not model['per_candidate_U_regression'] and watch.counts==dict(ranking_fits=1,fit_baseline_metrics=1,calibration_policy_comparisons=6)
    assert model['policies'][0]['comparison']['new_GT']==2 and model['policies'][2]['comparison']['new_GT']==6
    assert d['originals']==fixture()[0]['originals']


def summary(alpha,net=1,fp=0,n=1,ret=1,delta=.1):return dict(mixture=alpha,comparison=dict(net_GT=net,added_FP=fp,appended=n,retention=ret,macro_delta=delta))
@pytest.mark.parametrize('table,expected',[
    ([summary(0,ret=.99),summary(.5,net=0)],'abstain'),
    ([summary(0),summary(.5)],0),([summary(0,fp=1),summary(.5)],.5),
    ([summary(0,n=2),summary(.5)],.5),([summary(0,net=2),summary(.5)],0),
    ([summary(.5,delta=0)],'abstain'),([summary(.5,delta=None)],'abstain'),
    ([summary(.5,net=-1),summary(1,net=0)],'abstain')])
def test_actual_joint_protection_tie_break_and_zero_gain_abstain(table,expected):assert k.choose(table)==expected


@pytest.mark.parametrize('value',[.125,-1,2,True,float('nan')])
def test_unfrozen_or_boolean_policy_denied(value):
    d,t=fixture()
    with pytest.raises(ValueError):a.policy(d['candidates'],value,CFG['locations'],CFG)


def test_GT_free_features_and_scores_base_eligibility_immutable():
    d,t=fixture();saved=copy.deepcopy(d['originals']);mf=copy.deepcopy(d['manifest'])
    for row in mf:row.update(U=999,GT=[999],oracle=True,bounded_gain=999,original_corrected_IoU=1.)
    assert c.features(d['originals'],mf,d['probabilities'],CFG)==d['candidates']
    prior=old.c.features(d['originals'],d['manifest'],d['probabilities'],old.CFG)
    for row,before in zip(d['candidates'],prior,strict=True):
        trim=dict(row);trim.pop('bounded_gain');trim.pop('original_corrected_IoU');assert trim==before
    added=a.policy(d['candidates'],.5,CFG['locations'],CFG)
    for row in added:assert row==next(x['row'] for x in d['candidates'] if row['parent_id']==x['parent_id'])
    assert d['originals']==saved


@pytest.mark.parametrize('field,value',[('bounded_gain',999),('original_corrected_IoU',float('nan')),('positive_intersection',False),('x',float('inf'))])
def test_feature_or_locality_tampering_denied(field,value):
    d,t=fixture();d['candidates'][0][field]=value
    with pytest.raises(ValueError):a.policy(d['candidates'],.5,CFG['locations'],CFG)


def test_deterministic_rank_and_accepted_only_cap_traces():
    d,t=fixture();added,trace=k.select(d['candidates'],.5,CFG['locations'],CFG,c,a.locality);rows=copy.deepcopy(d['candidates']);random.Random(16).shuffle(rows)
    assert k.select(rows,.5,CFG['locations'],CFG,c,a.locality)==(added,trace)
    assert len(added)<=9 and len({x['image_id'] for x in added})==len(added)
    assert set(trace['accepted_source_keys'])=={x['parent_id'] for x in added}
    for group,counts in trace['groups'].items():
        assert counts.get('accepted',0)<=3
        assert counts['considered']==sum(counts.get(x,0) for x in ['accepted','rejected_duplicate','rejected_image_cap','rejected_group_cap'])
    duplicate=copy.deepcopy(rows[0]);duplicate['parent_id']=99999;duplicate['row']['parent_id']=99999;duplicate['row']['score']-=.0001;rows.append(duplicate)
    assert a.policy(rows,.5,CFG['locations'],CFG)==added
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError,match='duplicate identity'):a.policy(rows,.5,CFG['locations'],CFG)


def test_base_rejected_and_gate_rejected_never_consume_capacity():
    d,t=fixture();base=copy.deepcopy(d['candidates']);first=base[0];first['eligible']=False
    assert first['row'] not in a.policy(base,.5,CFG['locations'],CFG)
    base[0]['row']['box_xyxy']=[50,50,60,60];base[0]['positive_intersection']=False;base[0]['eligible']=True;base[0]['bounded_gain'],base[0]['original_corrected_IoU']=k.representation(base[0],c)
    added,trace=k.select(base,.5,CFG['locations'],CFG,c,a.locality)
    assert first['row'] not in added and any(x.get('rejected_locality',0) for x in trace['groups'].values())
    assert a.policy(base,'abstain',CFG['locations'],CFG)==[]


def test_no_area_epsilon_or_h_cutoff_even_when_IoU_underflows():
    row=dict(original_box_xyxy=[0,0,1e-200,1e-200],box_xyxy=[0,0,2e-200,2e-200],score=.9,parent_id=1,image_id='tiny',reid='24')
    candidate=dict(row=row,index=0,parent_id=1,location='24',image_id='tiny',x=1.,eligible=True,positive_intersection=True)
    candidate['bounded_gain'],candidate['original_corrected_IoU']=k.representation(candidate,c)
    assert candidate['original_corrected_IoU']==0 and a.policy([candidate],1.,['24'],CFG)==[row]


def fitted(path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture();ex,emit=emit_for(path);watch=guard();models,support,added=a.fit_and_freeze(d,t,path,CFG,watch,emit);return d,t,models,support,added,ex,watch


def test_complete_fits_main_freeze_before_diagnostics_counts_and_held_GT_isolation(tmp_path,monkeypatch):
    d,t,models,support,added,ex,watch=fitted(tmp_path,monkeypatch)
    assert [s['positive_GT_count'] for s in support]==[3,5,6] and [m['mixture'] for m in models]==[.5]*3
    assert len(added)==9 and watch.counts==dict(ranking_fits=13,fit_baseline_metrics=13,calibration_policy_comparisons=78)
    assert len(ex['jackknife.json']['fits'])==10
    for name,h in ex['prediction_freeze_receipt.json']['files'].items():assert c.sha(tmp_path/name)==h
    assert all(f['chosen_policy']['selected_positive_GT']>0 for f in ex['capacity_audit.json']['folds'])
    poison=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in CFG['held_groups'][0]:poison[im]=[]
    other=tmp_path/'poison';other.mkdir();ex2,emit=emit_for(other);m2,_,_=a.fit_and_freeze(d,poison,other,CFG,guard(),emit)
    assert m2[0]==models[0] and ex2['OOF_predictions.json']['folds'][0]==ex['OOF_predictions.json']['folds'][0]


def test_diagnostic_mutation_and_audit_counts_do_not_feedback(tmp_path,monkeypatch):
    d,t,models,support,added,ex,_=fitted(tmp_path,monkeypatch);other=tmp_path/'other';other.mkdir();ex2,emit=emit_for(other)
    def own(own,cfg,g):
        if len(own['locations'])<8:
            own['originals'].clear();own['candidates'].clear();own['targets'].clear();return dict(mixture='abstain',abstained=True)
        return a.calibrate(own,cfg,g)
    m2,_,ad2=a.fit_and_freeze(d,t,other,CFG,guard(),emit,own)
    assert m2==models and ad2==added and ex2['OOF_predictions.json']==ex['OOF_predictions.json']
    third=tmp_path/'third';third.mkdir();ex3,emit=emit_for(third);monkeypatch.setattr(k,'audits',lambda *args:(dict(fake=0),dict(fake=999)))
    m3,_,ad3=a.fit_and_freeze(d,t,third,CFG,guard(),emit)
    assert m3==models and ad3==added and ex3['OOF_predictions.json']==ex['OOF_predictions.json']


def test_audit_main_mutation_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture();ex,emit=emit_for(tmp_path)
    def mutate(data,models,*args):models[0]['mixture']='abstain';return {},{}
    monkeypatch.setattr(k,'audits',mutate)
    with pytest.raises(ValueError,match='mutated'):a.fit_and_freeze(d,t,tmp_path,CFG,guard(),emit)
    assert 'evaluation.json' not in ex


def test_zero_descriptive_support_does_not_override_true_joint_choice():
    d,t=fixture()
    for candidate in d['candidates']:candidate['positive_intersection']=False
    # Audit alone may report support loss; it must never choose an alpha.
    models=[]
    for held in CFG['held_groups']:
        fit=[x for x in CFG['locations'] if x not in held];models.append(dict(locations=fit,mixture=.5,policies=[dict(mixture=v,source_keys=[],comparison=dict(new_GT=0,net_GT=0)) for v in CFG['ranking']['mixtures']]))
    retained,capacity=k.audits(d,models,CFG,c,a.locality)
    assert [f['positive_GT_after'] for f in retained['folds']]==[0]*3 and not capacity['used_to_choose_main']
    assert k.choose([summary(.5)])==.5


@pytest.mark.parametrize('kind',['RSS','WALL','COUNT'])
def test_resource_limits(kind):
    if kind=='RSS':g=a.Guard(CFG,memory=lambda:2**33)
    elif kind=='WALL':g=a.Guard(CFG,start=0,clock=lambda:4000,memory=lambda:0)
    else:g=guard();g.counts['ranking_fits']=13
    with pytest.raises(RuntimeError):g.take('ranking_fits') if kind=='COUNT' else g.check()


def pipeline(tmp_path,monkeypatch):
    d,t=fixture();cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);run=tmp_path/'S01-E016-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'qualification.json',dict(status='synthetic_only',joint=dict(retained_old=14,net_targets=7),held_support=[]));d['snapshot']=snap
    lock=dict(original_rows_digest=c.digest(d['originals']),source_B12_hits=14,source_zip_sha256='synthetic',source_files={'qualification.json':c.sha(snap/'qualification.json')})
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.inputs,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None);monkeypatch.setattr(a.sys,'addaudithook',lambda hook:None)
    args=SimpleNamespace(source=tmp_path/'synthetic.zip',metadata=tmp_path/'synthetic.json',run=run);launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard(cfg);result=a.execute(args,cfg,lock,watch,launch)
    return run,lock,result,watch


def test_full_synthetic_execute_actual_plots_and_semantic_tamper(tmp_path,monkeypatch):
    run,lock,result,watch=pipeline(tmp_path,monkeypatch)
    assert result['primary_pass'] and result['comparison']['retention']==1 and result['comparison']['net_GT']==6
    assert watch.counts==dict(ranking_fits=13,fit_baseline_metrics=13,calibration_policy_comparisons=78,final_OOF_comparisons=1,held_group_comparisons=3)
    assert len(list((run/'analysis').glob('*.png')))==3
    text=(run/'analysis/README_analysis.md').read_text();assert 'per-candidate U regression' in text and 'Original|Positive intersection|Also x>=0' in text and 'seven-choice' not in text and 'tau=' not in text
    receipt=c.read(run/'output_receipt.json');ex={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')}
    bad=c.read(run/'capacity_audit.json');bad['folds'][0]['max_policy_positive_GT']=999;c.write(run/'capacity_audit.json',bad);receipt['files']['capacity_audit.json']=c.sha(run/'capacity_audit.json')
    with pytest.raises(ValueError,match='semantic'):a.verify(run,ex,receipt,lock['source_files'])


def test_actual_budget_harm_forces_abstention_despite_positive_capacity_entry(tmp_path,monkeypatch):
    d,t=fixture();full,_=old.fixture();d['originals']=full['originals']
    monkeypatch.setattr(c,'require_producer',lambda cfg:None)
    own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],CFG['locations']);model=a.calibrate(own,CFG,guard())
    assert model['mixture']=='abstain'
    p=next(p for p in model['policies'] if p['mixture']==.5)
    assert p['comparison']['lost_old']>0 and p['comparison']['net_GT']<=0
    assert len(p['source_keys'])>0
