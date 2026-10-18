#!/usr/bin/env python3
"""Qualify independent RGB localisation on FIT sites before fold-local connection."""
import time
BOOT_START=time.monotonic()
import copy,importlib.util,os,sys,collections,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e025_prior',HERE.parent/'pavetrack_pixel_selector/run.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
r=prior.r;c=prior.c;learning=prior.learning;legacy=prior.legacy;inputs=prior.inputs;locality=prior.locality;audit=prior.audit
spatial=c.module('e025_spatial',HERE/'spatial.py');model=c.module('e025_model',HERE/'model.py');analysis=c.module('e025_analysis',HERE/'analyze.py')
c.PROTOCOL='S01-E025-v1';c.CONTRACT='docs/research/S01/S01-E025/';r.BOOT_START=BOOT_START;r.HERE=HERE
class Guard(c.e12.Guard):
    def receipt(self):
        out=super().receipt();out.update(model_fits=self.counts['model_fits'],linear_solves=self.counts['linear_solves'],gradient_steps=self.counts['gradient_steps'],parameter_gradient_steps=self.counts['parameter_gradient_steps'],localizer_backward_rows=self.counts['localizer_backward_rows'],E003_loaded=False,E003_parameter_gradient_steps=0,E003_backbone_backward_rows=0)
        return out
r.Guard=Guard

def backend(cfg,g):return model.Backend(cfg,g,c)

def scope(data,targets,locs):return c.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locs)

def support_checks(data,targets,cfg,g):
    states=[]
    for k,held in enumerate(cfg['held_groups']):
        locs=[v for v in cfg['locations'] if v not in held];own=scope(data,targets,locs);g.take('fit_baseline_metrics');ref=c.baseline(own);support=prior.prior_inputs.validate_supervision(data['supervision'][k],data['labels'][k],own,ref,k,c,locality,audit)
        if support['positive_GT_count']!=cfg['fit']['expected_positive_GT'][k] or len(support['positive_sites'])!=cfg['fit']['expected_positive_sites'][k]:raise ValueError('utility support identity')
        states.append((own,ref,support,locs))
    return states

def train_and_qualify(data,run,cfg,g,emit,engine):
    models=[];banks=[];controls=[];names=[]
    for k in range(3):
        bank=spatial.references(data,k,run,cfg,g,c,emit);banks.append(bank);own=[]
        # All support selection is train6-only, before any optimizer step.
        selected=model.control_indices(data['candidates'],bank,cfg,k)
        for j in range(2):
            g.take('localizer_models');g.take('control_models')
            m=engine.fit(data['rgb'],bank,data['candidates'],k,control=j)
            if m['control_indices']!=selected:raise ValueError('control selection identity')
            name=f'localizer_control_fold_{k}_seed_{j}.json';emit(name,m);names.append(name);own.append(m)
        controls.append(own);g.take('localizer_models');m=engine.fit(data['rgb'],bank,data['candidates'],k)
        if not m['verified'] or m['parameters']!=cfg['localizer']['parameters'] or m['state_digest']!=model.digest(m['state']):raise ValueError('unverified localizer')
        models.append(m);name=f'localizer_model_fold_{k}.json';emit(name,m);names.append(name)
    for k,own in enumerate(controls):
        for m in own:
            if not m['verified'] or m['parameters']!=cfg['localizer']['parameters'] or m['state_digest']!=model.digest(m['state']):raise ValueError('unverified control')
    emit('localizer_training_freeze.json',dict(files={n:c.sha(run/n,g.check) for n in names},all_nine_frozen_before_control_or_qualification=True,frozen_before_any_qualification=True))
    control_results=[];control_files=[]
    for k,own in enumerate(controls):
        rows=[]
        for j,m in enumerate(own):
            ids=m['control_indices'];name=f'control_maps_fold_{k}_seed_{j}.npy'
            maps=spatial.infer(engine,m,data['rgb'],ids,run/name,'control_prediction_rows',cfg,g)
            rows.append(model.control_metrics(maps,banks[k],ids));control_files.append(name)
        value=dict(fold=k,seeds=[m['seed'] for m in own],indices=own[0]['control_indices'],models=[m['state_digest'] for m in own],results=rows,passed=all(v['passed'] for v in rows),training_only=True,not_generalisation=True)
        control_results.append(value);name=f'control_fold_{k}.json';emit(name,value);control_files.append(name)
    emit('control_freeze.json',dict(files={n:c.sha(run/n,g.check) for n in control_files},before_qualification=True,controls_never_deployed=True))
    qualifications=[];data['qualification_maps']={};data['qualification_rows']={}
    for k,m in enumerate(models):
        q,maps,rows=spatial.qualification(engine,m,data,banks[k],run,cfg,g,c,emit,k)
        q['qualification_only_status']=q['status'];q['qualification_only_pass']=q['qualified'];q['training_controls']=control_results[k]
        q['qualified']=q['qualified'] and control_results[k]['passed']
        if not control_results[k]['passed']:q['status']='negative_control'
        emit(f'qualification_fold_{k}.json',q);qualifications.append(q);data['qualification_maps'][k]=maps;data['qualification_rows'][k]=rows
    admitted=[k for k,v in enumerate(qualifications) if v['qualified']]
    names+=control_files+['control_freeze.json']+[f'qualification_{kind}fold_{k}.{ext}' for k in range(3) for kind,ext in [('', 'json'),('maps_','npy')]]
    emit('qualification_freeze.json',dict(files={n:c.sha(run/n,g.check) for n in names},admitted_folds=admitted,all_decisions_before_role_fitting=True,outer_labels_used=False))
    return models,qualifications,admitted

