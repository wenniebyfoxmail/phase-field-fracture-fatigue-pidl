#!/usr/bin/env python3
"""Producer-only fixed pixel-spatial descriptors and low-capacity selector."""
import time
BOOT_START=time.monotonic()
import copy,importlib.util,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e021_private_e015',HERE.parent/'pavetrack_locality_selector/run.py');ancestor=importlib.util.module_from_spec(s);s.loader.exec_module(ancestor)
r=ancestor.r;c=ancestor.c;locality=ancestor.locality;legacy=r.inputs
prior_inputs=c.module('e021_prior_inputs',HERE.parent/'pavetrack_role_probe/inputs.py');spatial=c.module('e021_spatial',HERE/'spatial.py')
learning=c.module('e021_learning',HERE/'learning.py');inputs=c.module('e021_inputs',HERE/'inputs.py');audit=c.module('e021_context_only',HERE.parent/'pavetrack_supervision_feasibility/audit.py')
c.PROTOCOL='S01-E021-v1';c.CONTRACT='docs/research/S01/S01-E021/';r.BOOT_START=BOOT_START;r.HERE=HERE
LegacyGuard=r.Guard
class Guard(LegacyGuard):
    def receipt(self):
        out=super().receipt();out.update(model_fits=self.counts['model_fits'],linear_solves=self.counts['linear_solves'],prediction_rows=self.counts['prediction_rows'],prediction_is_neural_forward=False,pixel_reads=self.counts['pixel_reads'],source_image_decodes=self.counts['source_image_decodes'],case_image_decodes=self.counts['case_image_decodes']);return out
r.Guard=Guard
InheritedRequire=c.require_producer
def require_producer(cfg):
    InheritedRequire(cfg)
    if os.environ.get('OPENBLAS_NUM_THREADS')!='1':raise PermissionError('CPU1 requires OPENBLAS_NUM_THREADS=1')
c.require_producer=require_producer


def representation(scope,cfg,guard,spatial_rows):
    guard.take('context_feature_builds');context=audit.context_features(scope['originals'],scope['candidates'],scope['image_locations'],c,guard);by={r['parent_id']:r for r in scope['candidates'] if r['eligible']};rows=[]
    for record in context['rows']:
        row=by[record['parent_id']];pressure,ties,overlap=record['values'];h=c.e8.box_iou(row['row']['original_box_xyxy'],row['row']['box_xyxy'])
        rows.append(dict(index=row['index'],parent_id=row['parent_id'],image_id=row['image_id'],location=row['location'],values=[row['row']['probability'],h,1/(1+overlap),1/(1+pressure)]))
    for row in rows:
        pixel=spatial_rows[row['index']]
        if any(pixel[k]!=row[k] for k in ['index','parent_id','image_id','location']):raise ValueError('pixel-feature row identity')
        row['values']+=pixel['values']
    learning.matrix([r['values'] for r in rows]);return context,rows


def scored(model,rows,guard):
    output=learning.predict(model,[r['values'] for r in rows],guard)
    return [dict(**row,**value) for row,value in zip(rows,output,strict=True)]


def score_map(rows):return {r['parent_id']:dict(roles=r['roles'],rank_score=r['rank_score']) for r in rows}


def capacity(rows,keys):
    chosen=set(keys);positive=[r for r in rows if r['parent_id'] in chosen and r['U']>0]
    return dict(selected_positive_candidates=len(positive),selected_positive_GT=len({tuple(v) for r in positive for v in r['new_identities']}))


