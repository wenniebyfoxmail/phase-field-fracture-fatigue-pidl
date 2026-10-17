#!/usr/bin/env python3
"""Producer-only finite ranking learning; frozen ancestors loaded privately."""
import time
BOOT_START=time.monotonic()
import copy,importlib.util,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('e016_private_e015',HERE.parent/'pavetrack_locality_selector/run.py');ancestor=importlib.util.module_from_spec(spec);spec.loader.exec_module(ancestor)
r=ancestor.r;c=ancestor.c;locality=ancestor.locality
ranking=c.module('e016_ranking',HERE/'ranking.py')
c.PROTOCOL='S01-E016-v1';c.CONTRACT='docs/research/S01/S01-E016/';r.BOOT_START=BOOT_START;r.HERE=HERE
inherited_features=c.features
inputs=r.inputs;Guard=r.Guard;evaluate=r.evaluate;verify=r.verify


def features(originals,manifest,probabilities,cfg):
    rows=inherited_features(originals,manifest,probabilities,cfg)
    for row in rows:row['bounded_gain'],row['original_corrected_IoU']=ranking.representation(row,c)
    return rows


def policy(candidates,mixture,locations,cfg):return ranking.select(candidates,mixture,locations,cfg,c,locality)[0]


def calibrate(data,cfg,guard):return ranking.calibrate(data,cfg,guard,c,locality)

c.features=features;c.policy=policy;c.calibrate=calibrate


def fit_and_freeze(data,targets,run,cfg,guard,emit,calibrator=None):
    calibrator=calibrate if calibrator is None else calibrator
    original_digest=c.digest(data['originals']);models=[];support=[];predictions=[];all_added=[]
    for k,held in enumerate(cfg['held_groups']):
        fit=[x for x in cfg['locations'] if x not in held];audit=c.support_labels(data['labels'][k],data['candidates'],fit,data['image_locations'])
        if audit['positive_GT_count']!=cfg['fit']['expected_positive_GT'][k] or len(audit['positive_sites'])!=cfg['fit']['expected_positive_sites'][k] or audit['nonpositive']==0:raise ValueError('FIT support lineage')
        own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],fit);model=calibrator(own,cfg,guard);models.append(model);support.append(audit)
        added=policy(data['candidates'],model['mixture'],held,cfg);all_added.extend(copy.deepcopy(added));predictions.append(dict(fold=k,held_locations=held,mixture=model['mixture'],source_keys=[r['parent_id'] for r in added],rows=added));emit(f'model_fold_{k}.json',model)
    if c.digest(data['originals'])!=original_digest:raise ValueError('original mutation')
    emit('OOF_predictions.json',dict(protocol=c.PROTOCOL,folds=predictions,original_rows_digest=original_digest,GT_free_prediction=True))
    emit('prediction_freeze_receipt.json',dict(protocol=c.PROTOCOL,files={n:c.sha(run/n,guard.check) for n in ['OOF_predictions.json']+[f'model_fold_{k}.json' for k in range(3)]},frozen_before_held_evaluation=True))
    main_digest=c.digest(models);diagnostics=[]
    for k,audit in enumerate(support):
        fit=[x for x in cfg['locations'] if x not in cfg['held_groups'][k]]
        for omitted in audit['positive_sites']:
            locs=[x for x in fit if x!=omitted];own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locs);model=calibrator(own,cfg,guard)
            remaining={tuple(v) for row in data['labels'][k]['rows'] if row['U']>0 and row['location']!=omitted for v in row['new_identities']}
            diagnostics.append(dict(main_fold=k,omitted_location=omitted,original_FIT8_positive_GT_before=audit['positive_GT_count'],original_FIT8_positive_GT_remaining=len(remaining),support_scope='original FIT8 descriptive support after location deletion; not recomputed FIT7 U',mixture_flipped=model['mixture']!=models[k]['mixture'],model=model))
    if c.digest(models)!=main_digest or c.digest(data['originals'])!=original_digest:raise ValueError('diagnostic feedback/mutation')
    emit('jackknife.json',dict(used_to_choose_main=False,scope='correlated location-deletion sensitivity, not independent validation',fits=diagnostics))
    before=c.digest([models,all_added]);retained,capacity=ranking.audits(data,models,cfg,c,locality)
    if c.digest([models,all_added])!=before:raise ValueError('audit mutated main state')
    emit('locality_audit.json',retained);emit('capacity_audit.json',capacity);guard.check()
    return models,support,sorted(all_added,key=lambda r:r['parent_id'])

def execute(args,cfg,lock,guard,launch):
    expected={'launch.json':copy.deepcopy(launch)}
    def emit(name,value):expected[name]=copy.deepcopy(value);c.write(args.run/name,value)
    data=inputs.load(args.source,args.run,cfg,lock,guard,c);records=inputs.metadata(args.metadata,cfg,lock,guard,c)
    if set(records)!=set(data['image_locations']) or any(records[im]['reid']!=loc for im,loc in data['image_locations'].items()):raise ValueError('metadata image membership')
    targets={im:r['crack_boxes_xyxy'] for im,r in records.items()};gate=c.e12.PixelGate([]);sys.addaudithook(gate)
    emit('input_audit.json',dict(protocol=c.PROTOCOL,source_zip_sha256=lock['source_zip_sha256'],original_rows_digest=c.digest(data['originals']),originals=len(data['originals']),corrections=len(data['candidates']),eligible=sum(r['eligible'] for r in data['candidates']),feature=cfg['feature'],fitting_info='each explicit FIT scope only',fresh_access=False))
    emit('features.json',dict(names=cfg['feature']['names'],rows=data['candidates']))
    models,support,added=fit_and_freeze(data,targets,args.run,cfg,guard,emit)
    result=evaluate(data,targets,added,args.run,cfg,lock,guard,emit)
    # Full R004 oracle content is consulted for explanatory comparison only now.
    reference=c.read(data['snapshot']/'qualification.json');emit('reference_only.json',dict(used_for_training=False,source='E012-R004 GT-informed diagnostic',status=reference['status'],retained=reference['joint']['retained_old'],net=reference['joint']['net_targets'],positive_support=reference['held_support']))
    analysis=c.module('e013_analysis',HERE/'analyze.py');analysis.render(args.run,result,models,support,expected['evaluation.json'],guard)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original mutation')
    for key in ['ranking_fits','calibration_policy_comparisons','fit_baseline_metrics','final_OOF_comparisons','held_group_comparisons']:
        if guard.counts[key]!=cfg['budget'][key]:raise ValueError('incomplete phase count:'+key)
    emit('resource.json',guard.receipt());receipt=dict(protocol=c.PROTOCOL,files={p.relative_to(args.run).as_posix():c.sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock['source_files']);guard.check();return result

r.fit_and_freeze=fit_and_freeze;r.execute=execute
if __name__=='__main__':r.main()