def connect(data,targets,states,localizers,admitted,run,cfg,g,emit,engine):
    models=[];descriptors={};maps={};fit_states={};supports=[v[2] for v in states]
    for k,(own,ref,support,locs) in enumerate(states):
        if k not in admitted:
            m=dict(fold=k,qualified=False,abstained=True,threshold='abstain',heads={},policies=[],coefficient_count=0,reason='localizer not qualified; E003 fixed abstain');models.append(m);emit(f'model_fold_{k}.json',m);continue
        bank=spatial.infer(engine,localizers[k],data['rgb'],list(range(len(data['candidates']))),run/f'localizer_maps_fold_{k}.npy','localizer_prediction_rows',cfg,g);maps[k]=bank;g.take('pixel_map_prediction_rows',len(bank))
        desc=[dict(index=row['index'],parent_id=row['parent_id'],image_id=row['image_id'],location=row['location'],**spatial.describe(bank[row['index']],row['row']['original_box_xyxy'],row['row']['box_xyxy'],data['contexts'][row['index']])) for row in data['candidates']];descriptors[k]=desc
        context,features=prior.representation(own,cfg,g,desc)
        if data['context'][k]!=dict(fold=k,locations=locs,**context):raise ValueError('FIT context identity')
        labels=data['supervision'][k]['rows'];g.take('training_target_rows',len(labels));m=learning.fit([v['values'] for v in features],labels,cfg,g);m.pop('pixel_head_coefficients_in_separate_model',None);m.update(fold=k,qualified=True,localizer_parameters=cfg['localizer']['parameters'],localizer_state_digest=localizers[k]['state_digest'],locations=locs,training_original_digest=c.digest(own['originals']),training_rows_digest=c.digest(labels),support=audit.support_summary(labels));models.append(m);fit_states[k]=(features,labels)
    # Every admitted role head is verified before any role prediction.
    predictions=[];added_all=[];capacity=[]
    for k,(own,ref,support,locs) in enumerate(states):
        m=models[k];held=cfg['held_groups'][k]
        if k not in admitted:
            predictions.append(dict(fold=k,held_locations=held,threshold='abstain',source_keys=[],rows=[],features_and_predictions=[],trace=[],context=None,localizer_qualified=False));capacity.append(dict(fold=k,available_positive_GT=support['positive_GT_count'],max_policy_positive_GT=0,chosen_policy=dict(threshold='abstain',selected_positive_GT=0),policies=[],qualified=False));continue
        features,labels=fit_states[k];preds=prior.scored(m,features,g);scores=prior.score_map(preds);table=[]
        for threshold in cfg['feature']['thresholds']:
            added,trace=learning.select(own['candidates'],scores,threshold,own['locations'],cfg,c,locality);g.take('calibration_policy_comparisons');table.append(dict(threshold=threshold,source_keys=[v['parent_id'] for v in added],trace=trace,comparison=c.compare(own,added,ref),**prior.capacity(data['labels'][k]['rows'],[v['parent_id'] for v in added])))
        threshold=c.choose(table);m.update(threshold=threshold,policies=table,baseline=ref[0],abstained=threshold=='abstain');emit(f'FIT_predictions_fold_{k}.json',dict(fold=k,GT_free=True,rows=preds))
        ims={im:loc for im,loc in data['image_locations'].items() if loc in held};held_scope=dict(originals=[v for v in data['originals'] if v['image_id'] in ims],candidates=[v for v in data['candidates'] if v['image_id'] in ims],image_locations=ims)
        context,features=prior.representation(held_scope,cfg,g,descriptors[k]);preds=prior.scored(m,features,g);added,trace=learning.select(held_scope['candidates'],prior.score_map(preds),threshold,held,cfg,c,locality);added_all.extend(copy.deepcopy(added));predictions.append(dict(fold=k,held_locations=held,threshold=threshold,source_keys=[v['parent_id'] for v in added],rows=added,features_and_predictions=preds,trace=trace,context=context,localizer_qualified=True));emit(f'model_fold_{k}.json',m)
        chosen=next(p for p in table if p['threshold']==threshold);capacity.append(dict(fold=k,available_positive_GT=support['positive_GT_count'],max_policy_positive_GT=max(p['selected_positive_GT'] for p in table),chosen_policy=chosen,policies=table,qualified=True))
    emit('OOF_predictions.json',dict(protocol=c.PROTOCOL,folds=predictions,GT_free_prediction=True,original_rows_digest=c.digest(data['originals']),unqualified_folds_fixed_abstain=True))
    names=['OOF_predictions.json','qualification_freeze.json']+[f'model_fold_{k}.json' for k in range(3)]+[f'localizer_maps_fold_{k}.npy' for k in admitted]+[f'localizer_model_fold_{k}.json' for k in range(3)]
    emit('prediction_freeze_receipt.json',dict(files={n:c.sha(run/n,g.check) for n in names},all_admitted_heads_verified_before_role_predictions=True,frozen_before_held_evaluation=True,admitted_folds=admitted))
    data['maps']=maps;data['descriptors']=descriptors;emit('capacity_audit.json',dict(folds=capacity,used_to_choose_main=False));emit('locality_audit.json',locality.retention_audit(data,cfg));return models,supports,sorted(added_all,key=lambda r:r['parent_id'])