def fit_and_freeze(data,targets,run,cfg,guard,emit):
    c.require_producer(cfg);digest=c.digest(data['originals']);pixel_digest=c.digest(data['spatial']);states=[];models=[];supports=[]
    # All nine main heads fit and numerically verified before any main prediction.
    for k,held in enumerate(cfg['held_groups']):
        locs=[x for x in cfg['locations'] if x not in held];own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locs)
        guard.take('fit_baseline_metrics');ref=c.baseline(own);payload=data['labels'][k];support=prior_inputs.validate_supervision(data['supervision'][k],payload,own,ref,k,c,locality,audit)
        if support['positive_GT_count']!=cfg['fit']['expected_positive_GT'][k] or len(support['positive_sites'])!=cfg['fit']['expected_positive_sites'][k]:raise ValueError('positive support identity')
        context,features=representation(own,cfg,guard,data['spatial'])
        if data['context'][k]!=dict(fold=k,locations=locs,**context):raise ValueError('cached FIT context mismatch')
        labels=data['supervision'][k]['rows'];guard.take('training_target_rows',len(labels));model=learning.fit([v['values'] for v in features],labels,cfg,guard)
        model.update(fold=k,locations=locs,training_original_digest=c.digest(own['originals']),training_rows_digest=c.digest(labels),support=audit.support_summary(labels),source='own saved E017 supervision and fixed new box-relative pixel descriptors; no representation fitting')
        states.append((own,ref,features,labels));models.append(model);supports.append(support)
    predictions=[];all_added=[];capacity_folds=[]
    for k,(own,ref,features,labels) in enumerate(states):
        model=models[k];fit_predictions=scored(model,features,guard);scores=score_map(fit_predictions);table=[]
        for threshold in cfg['feature']['thresholds']:
            added,trace=learning.select(own['candidates'],scores,threshold,own['locations'],cfg,c,locality);guard.take('calibration_policy_comparisons');comparison=c.compare(own,added,ref)
            table.append(dict(threshold=threshold,source_keys=[v['parent_id'] for v in added],trace=trace,comparison=comparison,**capacity(data['labels'][k]['rows'],[v['parent_id'] for v in added])))
        threshold=c.choose(table);model.update(threshold=threshold,policies=table,baseline=ref[0],abstained=threshold=='abstain',selection_reason='no protected FIT joint gain' if threshold=='abstain' else 'FIT netGT, min correction FP/exposure, largest gate')
        emit(f'FIT_predictions_fold_{k}.json',dict(fold=k,GT_free=True,rows=fit_predictions))
        # Prediction scope has no targets or labels: even held scope construction is GT-free.
        held=cfg['held_groups'][k];ims={im:loc for im,loc in data['image_locations'].items() if loc in held};scope=dict(originals=[v for v in data['originals'] if v['image_id'] in ims],candidates=[v for v in data['candidates'] if v['image_id'] in ims],image_locations=ims)
        context,held_features=representation(scope,cfg,guard,data['spatial']);held_predictions=scored(model,held_features,guard);added,trace=learning.select(scope['candidates'],score_map(held_predictions),threshold,held,cfg,c,locality)
        all_added.extend(copy.deepcopy(added));predictions.append(dict(fold=k,held_locations=held,threshold=threshold,source_keys=[v['parent_id'] for v in added],rows=added,features_and_predictions=held_predictions,trace=trace,context=context));emit(f'model_fold_{k}.json',model)
        chosen=next(v for v in table if v['threshold']==threshold);capacity_folds.append(dict(fold=k,available_positive_GT=supports[k]['positive_GT_count'],max_policy_positive_GT=max(v['selected_positive_GT'] for v in table),chosen_policy=chosen,policies=table))
    emit('OOF_predictions.json',dict(protocol=c.PROTOCOL,folds=predictions,GT_free_prediction=True,original_rows_digest=digest))
    names=['OOF_predictions.json']+[f'model_fold_{k}.json' for k in range(3)]
    emit('prediction_freeze_receipt.json',dict(protocol=c.PROTOCOL,files={n:c.sha(run/n,guard.check) for n in names},frozen_before_held_evaluation=True,all_nine_main_heads_verified_before_predictions=True))
    main_digest=c.digest([models,predictions]);diagnostics=[]
    for k,(own,ref,features,labels) in enumerate(states):
        for omitted in supports[k]['positive_sites']:
            indices=[j for j,row in enumerate(labels) if row['location']!=omitted];model=learning.fit([features[j]['values'] for j in indices],[labels[j] for j in indices],cfg,guard)
            pred=scored(model,features,guard);added,trace=learning.select(own['candidates'],score_map(pred),models[k]['threshold'],own['locations'],cfg,c,locality)
            keys=[v['parent_id'] for v in added];diagnostics.append(dict(main_fold=k,omitted_location=omitted,scope='original FIT8 labels/context/bank, delete training rows only; not rebased FIT7 U or independent CV',main_threshold=models[k]['threshold'],model=model,source_keys=keys,selection_changed=keys!=next(v for v in models[k]['policies'] if v['threshold']==models[k]['threshold'])['source_keys'],predictions=pred,trace=trace,**capacity(data['labels'][k]['rows'],keys)))
    if c.digest([models,predictions])!=main_digest or c.digest(data['originals'])!=digest or c.digest(data['spatial'])!=pixel_digest:raise ValueError('diagnostic feedback or original mutation')
    emit('jackknife.json',dict(used_to_choose_main=False,new_gate_calibration=False,new_detector_comparisons=0,fits=diagnostics));emit('capacity_audit.json',dict(folds=capacity_folds,source='saved own FIT8 membership; not joint gains',used_to_choose_main=False));emit('locality_audit.json',locality.retention_audit(data,cfg))
    return models,supports,sorted(all_added,key=lambda v:v['parent_id'])


