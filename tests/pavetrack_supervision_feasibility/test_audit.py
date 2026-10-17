import copy,importlib.util,json,math
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e017_tests',ROOT/'scripts/pavetrack_supervision_feasibility/run.py');c=a.c;m=a.audit
old=module('e017_synthetic_fixture',ROOT/'tests/pavetrack_utility_ranking/test_ranking.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')


def cached_fixture():
    d,t=old.fixture()
    for row in d['manifest']:
        if row['location'] not in {'514','1577','728','4494','2027'}:row['corrected_box_xyxy']=[2,0,12,10]
    d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],CFG)
    d['labels']=[]
    # Construct synthetic cached singleton records with the canonical comparator.
    # This is fixture creation only, never true-bank U recomputation by the consumer.
    for fold,held in enumerate(CFG['held_groups']):
        locs=[x for x in CFG['locations'] if x not in held];own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],locs);ref=c.baseline(own);rows=[]
        for candidate in own['candidates']:
            if not candidate['eligible']:continue
            q=c.compare(own,[candidate['row']],ref);cutoff=q['candidate']['global_score_threshold'];score=candidate['row']['score']
            rows.append(dict(index=candidate['index'],parent_id=candidate['parent_id'],image_id=candidate['image_id'],location=candidate['location'],score=score,new=q['new_GT'],lost=q['lost_old'],FP=q['added_FP'],U=q['new_GT']-q['lost_old']-q['added_FP'],new_identities=q['new_identities'],lost_identities=q['lost_identities'],admitted=cutoff is not None and score>=cutoff,cutoff=cutoff))
        d['labels'].append(dict(scope=f'fit8_fold_{fold}',locations=locs,baseline=ref[0],rows=rows))
    cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);cfg['budget']['supervision_rows']=sum(len(p['rows']) for p in d['labels'])
    return d,t,cfg


def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def own0():
    d,t,cfg=cached_fixture();scope=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],d['labels'][0]['locations']);return d,t,cfg,scope


def test_design_is_audit_only_and_ancestors_are_private_and_producer_gate(monkeypatch):
    assert old.c.PROTOCOL=='S01-E016-v1' and c.PROTOCOL=='S01-E017-v1'
    assert CFG['budget']['model_fits']==CFG['budget']['new_singleton_U']==0
    assert CFG['budget']['oracle_comparisons']==6 and CFG['budget']['supervision_rows']==38768
    with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})


def test_same_reference_gain_is_not_difference_of_separate_best_matches():
    d,t,cfg,own=own0();ref=c.baseline(own);rows,support=m.supervision(own,d['labels'][0],ref,c,a.locality)
    changed=next(row for row in rows if row['cached_singleton']['U']>0)
    assert changed['parent_max_IoU']==changed['corrected_max_IoU']==1
    assert changed['gain_same_reference']>.6 and changed['reference_state']=='switched'
    assert support['positive_GT_count']==3


@pytest.mark.parametrize('GT,expected', [([], (0.,None)),([[30,30,40,40]],(0.,None)),([[0,0,10,10],[0,0,10,10]],(1.,0))])
def test_null_reference_and_deterministic_tie(GT,expected):assert m.best_reference([0,0,10,10],GT,c)==expected


def test_GT_free_relative_pressure_and_exact_ties():
    row=dict(image_id='i',reid='24',parent_id=1,score=.5,box_xyxy=[0,0,10,10]);originals=[row,dict(row,parent_id=2,score=.8),dict(row,parent_id=3,score=.5)]
    candidate=dict(index=1,parent_id=1,image_id='i',location='24',eligible=True,row=dict(row,score=.5),GT='POISON',U=999,cutoff=999,admitted=True)
    out=m.context_features(originals,[candidate],{'i':'24'},c)
    assert out['rows'][0]['values']==[1.,2.,2] and out['GT_free'] and 'cutoff' not in out['names']
    candidate.update(GT=[],U=-999,admitted=False,cutoff=-999)
    assert m.context_features(originals,[candidate],{'i':'24'},c)==out


