#!/usr/bin/env python3
"""Producer-only frozen class-margin spatial attribution and low-capacity selector."""
import time
BOOT_START=time.monotonic()
import copy,importlib.util,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e023_private_e015',HERE.parent/'pavetrack_locality_selector/run.py');ancestor=importlib.util.module_from_spec(s);s.loader.exec_module(ancestor)
r=ancestor.r;c=ancestor.c;locality=ancestor.locality;legacy=r.inputs
prior_inputs=c.module('e023_prior_inputs',HERE.parent/'pavetrack_role_probe/inputs.py');spatial=c.module('e023_spatial',HERE/'spatial.py')
learning=c.module('e023_learning',HERE/'learning.py');inputs=c.module('e023_inputs',HERE/'inputs.py');audit=c.module('e023_context_only',HERE.parent/'pavetrack_supervision_feasibility/audit.py');pixel=c.module('e023_pixel',HERE/'pixels.py')
c.PROTOCOL='S01-E023-v1';c.CONTRACT='docs/research/S01/S01-E023/';r.BOOT_START=BOOT_START;r.HERE=HERE
# Reuse the existing GPU-aware resource guard, not the inherited CPU-only guard.
class Guard(c.e12.Guard):
    def receipt(self):
        out=super().receipt()
        out.update(model_fits=self.counts['model_fits'],linear_solves=self.counts['linear_solves'],prediction_rows=self.counts['prediction_rows'],prediction_is_neural_forward=False,pixel_reads=self.counts['pixel_reads'],backbone_forwards=self.counts['backbone_forwards'],head_forwards=self.counts['head_forwards'],head_input_gradient_rows=self.counts['head_input_gradient_rows'],backbone_backward_rows=0,parameter_gradient_steps=0,source_image_decodes=self.counts['source_image_decodes'],case_image_decodes=self.counts['case_image_decodes'],pixel_head_fits=self.counts['pixel_head_fits'],pixel_training_sample_rows=self.counts['pixel_training_sample_rows'],pixel_map_prediction_rows=self.counts['pixel_map_prediction_rows'])
        return out
r.Guard=Guard

def require_producer(cfg):
    c.e12.runtime.production_environment(cfg)
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
    c.require_producer(cfg);digest=c.digest(data['originals']);states=[];pixel_models=[]
    # All pixel models use only their own FIT8 polygon labels, including ineligible contexts.
    for k,held in enumerate(cfg['held_groups']):
        locs=[x for x in cfg['locations'] if x not in held];own=c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locs)
        guard.take('fit_baseline_metrics');ref=c.baseline(own);support=prior_inputs.validate_supervision(data['supervision'][k],data['labels'][k],own,ref,k,c,locality,audit)
        if support['positive_GT_count']!=cfg['fit']['expected_positive_GT'][k] or len(support['positive_sites'])!=cfg['fit']['expected_positive_sites'][k]:raise ValueError('positive utility support identity')
        annotations={im:data['annotations'][im] for im in own['image_locations']}
        model=pixel.fit(data['pixel_features'],data['contexts'],data['candidates'],annotations,data['images'],locs,cfg,guard,learning.ridge);pixel_models.append(model);emit(f'pixel_model_fold_{k}.json',model);states.append((own,ref,support,locs))
    maps=[];descriptors=[];models=[];fit_states=[]
    for k,(own,ref,support,locs) in enumerate(states):
        bank,desc=spatial.maps_and_descriptors(pixel_models[k],data['pixel_features'],data['contexts'],data['candidates'],run,k,cfg,guard,pixel);maps.append(bank);descriptors.append(desc)
        context,features=representation(own,cfg,guard,desc)
        if data['context'][k]!=dict(fold=k,locations=locs,**context):raise ValueError('cached FIT context mismatch')
        labels=data['supervision'][k]['rows'];guard.take('training_target_rows',len(labels));model=learning.fit([row['values'] for row in features],labels,cfg,guard)
        model.update(fold=k,locations=locs,training_original_digest=c.digest(own['originals']),training_rows_digest=c.digest(labels),support=audit.support_summary(labels),pixel_model=pixel_models[k],source='own-FIT human polygon-region supervised pixel readout; no current-held labels')
        models.append(model);fit_states.append((features,labels))
    # All three pixel heads and all nine role heads verified before ANY role prediction.
    data['pixel_models']=pixel_models;data['pixel_maps']=maps;data['spatial_by_fold']=descriptors
    predictions=[];all_added=[];capacity_folds=[]
    for k,((own,ref,support,locs),(features,labels)) in enumerate(zip(states,fit_states,strict=True)):
        model=models[k];fit_predictions=scored(model,features,guard);scores=score_map(fit_predictions);table=[]
        for threshold in cfg['feature']['thresholds']:
            added,trace=learning.select(own['candidates'],scores,threshold,own['locations'],cfg,c,locality);guard.take('calibration_policy_comparisons');comparison=c.compare(own,added,ref)
            table.append(dict(threshold=threshold,source_keys=[v['parent_id'] for v in added],trace=trace,comparison=comparison,**capacity(data['labels'][k]['rows'],[v['parent_id'] for v in added])))
        threshold=c.choose(table);model.update(threshold=threshold,policies=table,baseline=ref[0],abstained=threshold=='abstain',selection_reason='no protected FIT joint gain' if threshold=='abstain' else 'FIT netGT, FP, exposure, larger gate')
        emit(f'FIT_predictions_fold_{k}.json',dict(fold=k,GT_free=True,rows=fit_predictions))
        held=cfg['held_groups'][k];ims={im:loc for im,loc in data['image_locations'].items() if loc in held};scope=dict(originals=[v for v in data['originals'] if v['image_id'] in ims],candidates=[v for v in data['candidates'] if v['image_id'] in ims],image_locations=ims)
        context,held_features=representation(scope,cfg,guard,descriptors[k]);held_predictions=scored(model,held_features,guard);added,trace=learning.select(scope['candidates'],score_map(held_predictions),threshold,held,cfg,c,locality);all_added.extend(copy.deepcopy(added))
        predictions.append(dict(fold=k,held_locations=held,threshold=threshold,source_keys=[v['parent_id'] for v in added],rows=added,features_and_predictions=held_predictions,trace=trace,context=context));emit(f'model_fold_{k}.json',model)
        chosen=next(v for v in table if v['threshold']==threshold);capacity_folds.append(dict(fold=k,available_positive_GT=support['positive_GT_count'],max_policy_positive_GT=max(v['selected_positive_GT'] for v in table),chosen_policy=chosen,policies=table))
    emit('OOF_predictions.json',dict(protocol=c.PROTOCOL,folds=predictions,GT_free_prediction=True,original_rows_digest=digest))
    names=['OOF_predictions.json']+[f'{prefix}_fold_{k}.{ext}' for k in range(3) for prefix,ext in [('model','json'),('pixel_model','json'),('pixel_maps','npy')]]
    emit('prediction_freeze_receipt.json',dict(protocol=c.PROTOCOL,files={n:c.sha(run/n,guard.check) for n in names},frozen_before_held_evaluation=True,all_three_pixel_and_nine_role_heads_verified_before_role_predictions=True))
    data['spatial']=[descriptors[c.group_of(row['location'],cfg)][row['index']] for row in data['candidates']]
    emit('spatial_features.json',dict(protocol=c.PROTOCOL,GT_free_prediction=True,OOF_descriptors=True,rows=data['spatial']))
    emit('capacity_audit.json',dict(folds=capacity_folds,source='own FIT8 membership, overlapping utility GT',used_to_choose_main=False));emit('locality_audit.json',locality.retention_audit(data,cfg))
    if c.digest(data['originals'])!=digest:raise ValueError('original mutation')
    return models,[v[2] for v in states],sorted(all_added,key=lambda r:r['parent_id'])