def outer_pixels(data,localizers,admitted,cfg,g):
    records=[]
    for k in admitted:
        last=None;arr=None
        for row in data['candidates']:
            if row['location'] not in cfg['held_groups'][k]:continue
            im=row['image_id']
            if im!=last:
                mask=spatial.pixel.raster(data['annotations'][im],data['images'][im]);arr=__import__('numpy').asarray(mask,dtype='uint8').copy();mask.close();last=im
            i=row['index'];g.take('pixel_evaluation_rows');records.append(dict(index=i,image_id=im,location=row['location'],fold=k,**spatial.component(data['maps'][k][i],spatial.target(arr,data['contexts'][i]),localizers[k]['train_prevalence'])))
    images,sites=spatial.aggregate(records,cfg['locations']);active=[v for v in sites if v['images']];keys=['Brier','constant_Brier','zero_Brier','one_Brier','Dice'];return dict(contexts=records,images=images,locations=sites,macro={key:sum(r[key] for r in active)/len(active) for key in keys},covered_locations=[v['location'] for v in active],scope='post-freeze admittedfold outer pixels only; other sites null/not_predicted',used_to_choose_model_or_gate=False)

def cases(data,targets,added,admitted,qualifications,run,cfg,g,emit):
    keys=[];kind='qualification_only';originals={v['parent_id']:v for v in data['originals']}
    if not admitted:
        for k,rows in data['qualification_rows'].items():
            for loc in cfg['localizer']['qual_locations'][k]:
                choices=[(j,row) for j,row in enumerate(rows) if row['location']==loc];j,row=min(choices,key=lambda v:(-originals[v[1]['parent_id']]['score'],v[1]['image_id'],tuple(v[1]['row']['box_xyxy']),v[1]['parent_id']));keys.append((k,row,data['qualification_maps'][k][j],'own qualification site, excluded from CNN fit'))
    else:
        by={v['parent_id']:v for v in data['candidates']};orig={v['parent_id']:v for v in data['originals']};kind='OOF_appended' if added else 'FIT_opportunity_not_selected'
        pool={v['parent_id'] for v in added} if added else {v['parent_id'] for k in admitted for v in data['labels'][k]['rows'] if v['U']>0}
        for key in sorted(pool,key=lambda x:(-orig[x]['score'],by[x]['image_id'],tuple(by[x]['row']['box_xyxy']),x))[:6]:
            row=by[key];k=c.group_of(row['location'],cfg) if added else min(k for k in admitted if any(v['parent_id']==key and v['U']>0 for v in data['labels'][k]['rows']));keys.append((k,row,data['maps'][k][row['index']],'OOF held' if added else 'FIT opportunity, not OOF detection'))
    result=[];buffers=[]
    for j,(k,row,heat,scope_name) in enumerate(keys[:6]):
        im=row['image_id'];rec=data['images'][im];raw=spatial.image_bytes(rec,g);path=run/'case_images'/f'{j}.jpg';path.parent.mkdir(exist_ok=True);path.write_bytes(raw);buffers.append(raw);result.append(dict(parent_id=row['parent_id'],fold=k,image_id=im,location=row['location'],width=rec['width'],height=rec['height'],snapshot=path.relative_to(run).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),context=data['contexts'][row['index']],heatmap=heat.tolist(),original=row['row']['original_box_xyxy'],corrected=row['row']['box_xyxy'],GT=targets[im],GT_polygons=[v['polygon'] for v in data['annotations'][im] if v['category'] in ['Alligator Crack','Transverse Crack']],scope=scope_name))
    emit('cases.json',dict(kind=kind,cases=result,used_for_learning=False,rule='one global branch only; max6 total extra source reads; frozen score/image/key order'));return result,buffers