def test_context_features_scoped_bank_size_and_empty_scope():
    d,t,cfg,own=own0();features=m.context_features(own['originals'],own['candidates'],own['image_locations'],c)
    assert len(features['rows'])==len(own['candidates'])
    with pytest.raises(ValueError):m.context_features(own['originals'],own['candidates'],{},c)
    poison=copy.deepcopy(own['candidates']);poison[0]['row']['score']=float('nan')
    with pytest.raises(ValueError):m.context_features(own['originals'],poison,own['image_locations'],c)


def test_two_fixed_oracles_keep_cap_and_actual_positive_gain():
    d,t,cfg,own=own0();ref=c.baseline(own);labels,support=m.supervision(own,d['labels'][0],ref,c,a.locality)
    A,ta=m.oracle_select(own['candidates'],labels,'validity_only',cfg,c);B,tb=m.oracle_select(own['candidates'],labels,'decomposed_novel_budget',cfg,c)
    b=c.compare(own,B,ref);aa=c.compare(own,A,ref)
    assert b['retention']==1 and b['net_GT']==3 and aa['new_GT']<b['new_GT']
    assert len({r['image_id'] for r in B})==len(B) and all(sum(c.group_of(r['reid'],cfg)==g for r in B)<=3 for g in range(3))
    assert all(entry['reason']=='accepted' for entry in tb)
    assert all(row==next(cand['row'] for cand in own['candidates'] if cand['parent_id']==row['parent_id']) for row in B)
    with pytest.raises(ValueError):m.oracle_select(own['candidates'],labels,'scan',cfg,c)


def test_oracle_B_uses_decomposed_fields_not_U_gate():
    d,t,cfg,own=own0();labels,_=m.supervision(own,d['labels'][0],c.baseline(own),c,a.locality)
    expected=m.oracle_select(own['candidates'],labels,'decomposed_novel_budget',cfg,c)
    # Selection must not read U; label identity validation remains upstream.
    poison=copy.deepcopy(labels)
    for row in poison:row['cached_singleton']['U']=-999
    assert m.oracle_select(own['candidates'],poison,'decomposed_novel_budget',cfg,c)==expected


def test_validity_redundancy_is_separate_from_novel_budget_role_and_counts_deduplicate():
    d,t,cfg,own=own0();labels,_=m.supervision(own,d['labels'][0],c.baseline(own),c,a.locality);summary=m.support_summary(labels)
    assert summary['components']['valid_reference_already_detected']['candidates']>0
    assert summary['components']['cached_positive_utility']['distinct_cached_new_GT']==3
    copyrow=copy.deepcopy(next(r for r in labels if r['cached_singleton']['U']>0));out=m.support_summary(labels+[copyrow])
    assert out['components']['cached_positive_utility']['distinct_cached_new_GT']==3 and out['components']['cached_positive_utility']['candidates']==4


@pytest.mark.parametrize('kind',['baseline','score','counts','scope','admitted','cutoff','GT_index','new_membership','U'])
def test_cached_role_identity_and_scope_corruption_rejected(kind):
    d,t,cfg,own=own0();p=copy.deepcopy(d['labels'][0]);positive=next(row for row in p['rows'] if row['U']>0)
    if kind=='baseline':p['baseline']['macro_location_recall']=999
    elif kind=='score':p['rows'][0]['score']+=.01
    elif kind=='counts':positive['new_identities'].append(positive['new_identities'][0])
    elif kind=='scope':p['locations']=cfg['held_groups'][0]
    elif kind=='admitted':p['rows'][0]['admitted']=not p['rows'][0]['admitted']
    elif kind=='cutoff':p['rows'][0]['cutoff']=float('nan')
    elif kind=='GT_index':positive['new_identities'][0][1]=999
    elif kind=='new_membership':
        im=positive['image_id'];positive['new_identities']=[[im,0]]
    else:positive['U']=-123
    with pytest.raises(ValueError):m.supervision(own,p,c.baseline(own),c,a.locality)