def verify(run,expected,receipt,lock):
    snapshots={row['snapshot']:row['sha256'] for row in expected['cases.json']['cases']}
    wanted=set(expected)|{'pixel_features.npy','input_snapshot/train_polygons.json'}|{f'pixel_maps_fold_{k}.npy' for k in range(3)}|{'image_progress.jsonl','analysis/F00_learning.png','analysis/F01_detection.png','analysis/F02_cases.png','analysis/F03_pixel_component.png','analysis/README_analysis.md'}|{'input_snapshot/'+n for n in lock['source_files']}|set(snapshots)
    if set(receipt['files'])!=wanted:raise ValueError('strict output inventory')
    for name,h in receipt['files'].items():c.e12.checked(run/name,h)
    for name,value in expected.items():
        if c.read(run/name)!=value:raise ValueError('trusted semantic mismatch:'+name)
    for name,h in expected['prediction_freeze_receipt.json']['files'].items():c.e12.checked(run/name,h)
    for name,h in lock['source_files'].items():c.e12.checked(run/'input_snapshot'/name,h)
    for name,h in snapshots.items():c.e12.checked(run/name,h)
    c.e12.checked(run/'input_snapshot/train_polygons.json',lock['annotation_snapshot_sha256'])
    c.e12.checked(run/'pixel_features.npy',expected['spatial_extraction_receipt.json']['features_sha256'])
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
    backend=spatial.backend(cfg,lock,guard,c)
    data['pixel_features'],data['contexts']=spatial.extract(data,args.run,cfg,guard,c,emit,backend)
    del backend
    models,support,added=fit_and_freeze(data,targets,args.run,cfg,guard,emit)
    result=r.evaluate(data,targets,added,args.run,cfg,lock,guard,emit)
    frozen=c.read(args.run/'prediction_freeze_receipt.json')
    for n,h in frozen['files'].items():c.e12.checked(args.run/n,h,guard.check)
    emit('pixel_evaluation.json',pixel.evaluate(data,data['pixel_models'],data['pixel_maps'],cfg,guard))
    cases,case_buffers=spatial.cases(data,targets,added,args.run,cfg,guard,c,emit)
    analysis=c.module('e023_saved_analysis',HERE/'analyze.py');analysis.render(args.run,result,models,support,expected['evaluation.json'],guard,cases,case_buffers)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    gate.output.update(os.path.normcase(os.path.abspath(args.run/row['snapshot'])) for row in cases['cases'])
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original mutation')
    for key in ['source_image_decodes','feature_cache_bytes','spatial_feature_rows','backbone_forwards','pixel_head_fits','pixel_training_sample_rows','pixel_map_prediction_rows','pixel_evaluation_rows','model_sets','model_fits','linear_solves','training_target_rows','context_feature_builds','prediction_rows','fit_baseline_metrics','calibration_policy_comparisons','final_OOF_comparisons','held_group_comparisons']:
        if guard.counts[key]!=cfg['budget'][key]:raise ValueError('incomplete phase count:'+key)
    if sum(p.stat().st_size for p in args.run.rglob('*') if p.is_file())>cfg['budget']['archive_bytes_limit']-1048576:raise RuntimeError('fixed evidence archive size cap')
    emit('resource.json',guard.receipt());receipt=dict(protocol=c.PROTOCOL,files={p.relative_to(args.run).as_posix():c.sha(p,guard.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock);guard.check();return result
r.execute=execute
if __name__=='__main__':r.main()