def verify(run,expected,receipt,lock):
    snapshots={row['snapshot']:row['sha256'] for row in expected['cases.json']['cases']}
    wanted=set(expected)|{'image_progress.jsonl','analysis/F00_learning.png','analysis/F01_detection.png','analysis/F02_cases.png','analysis/README_analysis.md'}|{'input_snapshot/'+n for n in lock['source_files']}|set(snapshots)
    if set(receipt['files'])!=wanted:raise ValueError('strict output inventory')
    for name,h in receipt['files'].items():c.e12.checked(run/name,h)
    for name,value in expected.items():
        if c.read(run/name)!=value:raise ValueError('trusted semantic mismatch:'+name)
    for name,h in lock['source_files'].items():c.e12.checked(run/'input_snapshot'/name,h)
    for name,h in snapshots.items():c.e12.checked(run/name,h)
    c.e12.checked(run/'image_progress.jsonl',expected['spatial_extraction_receipt.json']['progress_sha256'])
    return True

def execute(args,cfg,lock,guard,launch):
    c.require_producer(cfg);expected={'launch.json':copy.deepcopy(launch)}
    def emit(name,value):expected[name]=copy.deepcopy(value);c.write(args.run/name,value)
    data=inputs.load(args.source,args.run,cfg,lock,guard,c,legacy,prior_inputs);records=legacy.metadata(args.metadata,cfg,lock,guard,c)
    if set(records)!=set(data['image_locations']) or any(records[im]['reid']!=loc for im,loc in data['image_locations'].items()):raise ValueError('metadata scope')
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original identity')
    targets={im:v['crack_boxes_xyxy'] for im,v in records.items()};gate=c.e12.PixelGate(list(data['images'].values()));sys.addaudithook(gate)
    emit('input_audit.json',dict(protocol=c.PROTOCOL,source_zip_sha256=lock['source_zip_sha256'],original_rows_digest=c.digest(data['originals']),originals=len(data['originals']),corrections=len(data['candidates']),eligible=sum(v['eligible'] for v in data['candidates']),fresh_access=False))
    data['spatial']=spatial.extract(data,args.run,cfg,guard,c,emit)
    models,support,added=fit_and_freeze(data,targets,args.run,cfg,guard,emit)
    result=r.evaluate(data,targets,added,args.run,cfg,lock,guard,emit)
    cases,case_buffers=spatial.cases(data,targets,added,args.run,cfg,guard,c,emit)
    analysis=c.module('e021_saved_analysis',HERE/'analyze.py');analysis.render(args.run,result,models,support,expected['evaluation.json'],guard,cases,case_buffers)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    gate.output.update(os.path.normcase(os.path.abspath(args.run/row['snapshot'])) for row in cases['cases'])
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original mutation')
    for key in ['source_image_decodes','spatial_feature_rows','model_sets','model_fits','linear_solves','training_target_rows','context_feature_builds','prediction_rows','fit_baseline_metrics','calibration_policy_comparisons','final_OOF_comparisons','held_group_comparisons']:
        if guard.counts[key]!=cfg['budget'][key]:raise ValueError('incomplete phase count:'+key)
    emit('resource.json',guard.receipt());receipt=dict(protocol=c.PROTOCOL,files={p.relative_to(args.run).as_posix():c.sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock);guard.check();return result
r.execute=execute
if __name__=='__main__':r.main()