def test_scope_process_counts_and_no_held_GT_feedback():
    d,t,cfg=cached_fixture();watch=guard(cfg);before=copy.deepcopy(d);report,labels,features,cases=m.process_scope(d,t,d['labels'][0],0,cfg,watch,c,a.locality)
    poison=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in cfg['held_groups'][0]:poison[im]=[]
    report2,labels2,features2,cases2=m.process_scope(d,poison,d['labels'][0],0,cfg,guard(cfg),c,a.locality)
    assert (report,labels,features,cases)==(report2,labels2,features2,cases2) and d==before
    assert watch.counts==dict(fit_baseline_metrics=1,context_feature_builds=1,supervision_rows=8,oracle_comparisons=2)


def test_fixed_intersection_marker_cannot_be_tampered():
    d,t,cfg,own=own0();own['candidates'][0]['positive_intersection']=False
    with pytest.raises(ValueError,match='representation'):m.supervision(own,d['labels'][0],c.baseline(own),c,a.locality)


def test_empty_fixed_admission_keeps_safe_no_correction_without_expanding_family():
    d,t,cfg,own=own0();ref=c.baseline(own);labels,_=m.supervision(own,d['labels'][0],ref,c,a.locality)
    for row in labels:row['fixed_admission']=False
    for name in cfg['oracles']['names']:
        rows,trace=m.oracle_select(own['candidates'],labels,name,cfg,c);comparison=c.compare(own,rows,ref)
        assert rows==trace==[] and comparison['retention']==1 and comparison['net_GT']==0


@pytest.mark.parametrize('kind',['RSS','WALL','COUNT'])
def test_budget_caps(kind):
    if kind=='RSS':watch=a.Guard(CFG,memory=lambda:2**33)
    elif kind=='WALL':watch=a.Guard(CFG,start=0,clock=lambda:1000,memory=lambda:0)
    else:watch=guard();watch.counts['oracle_comparisons']=6
    with pytest.raises(RuntimeError):watch.take('oracle_comparisons') if kind=='COUNT' else watch.check()


def pipeline(tmp_path,monkeypatch):
    d,t,cfg=cached_fixture();run=tmp_path/'S01-E017-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'qualification.json',dict(synthetic=True));d['snapshot']=snap
    lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'qualification.json':c.sha(snap/'qualification.json')})
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.inputs,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None);monkeypatch.setattr(a.sys,'addaudithook',lambda hook:None)
    args=SimpleNamespace(source=tmp_path/'synthetic.zip',metadata=tmp_path/'synthetic_metadata.json',run=run);launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard(cfg);result=a.execute(args,cfg,lock,watch,launch)
    return run,result,watch,lock


def test_complete_synthetic_execute_no_fit_claim_actual_figures_and_semantic_tamper(tmp_path,monkeypatch):
    run,result,watch,lock=pipeline(tmp_path,monkeypatch)
    assert result['primary_pass'] and result['primary_is_feasibility_only'] and not result['learned_result'] and result['passing_FITs']==3
    assert watch.counts==dict(fit_baseline_metrics=3,context_feature_builds=3,supervision_rows=28,oracle_comparisons=6)
    assert result['models_fitted']==result['full12_comparisons']==result['held_comparisons']==0
    assert len(list((run/'analysis').glob('*.png')))==3
    text=(run/'analysis/README_analysis.md').read_text();assert 'not predictor quality' in text and 'no held/full12 comparison' in text
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'supervision_fold_0.json');bad['rows'][0]['gain_same_reference']=999;c.write(run/'supervision_fold_0.json',bad);receipt['files']['supervision_fold_0.json']=c.sha(run/'supervision_fold_0.json')
    with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock['source_files'])