def exact_counts(cfg,g,admitted):
    b=cfg['budget'];mandatory=['feature_cache_bytes','spatial_feature_rows','source_image_decodes','localizer_models','localizer_steps','gradient_steps','parameter_gradient_steps','localizer_training_rows','localizer_backward_rows','localizer_mask_rows','localizer_mask_bytes','localizer_qualification_rows','localizer_qualifications','fit_baseline_metrics','control_models','control_steps','control_training_rows','control_prediction_rows']
    for name in mandatory:
        if g.counts[name]!=b[name]:raise ValueError('incomplete phase:'+name)
    n=cfg['input_counts']['corrections'];a=len(admitted);formula={'model_sets':a,'model_fits':3*a,'linear_solves':3*a,'training_target_rows':sum(cfg['budget_definitions']['role_training_rows'][k] for k in admitted),'prediction_rows':cfg['budget_definitions']['eligible_rows']*a,'context_feature_builds':2*a,'calibration_policy_comparisons':5*a,'localizer_prediction_rows':n*a,'pixel_map_prediction_rows':n*a,'pixel_evaluation_rows':sum(cfg['budget_definitions']['held_candidate_rows'][k] for k in admitted),'final_OOF_comparisons':int(a>0),'held_group_comparisons':3*int(a>0)}
    for key,value in formula.items():
        if g.counts[key]!=value:raise ValueError('conditional phase:'+key)

def verify(run,expected,receipt,lock):
    wanted=set(expected)|{'rgb_contexts.npy','image_progress.jsonl','input_snapshot/train_polygons.json'}|{'input_snapshot/'+n for n in lock['source_files']}|{f'FIT_masks_fold_{k}.npy' for k in range(3)}|{f'qualification_maps_fold_{k}.npy' for k in range(3)}|{'analysis/F00_qualification.png','analysis/F02_cases.png','analysis/README_analysis.md'}|{v['snapshot'] for v in expected['cases.json']['cases']}
    wanted|={'control_freeze.json'}|{f'control_fold_{k}.json' for k in range(3)}|{f'{kind}_fold_{k}_seed_{j}.{ext}' for k in range(3) for j in range(2) for kind,ext in [('localizer_control','json'),('control_maps','npy')]}
    admitted=expected['qualification_freeze.json']['admitted_folds']
    if admitted:wanted|={f'localizer_maps_fold_{k}.npy' for k in admitted}|{'analysis/F01_detection.png'}
    if set(receipt['files'])!=wanted:raise ValueError('strict output inventory')
    for n,h in receipt['files'].items():c.e12.checked(run/n,h)
    for n,v in expected.items():
        if c.read(run/n)!=v:raise ValueError('trusted semantic mismatch:'+n)
    for receipt_name in ['localizer_training_freeze.json','control_freeze.json','qualification_freeze.json']+(['prediction_freeze_receipt.json'] if admitted else []):
        for n,h in expected[receipt_name]['files'].items():c.e12.checked(run/n,h)
    for k in range(3):
        c.e12.checked(run/f'FIT_masks_fold_{k}.npy',expected[f'FIT_reference_index_fold_{k}.json']['sha256'])
        c.e12.checked(run/f'qualification_maps_fold_{k}.npy',expected[f'qualification_fold_{k}.json']['map_sha256'])
    for n,h in lock['source_files'].items():c.e12.checked(run/'input_snapshot'/n,h)
    c.e12.checked(run/'input_snapshot/train_polygons.json',lock['annotation_snapshot_sha256']);c.e12.checked(run/'rgb_contexts.npy',expected['spatial_extraction_receipt.json']['features_sha256']);c.e12.checked(run/'image_progress.jsonl',expected['spatial_extraction_receipt.json']['progress_sha256'])
    for v in expected['cases.json']['cases']:c.e12.checked(run/v['snapshot'],v['sha256'])
    return True

def execute(args,cfg,lock,g,launch):
    c.require_producer(cfg);expected={'launch.json':copy.deepcopy(launch)}
    def emit(n,v):expected[n]=copy.deepcopy(v);c.write(args.run/n,v)
    data=inputs.load(args.source,args.run,cfg,lock,g,c,legacy,prior.prior_inputs);records=legacy.metadata(args.metadata,cfg,lock,g,c)
    if set(records)!=set(data['image_locations']) or any(records[im]['reid']!=loc for im,loc in data['image_locations'].items()):raise ValueError('metadata scope')
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original identity')
    targets={im:v['crack_boxes_xyxy'] for im,v in records.items()};gate=c.e12.PixelGate(list(data['images'].values()));sys.addaudithook(gate);states=support_checks(data,targets,cfg,g)
    emit('input_audit.json',dict(original_rows_digest=c.digest(data['originals']),source_zip_sha256=lock['source_zip_sha256'],originals=len(data['originals']),corrections=len(data['candidates']),fresh_access=False))
    data['rgb'],data['contexts']=spatial.extract(data,args.run,cfg,g,c,emit);engine=backend(cfg,g);localizers,qualifications,admitted=train_and_qualify(data,args.run,cfg,g,emit,engine)
    if admitted:
        models,supports,added=connect(data,targets,states,localizers,admitted,args.run,cfg,g,emit,engine);result=r.evaluate(data,targets,added,args.run,cfg,lock,g,emit);emit('pixel_evaluation.json',outer_pixels(data,localizers,admitted,cfg,g))
    else:
        added=[];models=[];result=dict(protocol=c.PROTOCOL,status='localizer_not_qualified_no_connection',stageA=[q['status'] for q in qualifications],stageB='inconclusive_not_executed',primary_pass=None,comparison=dict(retention=None,new_GT=None,lost_old=None,net_GT=None,macro_delta=None),originals_unchanged=True,original_rows_digest=c.digest(data['originals']),fresh_access=False);emit('result.json',result)
    rows,buffers=cases(data,targets,added,admitted,qualifications,args.run,cfg,g,emit);analysis.render(args.run,result,qualifications,admitted,rows,buffers,g,c,spatial)
    gate.output.update(os.path.normcase(os.path.abspath(p)) for p in (args.run/'analysis').glob('*.png'))
    gate.output.update(os.path.normcase(os.path.abspath(args.run/v['snapshot'])) for v in rows)
    exact_counts(cfg,g,admitted)
    if c.digest(data['originals'])!=lock['original_rows_digest']:raise ValueError('original mutation')
    if sum(p.stat().st_size for p in args.run.rglob('*') if p.is_file())>cfg['budget']['archive_bytes_limit']-1048576:raise RuntimeError('archive cap')
    emit('resource.json',g.receipt());receipt=dict(files={p.relative_to(args.run).as_posix():c.sha(p,g.check) for p in sorted(args.run.rglob('*')) if p.is_file()},fresh_access=False);c.write(args.run/'output_receipt.json',receipt);verify(args.run,expected,receipt,lock);g.check();return result
r.execute=execute
original_main=r.main
def main():
    try:original_main()
    except model.ReferenceUnavailable as ex:
        # The ancestor already preserved a stopped execution receipt; classify the
        # missing-reference scientific result without inventing maps or metrics.
        run=Path(sys.argv[sys.argv.index('--run')+1]);path=run/'status.json';status=c.read(path)
        status.update(scientific_status='inconclusive_reference_unavailable',stageB='not_executed',net_GT=None)
        c.write(path,status);c.write(run/'inconclusive_reference.json',dict(reason=str(ex),stageB='not_executed',primary_pass=None,net_GT=None))
        raise
if __name__=='__main__':main()
